import os

from psychopy import core, data, gui, hardware

from stim4prf import HDF5StimulusLoader, MatlabStimulusLoader, PRFStimulusPresenter
from stim4prf.eyetracking import EyeLinkTracker, MRCEyeTracking
from stim4prf.fixation import ABCTargetFixation, FixationCross, FixationDot

subject = 'test'
session = '001'

# --- Choose your loader ---
# For HDF5 files:
loader = HDF5StimulusLoader(
    os.path.join(
        ".",
        "stimuli",
        "bar_smooth_size-1024_dur-300_ecc-6_width-2_tr2_images.h5",
    ),
    verbose=True,
)

# --- Choose fixation class and options ---
fixation_class = FixationDot  # or FixationCross, ABCTargetFixation
fixation_kwargs = {
    "size": 20,  # pix
    "color_switch_prob": 0.01,  # Probability of color switch per frame
    "min_switch_interval": 2.0,  # s no color switch after switch
    "colors": ("magenta", "green"),  # Colors to switch between
    "verbose": True,  # Print extra info
}

# --- Eyetracker options ---
eyetracker_class = EyeLinkTracker  # or EyeLinkTracker if connected
eyetracker_kwargs = {
    "dummy_mode": False,  # Set True for testing without hardware
    "outdir": os.path.join(".", "eyetracker"),  # Directory to save eyetracker data
    "skip_calibration": False, # when eyetracking is not working well we can skip callibration and drif correction
    "skip_driftcorrection": True, # when eyetracking is not working well we can skip the drift correction
}

# --- Create the stimulus presenter with all options ---
presenter = PRFStimulusPresenter(
    loader=loader,  # pass the loader instance
    fixation_class=fixation_class,  # pass the fixation class
    fixation_kwargs=fixation_kwargs,
    eyetracker_class=eyetracker_class,  # pass the eyetracker class
    eyetracker_kwargs=eyetracker_kwargs,
    screen=1,  # Which screen to use (0=primary)
    trigger_key="6",  # Key the scanner sends as trigger
    abort_key="escape",  # Key to abort run
    frame_log_interval=100,  # Log every N frames
    end_screen_wait=2.0,  # Seconds to show end screen
    flipVert=False,  # Flip images vertically
    flipHoriz=False,  # Flip images horizontally
    verbose=True,  # Print extra info
)

if __name__ == "__main__":
    runs = ['01', '02']
    for run in runs:
        presenter.run(
            subject=subject,
            session=session,
            run=run,
            outdir=os.path.join(".", "data"),
            button_keys=[
                "1",
                "2",
                "3",
                "4",
            ],  # List of buttons to accept during the run
        )
