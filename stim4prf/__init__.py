import logging

logging.basicConfig(
    level=logging.INFO,
    format='[stim4prf][%(levelname)s] %(message)s'
)
logger = logging.getLogger("stim4prf")

from .stim4prf.stimulus_loader import StimulusLoader, MatlabStimulusLoader, PythonStimulusLoader
from .stim4prf.fixation import Fixation, FixationDot, FixationCross
from .stim4prf.reaction_time import analyze_reaction_times
from .presenter import PRFStimulusPresenter