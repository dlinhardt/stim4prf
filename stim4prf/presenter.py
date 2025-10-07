import csv
import os
from datetime import datetime

import numpy as np
from psychopy import core, visual
from psychopy.hardware import keyboard

from stim4prf import logger

from .eyetracking import EyeLinkTracker, MRCEyeTracking
from .fixation import ABCTargetFixation, FixationCross, FixationDot
from .reaction_time import analyze_reaction_times


def get_screen_size(screen: int):
    """
    Return (width, height) for the requested screen.
    Falls back to primary if unavailable.
    """
    try:
        import pyglet

        display = pyglet.canvas.get_display()
        screens = display.get_screens()
        if screen < len(screens):
            logger.info(
                f"Screen size {screens[screen].width} x {screens[screen].height}"
            )
            return screens[screen].width, screens[screen].height
        else:
            logger.warning(
                f"Requested screen {screen} not available. Falling back to primary screen (0)."
            )
            logger.info(f"Screen size {screens[0].width} x {screens[0].height}")
            return screens[0].width, screens[0].height
    except Exception as e:
        logger.warning(
            f"Could not query screens ({e}). Using default PsychoPy screen size."
        )
        # Use PsychoPy default; usually fills the screen for fullscr=True
        return None, None


# ----------- Main Experiment Presenter -----------
class PRFStimulusPresenter:
    """
    Main class for presenting pRF stimuli using PsychoPy.
    Handles window creation, stimulus presentation, fixation, and logging.
    """

    def __init__(
        self,
        loader,
        fixation_class=FixationDot,
        fixation_kwargs=None,
        eyetracker_class=None,
        eyetracker_kwargs=None,
        screen: int = 0,
        verbose: bool = False,
        trigger_key: str = "s",
        abort_key: str = "escape",
        frame_log_interval: int = 100,
        end_screen_wait: float = 2.0,
        flipVert: bool = False,
        flipHoriz: bool = False,
    ):
        """
        Initialize the presenter and load stimulus.
        """
        self.loader = loader
        self.fixation_class = fixation_class
        self.fixation_kwargs = fixation_kwargs or {}
        self.eyetracker_class = eyetracker_class
        self.eyetracker_kwargs = eyetracker_kwargs or {}
        self.screen = screen
        self.verbose = verbose
        self.trigger_key = trigger_key
        self.abort_key = abort_key
        self.frame_log_interval = frame_log_interval
        self.end_screen_wait = end_screen_wait

        # --- Load the stimulus ---
        self.indexed_matrix, self.lut, self.frame_duration = self.loader.load()

        # --- Apply image transformations ONCE here ---
        self.flipVert = flipVert
        self.flipHoriz = flipHoriz
        if flipVert:
            self.indexed_matrix = np.flip(self.indexed_matrix, axis=1)
        if flipHoriz:
            self.indexed_matrix = np.flip(self.indexed_matrix, axis=2)

        self.nFrames = self.indexed_matrix.shape[0]

        # Initialize Eyetracker
        self.eyetracker = None
        if self.eyetracker_class is not None:
            self.eyetracker = self.eyetracker_class(**self.eyetracker_kwargs)

    def _setup_run(self):
        """
        Set up PsychoPy window, fixation, and image stimulus for each run.
        """

        # Initialize window
        width, height = get_screen_size(self.screen)
        window_kwargs = dict(
            fullscr=True,
            screen=self.screen,
            units="pix",
            colorSpace="rgb1",
            color=[0.5, 0.5, 0.5],
            checkTiming=True,
        )
        if width is not None and height is not None:
            window_kwargs["size"] = (width, height)
        self.win = visual.Window(**window_kwargs)

        # Initialize fixation
        self.fixation = self.fixation_class(self.win, **self.fixation_kwargs)

        # Initialize image stimulus
        h, w = self.indexed_matrix.shape[1:3]
        dummy_rgb = np.zeros((h, w, 3), dtype=np.float32)
        self.img_stim = visual.ImageStim(
            self.win,
            image=dummy_rgb,
            units="pix",
            size=(w, h),
            colorSpace="rgb1",
        )

    def run(
        self,
        subject: str,
        session: str,
        run: str,
        outdir: str,
        button_keys=None,
        ip: str | None = None,
    ) -> None:
        """
        Run the stimulus presentation.
        Handles trigger wait, stimulus loop, and logging.
        Logs frame onsets, fixation color changes, and button presses.
        """
        if button_keys is None:
            button_keys = ["1", "2", "3", "4"]

        # --- Setup window, fixation, and image stimulus ---
        self._setup_run()

        # --- Show break screen and wait for ENTER ---
        break_text = visual.TextStim(
            self.win,
            text="Break!\n\nPress ENTER to continue.\n\nPress SPACE to show fixation.",
            color=[1, 1, 1],
            height=60,
            pos=(0, -self.win.size[1] / 4),  # halfway to the bottom
        )
        break_text.draw()

        self.win.flip()
        kb = keyboard.Keyboard()
        kb.clearEvents()
        while True:
            keys = kb.getKeys(
                keyList=["return", "enter", "space", self.abort_key], waitRelease=False
            )
            if any(k.name == self.abort_key for k in keys):
                logger.info("Aborted by user.")
                return
            elif any(k.name == "space" for k in keys):
                # Show fixation for 2 seconds
                self.fixation.update()
                self.fixation.draw()
                self.win.flip()
                break
            elif any(k.name in ("return", "enter") for k in keys):
                break
            core.wait(0.01)

        # --- Prepare logging ---
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        log_fname = f"sub-{subject}_ses-{session}_run-{run}_{timestamp}.tsv"
        log_fpath = os.path.join(outdir, log_fname)
        os.makedirs(outdir, exist_ok=True)

        # --- Eyetracker setup and calibration (no recording yet) ---
        if self.eyetracker:
            if self.verbose:
                logger.info("Starting eyetracker calibration...")
            # Ensure a valid IP string for non-dummy mode
            self.eyetracker.connect(ip=ip or "100.1.1.1")
            self.eyetracker.calibrate(self.win)
            self.eyetracker.drift_correction()


        # --- Show start screen: fixation + instructions ---
        # Draw fixation at center
        self.fixation.update()
        self.fixation.draw()

        # Instruction at center
        center_text = visual.TextStim(
            self.win,
            text="Please fixate on the central target and keep your head still.",
            color=[1, 1, 1],
            height=30,
            pos=(0, self.win.size[1] / 8),
            flipHoriz=self.flipHoriz,
            flipVert=self.flipVert,
        )

        # Scanner wait message halfway to the bottom
        bottom_text = visual.TextStim(
            self.win,
            text=f"Waiting for scanner...\nPress '{self.trigger_key}' to begin.",
            color=[1, 1, 1],
            height=30,
            pos=(0, -self.win.size[1] / 4),
        )

        center_text.draw()
        bottom_text.draw()
        self.win.flip()
        kb.clearEvents()
        core.wait(0.2)
        if self.verbose:
            logger.info("Awaiting scanner trigger...")

        all_events = []  # Collect all events for logging
        aborted = False

        if self.eyetracker:
            # Start eyetracker recording
            if self.verbose:
                logger.info("Starting eyetracker recording...")
            self.eyetracker.start_recording()
            self.eyetracker.send_message(
                msg=f"run about to start sub-{subject} ses-{session} run-{run}"
            )

        try:
            # --- Wait for scanner trigger or abort key ---
            while True:
                keys = kb.getKeys(
                    keyList=[self.trigger_key, self.abort_key], waitRelease=False
                )
                if any(k.name == self.abort_key for k in keys):
                    logger.info("Aborted by user before start.")
                    aborted = True
                    break
                elif any(k.name == self.trigger_key for k in keys):
                    break
                core.wait(0.001)
            if self.verbose:
                logger.info("Scanner trigger received, starting presentation.")
            if aborted:
                # Skip recording/presentation; cleanup happens in finally
                return

            if self.eyetracker:
                self.eyetracker.send_message(f"BLOCK_START sub-{subject} ses-{session} run-{run}")
                self.eyetracker.send_message(f"TRIALID 1")
                self.eyetracker.send_message("EXPERIMENT_START")

            # --- Initialize clocks and event logs ---
            global_clock = core.Clock()
            frame_onsets = []
            button_events = []
            prev_button_state = set()
            frame_idx = 0
            scan_trigger_times = []

            # --- Mark stimulus onset for eyetracker ---
            if self.eyetracker:
                self.eyetracker.send_message("stimulus_onset")

            # --- Main stimulus presentation loop ---
            while frame_idx < self.nFrames:
                # --- Check for abort key ---
                if kb.getKeys(keyList=[self.abort_key], waitRelease=False):
                    logger.info("Aborted by user during run.")
                    aborted = True
                    break

                t = global_clock.getTime()

                # --- Log scanner trigger key presses ---
                if kb.getKeys(keyList=[self.trigger_key], waitRelease=False):
                    scan_trigger_times.append(t)
                    if self.eyetracker:
                        self.eyetracker.send_message(msg="scanner_trigger")

                # --- Log button presses ---
                pressed = kb.getKeys(
                    keyList=button_keys, waitRelease=False, clear=False
                )
                for key in pressed:
                    if key.name not in prev_button_state:
                        button_events.append((t, key.name))
                prev_button_state = set(k.name for k in pressed)

                # --- Present next stimulus frame if time ---
                if t >= (frame_idx * self.frame_duration):
                    idx = self.indexed_matrix[frame_idx]
                    rgb = self.lut[idx]
                    self.img_stim.setImage(rgb)
                    self.img_stim.draw()
                    self.fixation.update(now=t)
                    self.fixation.draw()
                    self.win.flip()
                    frame_onsets.append(t)
                    frame_idx += 1
                    if self.verbose and frame_idx % self.frame_log_interval == 0:
                        logger.info(f"Presented frame {frame_idx}/{self.nFrames}")
                else:
                    core.wait(0.001)

            # --- Show end screen ---
            final_text = visual.TextStim(
                self.win,
                text="Experiment complete.\nThank you!",
                color=[1, 1, 1],
                height=30,
            )
            final_text.draw()
            self.win.flip()
            core.wait(self.end_screen_wait)

            # --- Mark stimulus end for eyetracker ---
            if self.eyetracker:
                self.eyetracker.send_message("TRIAL_RESULT 0")
                self.eyetracker.send_message("BLOCK_END")
                self.eyetracker.send_message("EXPERIMENT_END")

            # --- Collect all events for logging ---
            for idx, onset in enumerate(frame_onsets):
                all_events.append((onset, "frame_onset", idx))
            for t, color in getattr(self.fixation, "switch_log", []):
                all_events.append((t, "fixation_color_switch", color))
            for t, key in button_events:
                all_events.append((t, "button_press", key))
            for t in scan_trigger_times:
                all_events.append((t, "scanner_trigger", f"button {self.trigger_key}"))
            all_events.sort(key=lambda x: x[0])

            # --- Save behavioral log and analyze reaction times ---
            with open(log_fpath, "w", newline="") as f:
                writer = csv.writer(f, delimiter="\t")
                writer.writerow(["Time", "Event", "Value"])
                for event in all_events:
                    writer.writerow(event)

                # --- Reaction time analysis ---
                switch_log = getattr(self.fixation, "switch_log", [])
                n_hits, n_switches, mean_rt, _ = analyze_reaction_times(
                    switch_log, button_events
                )
                hit_ratio = (n_hits / n_switches * 100) if n_switches > 0 else 0

                result1 = f"[RESULT] {n_hits}/{n_switches} ({hit_ratio:.1f}%) color switches were followed by a button press in 0.3–3s."
                result2 = f"[RESULT] Mean reaction time: {mean_rt:.3f} s"
                logger.info(result1)
                logger.info(result2)
                writer.writerow(["result", "", result1])
                writer.writerow(["result", "", result2])
            if self.verbose:
                logger.info(f"Saved timing log: {log_fpath}")

        except Exception as e:
            logger.error(f"Exception during run: {e}")
            raise
        finally:
            # --- Cleanup: close window and eyetracker ---
            if self.eyetracker:
                # Always try to end cleanly (even if aborted)
                self.eyetracker.send_message("stimulus_end")
                try:
                    self.eyetracker.stop_recording()
                except Exception:
                    pass
                # Pull EDF once per run
                try:
                    self.eyetracker.download_data(log_fname)
                finally:
                    self.eyetracker.close()
            # --- Close window last ---
            if hasattr(self, "win") and self.win:
                self.win.close()
