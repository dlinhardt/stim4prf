import logging
from abc import ABC, abstractmethod
import os
import numpy as np
from datetime import datetime
from psychopy import visual, core
from psychopy.hardware import keyboard
from scipy.io import loadmat
import pyglet
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[stim4prf][%(levelname)s] %(message)s'
)
logger = logging.getLogger("stim4prf")

# ----------- Stimulus Loader Abstract Base -----------
class StimulusLoader(ABC):
    """Abstract base class for stimulus loaders."""
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    @abstractmethod
    def load(self):
        """Return (indexed_matrix, lut, frame_duration)"""
        pass

# ----------- MATLAB Loader -----------
class MatlabStimulusLoader(StimulusLoader):
    """Loads stimulus from a MATLAB .mat file."""
    def __init__(self, mat_path: str, verbose: bool = False):
        super().__init__(verbose)
        self.mat_path = mat_path

    def load(self):
        if self.verbose:
            logger.info(f"Loading MATLAB stimulus from: {self.mat_path}")
        try:
            stimulus = loadmat(self.mat_path, squeeze_me=True)
        except FileNotFoundError:
            logger.error(f"Could not find file: {self.mat_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to load .mat file: {e}")
            raise
        if self.verbose:
            logger.info("Successfully loaded MATLAB file!")

        images = np.array(stimulus['stimulus']['images']).ravel()[0].T
        frames_to_show = stimulus['stimulus']['seq'].ravel()[0]
        if self.verbose:
            logger.info(f"# image frames in file: {images.shape[0]}")
            logger.info(f"# frames to present: {len(frames_to_show)}")
        indexed_matrix = np.zeros((len(frames_to_show), images.shape[1], images.shape[2]), dtype=np.uint8)
        for i, frame in enumerate(frames_to_show):
            indexed_matrix[i] = images[frame - 1]

        lut = stimulus['stimulus']['cmap'].ravel()[0]
        if self.verbose:
            logger.info(f"LUT shape: {lut.shape}, dtype: {lut.dtype}")

        lut_max = lut.max()
        if lut_max > 1:
            if lut_max <= 255:
                if self.verbose:
                    logger.info("Normalizing LUT from 0-255 to 0-1")
                lut = lut / 255.0
            else:
                logger.warning(f"LUT maximum unusually high: {lut_max}")
        if self.verbose:
            logger.info("Scaling LUT to [-1,1] for PsychoPy")
        lut = (lut * 2.0) - 1.0
        if lut.min() < -1. or lut.max() > 1.:
            logger.warning(f"LUT has values outside [-1,1]: min={lut.min()}, max={lut.max()}")
        if self.verbose:
            logger.info(f"LUT after scaling: min={lut.min()}, max={lut.max()}")

        frame_duration = stimulus['stimulus']['seqtiming'].ravel()[0][1]
        if self.verbose:
            logger.info(f"Frame duration: {frame_duration:.4f} seconds")
            logger.info("Finished preprocessing MATLAB stimulus.")

        return indexed_matrix, lut, frame_duration

# ----------- Python Loader -----------
class PythonStimulusLoader(StimulusLoader):
    """Loads stimulus from Python/NumPy arrays."""
    def __init__(self, indexed_matrix: np.ndarray, lut: np.ndarray, frame_duration: float, verbose: bool = False):
        super().__init__(verbose)
        self.indexed_matrix = indexed_matrix
        self.lut = lut
        self.frame_duration = frame_duration

    def load(self):
        return self.indexed_matrix, self.lut, self.frame_duration

# ----------- Fixation Base and Variants -----------
class Fixation(ABC):
    """Abstract base class for fixation markers."""
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    @abstractmethod
    def draw(self) -> None:
        pass

    @abstractmethod
    def update(self, now: float = None) -> None:
        pass

