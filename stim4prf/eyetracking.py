# eyetracker_base.py
import pylink
import os
import platform
from abc import ABC, abstractmethod
from EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy
import h5py
import numpy as np

class EyeTrackerBase(ABC):
    @abstractmethod
    def calibrate(self):
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
    def download_data(self):
        pass

    @abstractmethod
    def save_hdf5(self, filename, **kwargs):
        pass

class EyeLinkTracker(EyeTrackerBase):
    """
    EyeLink tracker integration for PsychoPy.
    Handles calibration, drift correction, recording, event marking, and EDF download.
    """
    def __init__(self, win, edf_file, session_folder, dummy_mode=False):
        self.win = win
        self.edf_file = edf_file
        self.session_folder = session_folder
        self.dummy_mode = dummy_mode
        self.el_tracker = None
        self.scn_width, self.scn_height = win.size

    def connect(self):
        if self.dummy_mode:
            self.el_tracker = pylink.EyeLink(None)
        else:
            self.el_tracker = pylink.EyeLink("100.1.1.1")
        self.el_tracker.openDataFile(self.edf_file)
        # Set up tracker parameters (can be expanded as needed)
        self.el_tracker.setOfflineMode()
        self.el_tracker.sendCommand("calibration_type = HV13")
        el_coords = f"screen_pixel_coords = 0 0 {self.scn_width - 1} {self.scn_height - 1}"
        self.el_tracker.sendCommand(el_coords)
        dv_coords = f"DISPLAY_COORDS  0 0 {self.scn_width - 1} {self.scn_height - 1}"
        self.el_tracker.sendMessage(dv_coords)

    def calibrate(self):
        # Set up graphics environment for calibration
        genv = EyeLinkCoreGraphicsPsychoPy(self.el_tracker, self.win)
        foreground_color = (-1, -1, -1)
        background_color = self.win.color
        genv.setCalibrationColors(foreground_color, background_color)
        genv.setTargetType('circle')
        genv.setCalibrationSounds('', '', '')
        if 'Darwin' in platform.system():
            genv.fixMacRetinaDisplay()
        pylink.openGraphicsEx(genv)
        # Run calibration
        self.el_tracker.doTrackerSetup()

    def drift_correction(self):
        # Center of the screen
        self.el_tracker.doDriftCorrect(
            int(self.scn_width / 2),
            int(self.scn_height / 2),
            1, 1
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

    def download_data(self):
        # Download EDF file from Host PC to local session folder
        local_edf = os.path.join(self.session_folder, self.edf_file)
        self.el_tracker.closeDataFile()
        self.el_tracker.receiveDataFile(self.edf_file, local_edf)
        self.el_tracker.close()

    def save_hdf5(
        self,
        filename,
        all_events=None,
        stimulus_onset=None,
        stimulus_end=None,
        scan_triggers=None,
        metadata=None
    ):
        """
        Save event log and metadata to HDF5.
        Gaze data is not included here (use EDF for full data).
        """
        with h5py.File(filename, "w") as f:
            # Save events
            if all_events is not None:
                dt = h5py.string_dtype(encoding='utf-8')
                events_arr = np.array([
                    (float(e[0]), str(e[1]), str(e[2]) if len(e) > 2 else '')
                    for e in all_events
                ], dtype=[('time', 'f8'), ('event', dt), ('value', dt)])
                f.create_dataset("events", data=events_arr)
            # Save stimulus timing
            stim_grp = f.create_group('stimulus')
            if stimulus_onset is not None:
                stim_grp.attrs['onset'] = stimulus_onset
            if stimulus_end is not None:
                stim_grp.attrs['end'] = stimulus_end
            # Save scanner triggers
            if scan_triggers is not None:
                f.create_dataset("scanner_triggers", data=np.array(scan_triggers))
            # Save metadata
            if metadata:
                for k, v in metadata.items():
                    f.attrs[k] = v
