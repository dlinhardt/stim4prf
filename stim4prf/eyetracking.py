# eyetracker_base.py
import os
import platform
from abc import ABC, abstractmethod
from datetime import datetime

import h5py
import numpy as np
import pylink
from psychopy import event, visual

from stim4prf import logger

from .EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy


# ----------- Eyetracker Base -----------
class EyeTrackerBase(ABC):
    @abstractmethod
    def calibrate(self, win):
        pass

    @abstractmethod
    def drift_correction(self):
        pass

    @abstractmethod
    def start_recording(self):
        pass

    @abstractmethod
    def stop_recording(self):
        pass

    @abstractmethod
    def send_message(self, msg):
        pass

    @abstractmethod
    def download_data(self, fname):
        pass

    @abstractmethod
    def save_hdf5(self, fname):
        pass


# ----------- EyeLink Tracker Implementation -----------
class EyeLinkTracker(EyeTrackerBase):
    """
    EyeLink tracker integration for PsychoPy.
    Handles calibration, drift correction, recording, event marking, and EDF download.
    """

    def __init__(self, outdir, dummy_mode=False):
        self.outdir = outdir
        os.makedirs(outdir, exist_ok=True)
        self.dummy_mode = dummy_mode
        self.el_tracker = None

    def connect(self):
        if self.dummy_mode:
            self.el_tracker = pylink.EyeLink(None)
            logger.info("Initialized dummy EyeLink tracker.")
        else:
            try:
                self.el_tracker = pylink.EyeLink("100.1.1.1")
                logger.info("Successfully connected to EyeLink tracker.")
            except:
                logger.exception("Could not connect to eyetracker!")
                self.win.close()
                raise

        timestamp = datetime.now().strftime("T%H%M%S")
        self.edf_file = timestamp + ".edf"
        self.el_tracker.openDataFile(self.edf_file)
        self.el_tracker.setOfflineMode()
        self.el_tracker.sendCommand("calibration_type = HV13")

    def calibrate(self, win):
        self.win = win
        self.scn_width, self.scn_height = self.win.size
        el_coords = (
            f"screen_pixel_coords = 0 0 {self.scn_width - 1} {self.scn_height - 1}"
        )
        self.el_tracker.sendCommand(el_coords)
        dv_coords = f"DISPLAY_COORDS  0 0 {self.scn_width - 1} {self.scn_height - 1}"
        self.el_tracker.sendMessage(dv_coords)
        genv = EyeLinkCoreGraphicsPsychoPy(self.el_tracker, self.win)
        genv.setTargetType("circle")
        genv.setCalibrationSounds("", "", "")
        pylink.openGraphicsEx(genv)

        if not self.dummy_mode:
            et_calib_msg = (
                "Press ENTER to calibrate tracker or ESC to jump to drift correction!"
            )
            msg = visual.TextStim(self.win, et_calib_msg, color=[1, 1, 1], height=30)
            msg.draw()
            self.win.flip()
            try:
                self.el_tracker.doTrackerSetup()
            except RuntimeError as err:
                logger.error(err)
                self.el_tracker.exitCalibration()

    def drift_correction(self):
        self.el_tracker.doDriftCorrect(
            int(self.scn_width / 2), int(self.scn_height / 2), 1, 1
        )

    def start_recording(self):
        self.el_tracker.setOfflineMode()
        self.el_tracker.startRecording(1, 1, 1, 1)
        pylink.pumpDelay(100)

    def stop_recording(self):
        pylink.pumpDelay(100)
        self.el_tracker.stopRecording()

    def send_message(self, msg):
        self.el_tracker.sendMessage(msg)

    def download_data(self, fname):
        local_edf = os.path.join(self.outdir, fname.replace(".tsv", ".edf"))
        self.el_tracker.setOfflineMode()
        self.el_tracker.sendCommand("clear_screen 0")
        pylink.msecDelay(500)
        self.el_tracker.closeDataFile()
        try:
            self.el_tracker.receiveDataFile(self.edf_file, local_edf)
            logger.info(f"Successfully downloaded EDF file to {local_edf}")
        except RuntimeError as err:
            logger.error(err)
        self.el_tracker.close()
        logger.debug("Closed connection to EyeLink tracker.")

    def save_hdf5(self, fname):
        """
        Save event log and metadata to HDF5.
        Gaze data is not included here (use EDF for full data).
        """
        pass
        filename = os.path.join(self.outdir, fname.replace(".tsv", ".h5"))
        with h5py.File(filename, "w") as f:
            pass
