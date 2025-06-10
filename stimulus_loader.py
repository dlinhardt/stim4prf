from abc import ABC, abstractmethod
from scipy.io import loadmat
import numpy as np
from . import logger

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