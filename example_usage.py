import os

from stim4prf import HDF5StimulusLoader, MatlabStimulusLoader, PRFStimulusPresenter
from stim4prf.eyetracking import EyeLinkTracker
from stim4prf.fixation import FixationDot

# For legacy MATLAB files:
# loader = MatlabStimulusLoader(os.path.join('stimuli', 'bar_smooth_test_stimulus.mat'), verbose=False)

# For the new HDF5 files:
loader = HDF5StimulusLoader(
    os.path.join(
        ".",
        "stimuli",
        "bar_smooth_size-1080_dur-300_ecc-10.6_width-2_tr1_images.h5",
    ),
    verbose=False,
)

# Create the stimulus presenter with the desired parameters
presenter = PRFStimulusPresenter(
    loader,
    fixation_class=FixationDot,
    fixation_kwargs={
        "radius": 8,
        "color_switch_prob": 0.01,
        "min_switch_interval": 2.0,
    },
    screen=1,
    verbose=True,
    trigger_key="6",
    abort_key="escape",
    end_screen_wait=2.0,
    flipVert=False,
    flipHoriz=False,
    eyetracker_class=EyeLinkTracker,
    eyetracker_kwargs={"dummy_mode": False},
)

# Run the presenter with specified subject, session, and run identifiers
presenter.run(
    subject="01",
    session="01",
    run="01",
    outdir=os.path.join(".", "logs"),
)

presenter.run(
    subject="01",
    session="01",
    run="02",
    outdir=os.path.join(".", "logs"),
)
