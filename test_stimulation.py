from abc import ABC, abstractmethod
import os
import numpy as np
from datetime import datetime
from psychopy import visual, core, logging
from psychopy.hardware import keyboard
from scipy.io import loadmat
import pyglet

# ----------- Stimulus Loader Abstract Base -----------
class StimulusLoader(ABC):
    @abstractmethod
    def load(self):
        """Return (indexed_matrix, lut, frame_duration)"""
        pass

# ----------- MATLAB Loader -----------
class MatlabStimulusLoader(StimulusLoader):
    def __init__(self, mat_path):
        self.mat_path = mat_path

    def load(self):
        stimulus = loadmat(self.mat_path, squeeze_me=True)
        images = np.array(stimulus['stimulus']['images']).ravel()[0].T
        frames_to_show = stimulus['stimulus']['seq'].ravel()[0]
        indexed_matrix = np.zeros((len(frames_to_show), images.shape[1], images.shape[2]), dtype=np.uint8)
        for i, frame in enumerate(frames_to_show):
            indexed_matrix[i] = images[frame - 1]
        lut = stimulus['stimulus']['cmap'].ravel()[0]
        frame_duration = stimulus['stimulus']['seqtiming'].ravel()[0][1]
        return indexed_matrix, lut, frame_duration

# ----------- Python Loader -----------
class PythonStimulusLoader(StimulusLoader):
    def __init__(self, indexed_matrix, lut, frame_duration):
        self.indexed_matrix = indexed_matrix  # (nFrames, h, w)
        self.lut = lut                        # (nColors, 3)
        self.frame_duration = frame_duration

    def load(self):
        return self.indexed_matrix, self.lut, self.frame_duration

# ----------- Fixation Base and Variants -----------
class Fixation(ABC):
    @abstractmethod
    def draw(self):
        pass

    @abstractmethod
    def update(self):
        pass

class FixationDot(Fixation):
    def __init__(self, win, radius=8, colors=('magenta', 'green')):
        self.win = win
        self.radius = radius
        self.colors = colors
        self.current_color = colors[0]
        self.circle = visual.Circle(win, radius=self.radius, fillColor=self.current_color,
                                   lineColor=self.current_color, pos=(0,0), units='pix')

    def update(self):
        import random
        if random.random() < 0.01:
            self.current_color = self.colors[1] if self.current_color == self.colors[0] else self.colors[0]
            self.circle.fillColor = self.current_color
            self.circle.lineColor = self.current_color

    def draw(self):
        self.circle.draw()

class FixationCross(Fixation):
    def __init__(self, win, size=30, colors=('magenta', 'green')):
        self.win = win
        self.size = size
        self.colors = colors
        self.current_color = colors[0]
        self.text = visual.TextStim(win, text='+', color=self.current_color,
                                   height=self.size, pos=(0,0))

    def update(self):
        import random
        if random.random() < 0.01:
            self.current_color = self.colors[1] if self.current_color == self.colors[0] else self.colors[0]
            self.text.color = self.current_color

    def draw(self):
        self.text.draw()

# ----------- Main Experiment Presenter -----------
class PRFStimulusPresenter:
    def __init__(self, loader: StimulusLoader, fixation_type='dot', screen=0):
        # --- Mac external display fix: query true pixel size with pyglet ---
        display = pyglet.canvas.get_display()
        screens = display.get_screens()
        if screen >= len(screens):
            raise RuntimeError(f"Screen {screen} not available")
        width, height = screens[screen].width, screens[screen].height

        # Load only indices and LUT (resource efficient)
        self.indexed_matrix, self.lut, self.frame_duration = loader.load()
        self.nFrames = self.indexed_matrix.shape[0]
        self.screen = screen

        # Window setup (robust for Mac/Retina/external)
        self.win = visual.Window(
            size=(width, height),
            units='pix',
            fullscr=True,
            screen=self.screen,
            color=[0,0,0],
            winType='glfw',
            useRetina=False
        )
        self.fixation_type = fixation_type
        if fixation_type == 'dot':
            self.fixation = FixationDot(self.win)
        elif fixation_type == 'cross':
            self.fixation = FixationCross(self.win)
        else:
            raise ValueError("fixation_type must be 'dot' or 'cross'")

        # Prepare a single ImageStim object (blank at init)
        h, w = self.indexed_matrix.shape[1:3]
        dummy_rgb = np.zeros((h, w, 3), dtype=np.float32)
        self.img_stim = visual.ImageStim(
            self.win,
            image=dummy_rgb,
            units='pix',
            size=(w, h),
            colorSpace='rgb1'
        )

    def run(self, subject, session, run, outdir):
        import csv

        # BIDS log file name
        timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        log_fname = os.path.join(
            outdir,
            f"sub-{subject}_ses-{session}_run-{run}_{timestamp}.tsv"
        )
        os.makedirs(outdir, exist_ok=True)

        # Wait for scanner trigger
        info_text = visual.TextStim(self.win, text="Waiting for scanner...\nPress '6' to begin",
                                   color=[1,1,1], height=30)
        info_text.draw()
        self.win.flip()
        kb = keyboard.Keyboard()
        kb.clearEvents()
        core.wait(0.5)  # Allow window to get focus

        while True:
            keys = kb.getKeys(keyList=['6', 'escape'], waitRelease=False)
            if keys:
                if keys[0].name == 'escape':
                    self.win.close()
                    core.quit()
                elif keys[0].name == '6':
                    break
            core.wait(0.001)

        # Main presentation loop (efficient: only 1 frame decoded at a time)
        global_clock = core.Clock()
        frame_onsets = []
        frame_idx = 0

        while frame_idx < self.nFrames:
            if kb.getKeys(keyList=['escape'], waitRelease=False):
                self.win.close()
                core.quit()
            t = global_clock.getTime()
            if t >= (frame_idx * self.frame_duration):
                idx = self.indexed_matrix[frame_idx]
                rgb = self.lut[idx]
                rgb_float = rgb.astype(np.float32) / 255.0
                rgb_rescaled = (rgb_float * 2.0) - 1.0
                self.img_stim.image = rgb_rescaled
                self.img_stim.draw()
                self.fixation.update()
                self.fixation.draw()
                self.win.flip()
                frame_onsets.append(t)
                frame_idx += 1
            else:
                core.wait(0.001)

        # End message
        final_text = visual.TextStim(self.win, text="Experiment complete.\nThank you!",
                                    color=[1,1,1], height=30)
        final_text.draw()
        self.win.flip()
        core.wait(2.0)
        self.win.close()

        # Save timing log
        with open(log_fname, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(['FrameIndex', 'OnsetTime'])
            for idx, onset in enumerate(frame_onsets):
                writer.writerow([idx, onset])

# ----------- USAGE EXAMPLES -----------
# For MATLAB stimuli:
if __name__ == "__main__":
    loader = MatlabStimulusLoader('./bar_smooth_test_stimulus.mat')
    presenter = PRFStimulusPresenter(loader, fixation_type='dot', screen=0)
    presenter.run(subject='01', session='01', run='01', outdir='./bids_logs')
    # presenter.run(subject='01', session='01', run='02', outdir='./bids_logs')

# # For Python/NumPy (where you have an indexed_matrix and lut already loaded):
# # loader = PythonStimulusLoader(indexed_matrix, lut, frame_duration=0.125)
# # presenter = PRFStimulusPresenter(loader, fixation_type='cross', screen=0)
# # presenter.run(subject='99', session='01', run='01', outdir='./bids_logs')
