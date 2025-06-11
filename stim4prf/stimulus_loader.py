from abc import ABC, abstractmethod
from scipy.io import loadmat
import numpy as np
import h5py
from .. import logger

# ----------- Stimulus Loader Abstract Base -----------
class StimulusLoader(ABC):
    """Abstract base class for stimulus loaders."""
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    @abstractmethod
    def load(self):
        """Return (indexed_matrix, lut, frame_duration)"""
        pass

    @staticmethod
    def normalize_lut(lut, verbose=False):
        lut_max = lut.max()
        if lut_max > 1:
            if lut_max <= 255:
                if verbose:
                    logger.info("Normalizing LUT from 0-255 to 0-1")
                lut = lut / 255.0
            else:
                logger.warning(f"LUT maximum unusually high: {lut_max}")
        if verbose:
            logger.info("Scaling LUT to [-1,1] for PsychoPy")
        return lut

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
        lut = stimulus['stimulus']['cmap'].ravel()[0]
        if self.verbose:
            logger.info(f"# image frames in file: {images.shape[0]}")
            logger.info(f"# frames to present: {len(frames_to_show)}")
            logger.info(f"LUT shape: {lut.shape}, dtype: {lut.dtype}")

        indexed_matrix = images[frames_to_show - 1]

        lut = self.normalize_lut(lut, self.verbose)

        frame_duration = stimulus['stimulus']['seqtiming'].ravel()[0][1]

        if self.verbose:
            logger.info(f"Frame duration: {frame_duration:.4f} seconds")
            logger.info("Finished preprocessing MATLAB stimulus.")

        return indexed_matrix, lut, frame_duration

# ----------- HDF5 Loader -----------
class HDF5StimulusLoader(StimulusLoader):
    """Loads stimulus from an HDF5 (.h5) file."""
    def __init__(self, h5_path: str, verbose: bool = False):
        super().__init__(verbose)
        self.h5_path = h5_path

    def load(self):
        if self.verbose:
            logger.info(f"Loading HDF5 stimulus from: {self.h5_path}")
        try:
            with h5py.File(self.h5_path, 'r') as f:
                images = np.array(f['images'])
                frames_to_show = np.array(f['seq']).astype(int).ravel()
                lut = np.array(f['cmap'])
                params = dict(f['params'].attrs)
        except FileNotFoundError:
            logger.error(f"Could not find file: {self.h5_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to load .h5 file: {e}")
            raise

        if self.verbose:
            logger.info(f"# image frames in file: {images.shape[0]}")
            logger.info(f"# frames to present: {len(frames_to_show)}")
            logger.info(f"LUT shape: {lut.shape}, dtype: {lut.dtype}")

        indexed_matrix = images[frames_to_show]

        lut = self.normalize_lut(lut, self.verbose)

        frame_duration =  1 / params['tempFreq']

        if self.verbose:
            logger.info(f"Frame duration: {frame_duration:.4f} seconds")
            logger.info("Finished preprocessing HDF5 stimulus.")

        return indexed_matrix, lut, frame_duration