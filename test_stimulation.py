from abc import ABC, abstractmethod
import os
import numpy as np
from datetime import datetime
from psychopy import visual, core
from psychopy.hardware import keyboard
from scipy.io import loadmat
import pyglet
import random  # moved import to top

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
        # Load MATLAB .mat file containing stimulus
        if self.verbose:
            print(f"[stim4prf] Loading MATLAB stimulus from: {self.mat_path}")
        try:
            stimulus = loadmat(self.mat_path, squeeze_me=True)
        except FileNotFoundError:
            print(f"[stim4prf][ERROR] Could not find file: {self.mat_path}")
            raise
        except Exception as e:
            print(f"[stim4prf][ERROR] Failed to load .mat file: {e}")
            raise
        if self.verbose:
            print(f"[stim4prf] Successfully loaded MATLAB file!")

        # Extract images and sequence
        images = np.array(stimulus['stimulus']['images']).ravel()[0].T
        frames_to_show = stimulus['stimulus']['seq'].ravel()[0]
        if self.verbose:
            print(f"[stim4prf] # image frames in file: {images.shape[0]}")
            print(f"[stim4prf] # frames to present: {len(frames_to_show)}")
        indexed_matrix = np.zeros((len(frames_to_show), images.shape[1], images.shape[2]), dtype=np.uint8)
        for i, frame in enumerate(frames_to_show):
            indexed_matrix[i] = images[frame - 1]

        # Extract and normalize color lookup table (LUT)
        lut = stimulus['stimulus']['cmap'].ravel()[0]
        if self.verbose:
            print(f"[stim4prf] LUT shape: {lut.shape}, dtype: {lut.dtype}")

        lut_max = lut.max()
        if lut_max > 1:
            if lut_max <= 255:
                if self.verbose:
                    print(f"[stim4prf] Normalizing LUT from 0-255 to 0-1")
                lut = lut / 255.0
            else:
                print(f"[stim4prf][WARN] LUT maximum unusually high: {lut_max}")
        if self.verbose:
            print(f"[stim4prf] Scaling LUT to [-1,1] for PsychoPy")
        lut = (lut * 2.0) - 1.0
        if lut.min() < -1. or lut.max() > 1.:
            print(f"[stim4prf][WARN] LUT has values outside [-1,1]: min={lut.min()}, max={lut.max()}")
        if self.verbose:
            print(f"[stim4prf] LUT after scaling: min={lut.min()}, max={lut.max()}")

        # Get frame duration
        frame_duration = stimulus['stimulus']['seqtiming'].ravel()[0][1]
        if self.verbose:
            print(f"[stim4prf] Frame duration: {frame_duration:.4f} seconds")
            print(f"[stim4prf] Finished preprocessing MATLAB stimulus.")

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
        # Return preloaded stimulus data
        return self.indexed_matrix, self.lut, self.frame_duration

# ----------- Fixation Base and Variants -----------
class Fixation(ABC):
    """Abstract base class for fixation markers."""
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    @abstractmethod
    def draw(self):
        pass

    @abstractmethod
    def update(self):
        pass

class FixationDot(Fixation):
    """A colored dot fixation marker that occasionally changes color."""
    def __init__(
        self,
        win,
        radius: int = 8,
        colors: tuple = ('magenta', 'green'),
        color_switch_prob: float = 0.01,
        verbose: bool = False
    ):
        super().__init__(verbose)
        self.win = win
        self.radius = radius
        self.colors = colors
        self.color_switch_prob = color_switch_prob
        self.current_color = colors[0]
        self.last_switch_time = None  # Track last switch time
        self.switch_log = []          # Store (time, new_color)
        self.min_switch_interval = 2.0  # Minimum time between color changes (seconds)
        self.circle = visual.Circle(win, radius=self.radius, fillColor=self.current_color,
                                   lineColor=self.current_color, pos=(0,0), units='pix')

    def update(self, now=None):
        # Occasionally switch color, but only if min_switch_interval has passed
        if now is None:
            return
        if self.last_switch_time is None or (now - self.last_switch_time) >= self.min_switch_interval:
            if random.random() < self.color_switch_prob:
                self.current_color = self.colors[1] if self.current_color == self.colors[0] else self.colors[0]
                self.circle.fillColor = self.current_color
                self.circle.lineColor = self.current_color
                self.last_switch_time = now
                self.switch_log.append((now, self.current_color))

    def draw(self):
        self.circle.draw()

