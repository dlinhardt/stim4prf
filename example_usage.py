from stim4prf import (
    MatlabStimulusLoader,
    HDF5StimulusLoader,
    PRFStimulusPresenter
)
import os

# For legacy MATLAB files:
loader = MatlabStimulusLoader(os.path.join('stimuli', 'bar_smooth_test_stimulus.mat'), verbose=False)

# For the new HDF5 files:
# loader = HDF5StimulusLoader(os.path.join('stimuli', 'bar_smooth_size-1080_dur-300_ecc-10.6_width-2_tr1_images.h5'), verbose=False)

# Create the stimulus presenter with the desired parameters
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

# Run the presenter with specified subject, session, and run identifiers
presenter.run(subject='01', session='01', run='01', outdir=os.path.join('.', 'logs'))