class FixationDot(Fixation):
    """A colored dot fixation marker that occasionally changes color."""
    def __init__(
        self,
        win,
        radius: int = 8,
        colors: tuple = ('magenta', 'green'),
        color_switch_prob: float = 0.01,
        min_switch_interval: float = 2.0,
        verbose: bool = False
    ):
        super().__init__(verbose)
        self.win = win
        self.radius = radius
        self.colors = colors
        self.color_switch_prob = color_switch_prob
        self.current_color = colors[0]
        self.last_switch_time = None
        self.switch_log = []
        self.min_switch_interval = min_switch_interval
        self.circle = visual.Circle(win, radius=self.radius, fillColor=self.current_color,
                                   lineColor=self.current_color, pos=(0,0), units='pix')

    def update(self, now: float = None) -> None:
        if now is None:
            return
        if self.last_switch_time is None or (now - self.last_switch_time) >= self.min_switch_interval:
            if random.random() < self.color_switch_prob:
                self.current_color = self.colors[1] if self.current_color == self.colors[0] else self.colors[0]
                self.circle.fillColor = self.current_color
                self.circle.lineColor = self.current_color
                self.last_switch_time = now
                self.switch_log.append((now, self.current_color))
                if self.verbose:
                    logger.info(f"Fixation color switched to {self.current_color}")

    def draw(self) -> None:
        self.circle.draw()

class FixationCross(Fixation):
    """A colored cross fixation marker that occasionally changes color."""
    def __init__(
        self,
        win,
        size: int = 30,
        colors: tuple = ('magenta', 'green'),
        color_switch_prob: float = 0.01,
        min_switch_interval: float = 2.0,
        verbose: bool = False
    ):
        super().__init__(verbose)
        self.win = win
        self.size = size
        self.colors = colors
        self.color_switch_prob = color_switch_prob
        self.current_color = colors[0]
        self.last_switch_time = None
        self.switch_log = []
        self.min_switch_interval = min_switch_interval
        self.text = visual.TextStim(win, text='+', color=self.current_color,
                                   height=self.size, pos=(0,0))

    def update(self, now: float = None) -> None:
        if now is None:
            return
        if self.last_switch_time is None or (now - self.last_switch_time) >= self.min_switch_interval:
            if random.random() < self.color_switch_prob:
                self.current_color = self.colors[1] if self.current_color == self.colors[0] else self.colors[0]
                self.text.color = self.current_color
                self.last_switch_time = now
                self.switch_log.append((now, self.current_color))
                if self.verbose:
                    logger.info(f"Fixation color switched to {self.current_color}")

    def draw(self) -> None:
        self.text.draw()

# ----------- Reaction Time Analysis Helper -----------
def analyze_reaction_times(
    switch_log: list[tuple[float, str]],
    button_events: list[tuple[float, str]],
    min_rt: float = 0.3,
    max_rt: float = 3.0
) -> tuple[int, int, float, list[float]]:
    """
    Analyze reaction times between color switches and button presses.
    Returns (n_hits, n_switches, mean_rt, reaction_times).
    """
    n_switches = len(switch_log)
    n_hits = 0
    reaction_times = []
    button_events_sorted = sorted(button_events, key=lambda x: x[0])
    for switch_time, _ in switch_log:
        for btn_time, _ in button_events_sorted:
            dt = btn_time - switch_time
            if min_rt <= dt <= max_rt:
                n_hits += 1
                reaction_times.append(dt)
                break
    mean_rt = np.mean(reaction_times) if reaction_times else float('nan')
    return n_hits, n_switches, mean_rt, reaction_times

