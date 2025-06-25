import os

from stim4prf import HDF5StimulusLoader, MatlabStimulusLoader, PRFStimulusPresenter
from stim4prf.eyetracking import EyeLinkTracker
from stim4prf.fixation import ABCTargetFixation, FixationCross, FixationDot

# --- Choose your loader ---
# For legacy MATLAB files:
# loader = MatlabStimulusLoader(os.path.join('stimuli', 'bar_smooth_test_stimulus.mat'), verbose=True)

# For HDF5 files:
loader = HDF5StimulusLoader(
    os.path.join(
        ".",
        "stimuli",
        "bar_smooth_size-1080_dur-300_ecc-10.6_width-2_tr1_images.h5",
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
eyetracker_class = None  # or EyeLinkTracker if connected
eyetracker_kwargs = {
    "dummy_mode": False,  # Set True for testing without hardware
}

# --- Create the stimulus presenter with all options ---
presenter = PRFStimulusPresenter(
    loader=loader,  # pass the loader instance
    fixation_class=fixation_class,  # pass the fixation class
    fixation_kwargs=fixation_kwargs,
    eyetracker_class=eyetracker_class,  # pass the eyetracker class
    eyetracker_kwargs=eyetracker_kwargs,
    screen=1,  # Which screen to use (0=primary)
    verbose=True,  # Print extra info
    trigger_key="6",  # Key the scanner sends as trigger
    abort_key="escape",  # Key to abort run
    frame_log_interval=100,  # Log every N frames
    end_screen_wait=2.0,  # Seconds to show end screen
    flipVert=False,  # Flip images vertically
    flipHoriz=False,  # Flip images horizontally
)

# --- Run the presenter ---
subject = "01"
session = "01"
runs = ["01", "02"]  # List of runs to execute

for run in runs:
    presenter.run(
        subject=subject,
        session=session,
        run=run,
        outdir=os.path.join(".", "logs"),
        button_keys=["1", "2", "3", "4"],  # List of buttons to accept during the run
    )
