from stim4prf import logger
from .fixation import FixationDot, FixationCross, ABCTargetFixation
from .reaction_time import analyze_reaction_times
from .eyetracking import EyeLinkTracker
from psychopy import visual, core
from psychopy.hardware import keyboard
from datetime import datetime
import numpy as np
import os
import csv

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
        fixation_class=FixationDot,
        fixation_kwargs=None,
        eyetracker_class=None,
        eyetracker_kwargs=None,
        screen: int = 0,
        verbose: bool = False,
        trigger_key: str = '6',
        abort_key: str = 'escape',
        frame_log_interval: int = 100,
        end_screen_wait: float = 2.0
    ):
        """
        Initialize the presenter.
        """
        self.loader = loader
        self.verbose = verbose
        self.trigger_key = trigger_key
        self.abort_key = abort_key
        self.frame_log_interval = frame_log_interval
        self.end_screen_wait = end_screen_wait
        self.screen = screen
        
        # Eyetracker instantiation (after window is created)
        self.eyetracker = None
        if eyetracker_class is not None:
            print('starting eyetracker')
            if eyetracker_kwargs is None:
                eyetracker_kwargs = {}
            self.eyetracker = eyetracker_class(**eyetracker_kwargs)

        # Cross-platform screen size handling
        width, height = get_screen_size(screen)
        window_kwargs = dict(
            fullscr=True,
            screen=self.screen,
            units='pix',
            colorSpace='rgb1',
            color=[0.5,0.5,0.5],
        )
        if width is not None and height is not None:
            window_kwargs['size'] = (width, height)
            
        # Create PsychoPy window
        self.win = visual.Window(**window_kwargs)

        # Load only indices and LUT
        self.indexed_matrix, self.lut, self.frame_duration = loader.load()
        self.nFrames = self.indexed_matrix.shape[0]

        # Choose fixation type
        if fixation_kwargs is None:
            fixation_kwargs = {}
        self.fixation = fixation_class(self.win, **fixation_kwargs)

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
            # --- EYETRACKER SETUP ---
            if self.eyetracker:
                self.eyetracker.connect()
                self.eyetracker.calibrate()
                self.eyetracker.drift_correction()
                self.eyetracker.start_recording()
                self.eyetracker.send_message(f"EXPERIMENT_START {subject} {session} {run}")

            # --- Wait for scanner trigger, then mark stimulus onset ---
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

            # --- Wait for trigger, then ---
            if self.eyetracker:
                self.eyetracker.send_message("stimulus_onset")

            # --- Main stimulus loop ---
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

                if self.eyetracker and kb.getKeys(keyList=[self.trigger_key], waitRelease=False):
                    self.eyetracker.send_message('scanner_trigger')

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

            # Save behavioral log
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

            if self.eyetracker:
                self.eyetracker.send_message("stimulus_end")
                self.eyetracker.stop_recording()
                self.eyetracker.download_data()
                # Let the eyetracker handle saving its own data (agnostic call)
                h5_fname = log_fname.replace('.tsv', '_eyetrack.h5')
                self.eyetracker.save_hdf5(
                    h5_fname,
                    all_events=all_events,
                    stimulus_onset=all_events[0][0] if all_events else None,
                    stimulus_end=all_events[-1][0] if all_events else None,
                    scan_triggers=scan_trigger_times,
                    metadata={'subject': subject, 'session': session, 'run': run}
                )
                if self.verbose:
                    logger.info(f"Saved eyetracking data: {h5_fname}")