# ----------- Main Experiment Presenter -----------
class PRFStimulusPresenter:
    """
    Main class for presenting pRF stimuli using PsychoPy.
    Handles window creation, stimulus presentation, fixation, and logging.
    """
    def __init__(
        self,
        loader: StimulusLoader,
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

        # Mac external display fix: query pixel size with pyglet
        display = pyglet.canvas.get_display()
        screens = display.get_screens()
        if screen >= len(screens):
            logger.error(f"Screen {screen} not available.")
            raise RuntimeError(f"Screen {screen} not available")
        width, height = screens[screen].width, screens[screen].height
        if self.verbose:
            logger.info(f"Using screen {screen}: {width}x{height}px")

        # Load only indices and LUT
        self.indexed_matrix, self.lut, self.frame_duration = loader.load()
        self.nFrames = self.indexed_matrix.shape[0]
        self.screen = screen

        # Create PsychoPy window
        self.win = visual.Window(
            size=(width, height),
            units='pix',
            fullscr=True,
            screen=self.screen,
            color=[0,0,0],
        )
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
        else:
            logger.error(f"Invalid fixation_type: {fixation_type}")
            raise ValueError("fixation_type must be 'dot' or 'cross'")

        # Prepare image stimulus
        h, w = self.indexed_matrix.shape[1:3]
        dummy_rgb = np.zeros((h, w, 3), dtype=np.float32)
        self.img_stim = visual.ImageStim(
            self.win,
            image=dummy_rgb,
            units='pix',
            size=(w, h),
            colorSpace='rgb'
        )

    def run(
        self,
        subject: str,
        session: str,
        run: str,
        outdir: str,
        button_keys: list[str] = ['1', '2', '3', '4']
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
        core.wait(0.5)
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

            while frame_idx < self.nFrames:
                if kb.getKeys(keyList=[self.abort_key], waitRelease=False):
                    logger.info("Aborted by user.")
                    return

                t = global_clock.getTime()
                pressed = kb.getKeys(keyList=button_keys, waitRelease=False, clear=False)
                for key in pressed:
                    if key.name not in prev_button_state:
                        button_events.append((t, key.name))
                        prev_button_state.add(key.name)
                current_pressed = set(k.name for k in pressed)
                prev_button_state = prev_button_state & current_pressed

                if t >= (frame_idx * self.frame_duration):
                    idx = self.indexed_matrix[frame_idx]
                    rgb = self.lut[idx]
                    self.img_stim.image = rgb
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

            with open(log_fname, 'w', newline='') as f:
                writer = csv.writer(f, delimiter='\t')
                writer.writerow(['Event', 'Time', 'Value'])
                for idx, onset in enumerate(frame_onsets):
                    writer.writerow(['frame_onset', onset, idx])
                for t, color in getattr(self.fixation, 'switch_log', []):
                    writer.writerow(['fixation_color_switch', t, color])
                for t, key in button_events:
                    writer.writerow(['button_press', t, key])

                # --- Reaction time analysis ---
                switch_log = getattr(self.fixation, 'switch_log', [])
                n_hits, n_switches, mean_rt, _ = analyze_reaction_times(switch_log, button_events)
                hit_ratio = (n_hits / n_switches * 100) if n_switches > 0 else 0

                result1 = f"[stim4prf][RESULT] {n_hits}/{n_switches} ({hit_ratio:.1f}%) color switches were followed by a button press in 0.3–3s."
                result2 = f"[stim4prf][RESULT] Mean reaction time: {mean_rt:.3f} s"
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

# ----------- USAGE EXAMPLES -----------
if __name__ == "__main__":
    loader = MatlabStimulusLoader('./bar_smooth_test_stimulus.mat', verbose=False)
    presenter = PRFStimulusPresenter(
        loader,
        fixation_type='dot',
        screen=1,
        verbose=True,
        trigger_key='6',
        abort_key='escape',
        fixation_color_switch_prob=0.01,
        fixation_cross_size=30,
        fixation_dot_radius=8,
        min_switch_interval=2.0,
        frame_log_interval=100,
        end_screen_wait=2.0
    )
    presenter.run(subject='01', session='01', run='01', outdir='./bids_logs')

# # For Python/NumPy (where you have an indexed_matrix and lut already loaded):
# # loader = PythonStimulusLoader(indexed_matrix, lut, frame_duration=0.125)
# # presenter = PRFStimulusPresenter(loader, fixation_type='cross', screen=0)
# # presenter.run(subject='99', session='01', run='01', outdir='./bids_logs')
