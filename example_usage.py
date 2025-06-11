import sys
sys.path.append('/Users/fmri')
from stim4prf import (
    MatlabStimulusLoader,
    PRFStimulusPresenter
)
import os

if __name__ == "__main__":
    loader = MatlabStimulusLoader(os.path.join('.', 'bar_smooth_test_stimulus.mat'), verbose=False)
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
    presenter.run(subject='01', session='01', run='01', outdir=os.path.join('.', 'bids_logs'))

# # For Python/NumPy (where you have an indexed_matrix and lut already loaded):
# # loader = PythonStimulusLoader(indexed_matrix, lut, frame_duration=0.125)
# # presenter = PRFStimulusPresenter(loader, fixation_type='cross', screen=0)
# # presenter.run(subject='99', session='01', run='01', outdir='./bids_logs')