class FixationCross(Fixation):
    """A colored cross fixation marker that occasionally changes color."""
    def __init__(
        self,
        win,
        size: int = 30,
        colors: tuple = ('magenta', 'green'),
        color_switch_prob: float = 0.01,
        verbose: bool = False
    ):
        super().__init__(verbose)
        self.win = win
        self.size = size
        self.colors = colors
        self.color_switch_prob = color_switch_prob
        self.current_color = colors[0]
        self.last_switch_time = None  # Track last switch time
        self.switch_log = []          # Store (time, new_color)
        self.min_switch_interval = 2.0  # Minimum time between color changes (seconds)
        self.text = visual.TextStim(win, text='+', color=self.current_color,
                                   height=self.size, pos=(0,0))

    def update(self, now=None):
        # Occasionally switch color, but only if min_switch_interval has passed
        if now is None:
            return
        if self.last_switch_time is None or (now - self.last_switch_time) >= self.min_switch_interval:
            if random.random() < self.color_switch_prob:
                self.current_color = self.colors[1] if self.current_color == self.colors[0] else self.colors[0]
                self.text.color = self.current_color
                self.last_switch_time = now
                self.switch_log.append((now, self.current_color))

    def draw(self):
        self.text.draw()

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
    ):
        self.verbose = verbose
        self.trigger_key = trigger_key
        self.abort_key = abort_key

        # Mac external display fix: query pixel size with pyglet
        display = pyglet.canvas.get_display()
        screens = display.get_screens()
        if screen >= len(screens):
            print(f"[stim4prf][ERROR] Screen {screen} not available.")
            raise RuntimeError(f"Screen {screen} not available")
        width, height = screens[screen].width, screens[screen].height
        if self.verbose:
            print(f"[stim4prf] Using screen {screen}: {width}x{height}px")

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
                verbose=self.verbose
            )
        elif fixation_type == 'cross':
            self.fixation = FixationCross(
                self.win,
                size=fixation_cross_size,
                color_switch_prob=fixation_color_switch_prob,
                verbose=self.verbose
            )
        else:
            print(f"[stim4prf][ERROR] Invalid fixation_type: {fixation_type}")
            raise ValueError("fixation_type must be 'dot' or 'cross'")

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
        button_keys: list = ['1', '2', '3', '4']  # Add button keys to monitor
    ):
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

        # Show waiting screen for scanner trigger
        info_text = visual.TextStim(self.win, text=f"Waiting for scanner...\nPress '{self.trigger_key}' to begin",
                                   color=[1,1,1], height=30)
        info_text.draw()
        self.win.flip()
        kb = keyboard.Keyboard()
        kb.clearEvents()
        core.wait(0.5)
        if self.verbose:
            print("[stim4prf] Awaiting scanner trigger...")

        # Wait for trigger key or abort key
        try:
            while True:
                keys = kb.getKeys(keyList=[self.trigger_key, self.abort_key], waitRelease=False)
                if keys:
                    if keys[0].name == self.abort_key:
                        print("[stim4prf] Aborted by user.")
                        return
                    elif keys[0].name == self.trigger_key:
                        break
                core.wait(0.001)
            if self.verbose:
                print("[stim4prf] Scanner trigger received, starting presentation.")

            global_clock = core.Clock()
            frame_onsets = []
            button_events = []  # Store (time, key)
            prev_button_state = set()

            frame_idx = 0

            # Main stimulus presentation loop
            while frame_idx < self.nFrames:
                # Abort check
                if kb.getKeys(keyList=[self.abort_key], waitRelease=False):
                    print("[stim4prf] Aborted by user.")
                    return

                t = global_clock.getTime()

                # Button press monitoring (log all new presses)
                pressed = kb.getKeys(keyList=button_keys, waitRelease=False, clear=False)
                for key in pressed:
                    # Only log new presses (not held keys)
                    if key.name not in prev_button_state:
                        button_events.append((t, key.name))
                        prev_button_state.add(key.name)
                # Remove keys that are no longer pressed
                current_pressed = set(k.name for k in pressed)
                prev_button_state = prev_button_state & current_pressed

                if t >= (frame_idx * self.frame_duration):
                    idx = self.indexed_matrix[frame_idx]
                    rgb = self.lut[idx]
                    self.img_stim.image = rgb
                    self.img_stim.draw()
                    # Pass current time to fixation update for color switch logging
                    self.fixation.update(now=t)
                    self.fixation.draw()
                    self.win.flip()
                    frame_onsets.append(t)
                    frame_idx += 1
                    if self.verbose and frame_idx % self.frame_log_interval == 0:
                        print(f"[stim4prf] Presented frame {frame_idx}/{self.nFrames}")
                else:
                    core.wait(0.001)

            # Show end screen
            final_text = visual.TextStim(self.win, text="Experiment complete.\nThank you!",
                                        color=[1,1,1], height=30)
            final_text.draw()
            self.win.flip()
            core.wait(self.end_screen_wait)

            # Write timing log (frames, color switches, button presses)
            with open(log_fname, 'w', newline='') as f:
                writer = csv.writer(f, delimiter='\t')
                writer.writerow(['Event', 'Time', 'Value'])
                for idx, onset in enumerate(frame_onsets):
                    writer.writerow(['frame_onset', onset, idx])
                for t, color in getattr(self.fixation, 'switch_log', []):
                    writer.writerow(['fixation_color_switch', t, color])
                for t, key in button_events:
                    writer.writerow(['button_press', t, key])
            if self.verbose:
                print(f"[stim4prf] Saved timing log: {log_fname}")
        except Exception as e:
            print(f"[stim4prf][ERROR] Exception during run: {e}")
            raise
        finally:
            if hasattr(self, 'win') and self.win:
                self.win.close()

# ----------- USAGE EXAMPLES -----------
if __name__ == "__main__":
    # Example usage with MATLAB loader
    loader = MatlabStimulusLoader('./bar_smooth_test_stimulus.mat', verbose=False)
    presenter = PRFStimulusPresenter(
        loader,
        fixation_type='dot',
        screen=1,
        verbose=False,
        trigger_key='6',           # configurable trigger key
        abort_key='escape',        # configurable abort key
        fixation_color_switch_prob=0.01,  # configurable color switch probability
        fixation_cross_size=30,    # configurable cross size
        fixation_dot_radius=8     # configurable dot radius
    )
    presenter.run(subject='01', session='01', run='01', outdir='./bids_logs')

# # For Python/NumPy (where you have an indexed_matrix and lut already loaded):
# # loader = PythonStimulusLoader(indexed_matrix, lut, frame_duration=0.125)
# # presenter = PRFStimulusPresenter(loader, fixation_type='cross', screen=0)
# # presenter.run(subject='99', session='01', run='01', outdir='./bids_logs')
