from stim4prf import logger
from .fixation import FixationDot, FixationCross, ABCTargetFixation
from .reaction_time import analyze_reaction_times
from psychopy import visual, core
from psychopy.hardware import keyboard
from datetime import datetime
import numpy as np
import os

def get_screen_size(screen: int):
    """Return (width, height) for the requested screen. Fall back to primary if unavailable."""
    try:
        import pyglet
        display = pyglet.canvas.get_display()
        screens = display.get_screens()
        if screen < len(screens):
            return screens[screen].width, screens[screen].height
        else:
            logger.warning(f"Requested screen {screen} not available. Falling back to primary screen (0).")
            return screens[0].width, screens[0].height
    except Exception as e:
        logger.warning(f"Could not query screens ({e}). Using default PsychoPy screen size.")
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
        fixation_type: str = 'dot',
        screen: int = 0,
        verbose: bool = False,
        trigger_key: str = '6',
        abort_key: str = 'escape',
        fixation_color_switch_prob: float = 0.01,
        fixation_cross_size: int = 30,
        fixation_dot_radius: int = 8,
        min_switch_interval: float = 2.0,
        frame_log_interval: int = 100,

        end_screen_wait: float = 2.0
    ):
        """
        Initialize the presenter.
        """
        self.verbose = verbose
        self.trigger_key = trigger_key
        self.abort_key = abort_key
        self.frame_log_interval = frame_log_interval
        self.end_screen_wait = end_screen_wait

        # Cross-platform screen size handling
        width, height = get_screen_size(screen)
        window_kwargs = dict(
            fullscr=True,
            screen=screen,
            units='pix',
            colorSpace='rgb1',
            color=[0.5,0.5,0.5],
        )
        if width is not None and height is not None:
            window_kwargs['size'] = (width, height)

        self.win = visual.Window(**window_kwargs)

        # Load only indices and LUT
        self.indexed_matrix, self.lut, self.frame_duration = loader.load()
        self.nFrames = self.indexed_matrix.shape[0]
        self.screen = screen

        # Choose fixation type
        if fixation_type == 'dot':
            self.fixation = FixationDot(
                self.win,
                radius=fixation_dot_radius,
                color_switch_prob=fixation_color_switch_prob,
                min_switch_interval=min_switch_interval,
                verbose=self.verbose
            )
        elif fixation_type == 'cross':
            self.fixation = FixationCross(
                self.win,
                size=fixation_cross_size,
                color_switch_prob=fixation_color_switch_prob,
                min_switch_interval=min_switch_interval,
                verbose=self.verbose
            )
        elif fixation_type == 'abc':
            self.fixation = ABCTargetFixation(
                self.win,
            )
        else:
            logger.error(f"Invalid fixation_type: {fixation_type}")
            raise ValueError("fixation_type must be 'dot', 'cross', or 'abc'")

        # Prepare image stimulus
        h, w = self.indexed_matrix.shape[1:3]
        dummy_rgb = np.zeros((h, w, 3), dtype=np.float32)
        self.img_stim = visual.ImageStim(
            self.win,
            image=dummy_rgb,
            units='pix',
            size=(w, h),
            colorSpace='rgb1'
        )

    def run(
        self,
        subject: str,
        session: str,
        run: str,
        outdir: str,
        button_keys = ['1', '2', '3', '4']
    ) -> None:
        """
        Run the stimulus presentation.
        Handles trigger wait, stimulus loop, and logging.
        Logs frame onsets, fixation color changes, and button presses.
        """
        import csv
        timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        log_fname = os.path.join(
            outdir,
            f"sub-{subject}_ses-{session}_run-{run}_{timestamp}.tsv"
        )
        os.makedirs(outdir, exist_ok=True)

        info_text = visual.TextStim(self.win, text=f"Waiting for scanner...\nPress '{self.trigger_key}' to begin",
                                   color=[1,1,1], height=30)
        info_text.draw()
        self.win.flip()
        kb = keyboard.Keyboard()
        kb.clearEvents()
        core.wait(0.2)
        if self.verbose:
            logger.info("Awaiting scanner trigger...")

        try:
            while True:
                keys = kb.getKeys(keyList=[self.trigger_key, self.abort_key], waitRelease=False)
                if keys:
                    if keys[0].name == self.abort_key:
                        logger.info("Aborted by user.")
                        return
                    elif keys[0].name == self.trigger_key:
                        break
                core.wait(0.001)
            if self.verbose:
                logger.info("Scanner trigger received, starting presentation.")

            global_clock = core.Clock()
            frame_onsets = []
            button_events = []
            prev_button_state = set()
            frame_idx = 0
            scan_trigger_times = []

            while frame_idx < self.nFrames:
                if kb.getKeys(keyList=[self.abort_key], waitRelease=False):
                    logger.info("Aborted by user.")
                    return

                t = global_clock.getTime()

                # log the scanner trigger
                if kb.getKeys(keyList=[self.trigger_key], waitRelease=False):
                    scan_trigger_times.append(t)

                # log the button presses
                pressed = kb.getKeys(keyList=button_keys, waitRelease=False, clear=False)
                for key in pressed:
                    if key.name not in prev_button_state:
                        button_events.append((t, key.name))
                prev_button_state = set(k.name for k in pressed)

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

            final_text = visual.TextStim(self.win, text="Experiment complete.\nThank you!",
                                        color=[1,1,1], height=30)
            final_text.draw()
            self.win.flip()
            core.wait(self.end_screen_wait)

            # Collect all events in a single list
            all_events = []

            for idx, onset in enumerate(frame_onsets):
                all_events.append((onset, 'frame_onset', idx))

            for t, color in getattr(self.fixation, 'switch_log', []):
                all_events.append((t, 'fixation_color_switch', color))

            for t, key in button_events:
                all_events.append((t, 'button_press', key))

            for t in scan_trigger_times:
                all_events.append((t, 'scanner_trigger', f'button {self.trigger_key}'))

            # Sort all events by their timestamp
            all_events.sort(key=lambda x: x[0])

            with open(log_fname, 'w', newline='') as f:
                writer = csv.writer(f, delimiter='\t')
                writer.writerow(['Time', 'Event', 'Value'])
                for event in all_events:
                    writer.writerow(event)

                # --- Reaction time analysis ---
                switch_log = getattr(self.fixation, 'switch_log', [])
                n_hits, n_switches, mean_rt, _ = analyze_reaction_times(switch_log, button_events)
                hit_ratio = (n_hits / n_switches * 100) if n_switches > 0 else 0

                result1 = f"[RESULT] {n_hits}/{n_switches} ({hit_ratio:.1f}%) color switches were followed by a button press in 0.3–3s."
                result2 = f"[RESULT] Mean reaction time: {mean_rt:.3f} s"
                logger.info(result1)
                logger.info(result2)
                writer.writerow(['result', '', result1])
                writer.writerow(['result', '', result2])
            if self.verbose:
                logger.info(f"Saved timing log: {log_fname}")
        except Exception as e:
            logger.error(f"Exception during run: {e}")
            raise
        finally:
            if hasattr(self, 'win') and self.win:
                self.win.close()
