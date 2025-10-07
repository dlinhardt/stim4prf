# eyetracker.py
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import pylink
from psychopy import visual

from stim4prf import logger
from .EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy


# ----------- Eyetracker Base -----------
class EyeTrackerBase(ABC):
    @abstractmethod
    def connect(self, ip: str = "100.1.1.1"): ...

    @abstractmethod
    def calibrate(self, win): ...

    @abstractmethod
    def drift_correction(self): ...

    @abstractmethod
    def start_recording(self): ...

    @abstractmethod
    def stop_recording(self): ...

    @abstractmethod
    def send_message(self, msg: str): ...

    @abstractmethod
    def download_data(self, trial_tsv_name: str): ...

    @abstractmethod
    def close(self): ...


# ----------- EyeLink Tracker Implementation -----------
class EyeLinkTracker(EyeTrackerBase):
    """
    EyeLink tracker integration for PsychoPy.
    Handles connection, configuration, calibration graphics, drift correction,
    recording, standard Data Viewer messages, and EDF download.
    """

    def __init__(self, outdir: str, dummy_mode: bool = False, session_name: Optional[str] = None):
        self.outdir = outdir
        os.makedirs(outdir, exist_ok=True)
        self.dummy_mode = dummy_mode
        self.el_tracker: Optional[pylink.EyeLink] = None
        self.win = None
        self.scn_width, self.scn_height = None, None

        # EDF must be <= 8 characters (no extension). Use compact session tag + time.
        base = (session_name or "S")[:3].upper() + datetime.now().strftime("%H%M%S")
        self.edf_file = (base[:8]).upper() + ".edf"

    # ---- lifecycle ----
    def connect(self, ip: str = "100.1.1.1"):
        try:
            self.el_tracker = pylink.EyeLink(None if self.dummy_mode else ip)
            logger.info("Connected to EyeLink tracker (dummy=%s).", self.dummy_mode)
        except Exception:
            logger.exception("Could not connect to EyeLink tracker.")
            raise

        if not self.el_tracker.isConnected():
            logger.error("EyeLink tracker not connected.")
            raise RuntimeError("EyeLink tracker not connected")

        # Open EDF and set into offline (required before many config commands)
        self.el_tracker.setOfflineMode()
        self.el_tracker.openDataFile(self.edf_file)

        # Set experiment name on Host (appears in header/host UI)
        self.el_tracker.setName("stim4prf")

        # Standard sampling/event filters for EDF and Link
        # (left+right gaze, pupil, area, status; and common events incl. FIXUPDATE for link)
        self.el_tracker.setFileSampleFilter("LEFT,RIGHT,GAZE,AREA,PUPIL,STATUS")
        self.el_tracker.setLinkSampleFilter("LEFT,RIGHT,GAZE,AREA,HTARGET,PUPIL,STATUS")
        self.el_tracker.setFileEventFilter("LEFT,RIGHT,FIXATION,SACCADE,BLINK,MSG,INPUT")
        self.el_tracker.setLinkEventFilter("LEFT,RIGHT,FIXATION,FIXUPDATE,SACCADE,BLINK,MSG,INPUT")

        # Parser / thresholds can be tuned per task; keep defaults unless you need strict saccade parsing.
        # Example (commented): self.el_tracker.setSaccadeVelocityThreshold(35); self.el_tracker.setAccelerationThreshold(950)

        # 13-point calibration (recommended for high-precision tasks)
        self.el_tracker.setCalibrationType("HV13")

    def calibrate(self, win):
        if self.el_tracker is None:
            raise RuntimeError("connect() must be called before calibrate().")
        self.win = win
        self.scn_width, self.scn_height = self.win.size

        # Announce pixel coords to Host + Data Viewer
        self.el_tracker.sendCommand(
            f"screen_pixel_coords = 0 0 {self.scn_width - 1} {self.scn_height - 1}"
        )
        self.el_tracker.sendMessage(
            f"DISPLAY_COORDS 0 0 {self.scn_width - 1} {self.scn_height - 1}"
        )

        # PsychoPy calibration graphics
        genv = EyeLinkCoreGraphicsPsychoPy(self.el_tracker, self.win)
        genv.setTargetType("circle")
        genv.setCalibrationSounds("", "", "")  # silent calibration
        pylink.openGraphicsEx(genv)

        try:
            # Optional on-screen prompt (shown on Display PC)
            msg = visual.TextStim(self.win,
                                  "Press ENTER to begin calibration.\nESC = skip to drift correction.",
                                  color=[1, 1, 1], height=30)
            msg.draw()
            self.win.flip()

            self.el_tracker.doTrackerSetup()

        except RuntimeError as err:
            logger.error("Calibration/setup aborted: %s", err)
            self.el_tracker.exitCalibration()
        finally:
            # Always close the graphics hooks after setup
            pylink.closeGraphics()

    def drift_correction(self):
        if self.el_tracker is None or self.scn_width is None:
            raise RuntimeError("calibrate() must be called before drift_correction().")
        cx, cy = int(self.scn_width / 2), int(self.scn_height / 2)
        try:
            self.el_tracker.doDriftCorrect(cx, cy, 1, 1)
        except RuntimeError as err:
            logger.warning("Drift correction failed/aborted: %s", err)

    # ---- recording ----
    def start_recording(self):
        if self.el_tracker is None:
            raise RuntimeError("connect() must be called before start_recording().")

        self.el_tracker.setOfflineMode()
        # Clear host screen (optional cosmetic)
        self.el_tracker.sendCommand("clear_screen 0")

        # Start recording: samples, events, link
        self.el_tracker.startRecording(1, 1, 1, 1)

        # Wait until the tracker reports recording (avoid capturing pre-roll junk)
        pylink.pumpDelay(100)
        if not self.el_tracker.isRecording():
            logger.error("Tracker did not enter recording mode.")
            raise RuntimeError("EyeLink failed to start recording")

        # Standard Data Viewer messages to segment trials are your responsibility:
        # call send_message('TRIALID <id>') before each trial and 'TRIAL_RESULT <code>' after.
        logger.debug("Recording started.")

    def stop_recording(self):
        if self.el_tracker is None:
            return
        # Small delay to ensure last samples are written
        pylink.pumpDelay(100)
        try:
            self.el_tracker.stopRecording()
            logger.debug("Recording stopped.")
        except RuntimeError as err:
            logger.warning("stopRecording raised: %s", err)

    # ---- messaging & data ----
    def send_message(self, msg: str):
        if self.el_tracker is not None:
            self.el_tracker.sendMessage(msg)

    def download_data(self, trial_tsv_name: str):
        """
        Close EDF and transfer it to outdir; name matches the trial file with .edf suffix.
        """
        if self.el_tracker is None:
            raise RuntimeError("No tracker connection to download from.")

        local_edf = os.path.join(self.outdir, trial_tsv_name.replace(".tsv", ".edf"))

        self.el_tracker.setOfflineMode()
        self.el_tracker.sendCommand("clear_screen 0")
        pylink.msecDelay(500)

        try:
            self.el_tracker.closeDataFile()
        except RuntimeError as err:
            logger.warning("closeDataFile raised: %s", err)

        try:
            # Host->Display transfer; will overwrite if exists (desired in reruns)
            self.el_tracker.receiveDataFile(self.edf_file, local_edf)
            logger.info("EDF downloaded to %s", local_edf)
        except RuntimeError as err:
            logger.error("EDF transfer failed: %s", err)

    def close(self):
        """Close link to tracker (safe to call multiple times)."""
        try:
            if self.el_tracker is not None:
                self.el_tracker.close()
                logger.debug("Closed EyeLink connection.")
        finally:
            self.el_tracker = None


"""
This wrapper allows to use the MRC eyetracking software for the MRC Hi-Speed Camera in Psychopy via the MRC_Eyetracking.dll.
It also adds some additional basic functions: calibrate(), start_recording(), stop_recording() and send_message(), though all but calibrate() are essentially renamings of existing MRC functions (which are also still callable)
To import this wrapper ensure that the MRCEyetracking.dll is stored in the "DLL_1_5_3" folder within the same directory of the experiment (or adjust the dll_path variable accordingly)
Use a code-component at the start of the experiment like this:
    import os
    from mrc_eyetracker import MRCEyeTracking
    eyetracker = MRCEyeTracking(dll_path)
    dll_path = os.path.abspath("DLL_1_5_3/MRC_Eyetracking.dll")

Then all further calls of the functions can be made via e.g. eyetracker.eye_connect() or eyetracker.calibrate(win = win). All functions work with units set to pixel only and need adjustment otherwise as the software measures in pixel.

Tested for Psychopy v. 2024.1.5
Created by Daniel Weinert https://github.com/DEWeinert https://www.researchgate.net/profile/Daniel-Weinert
"""


class EyeEvent(Structure):
    _fields_ = [
        ("eye", c_int),
        ("event_type", c_int),
        ("timestamp", c_double),
        ("event_text", ctypes.c_char * 256),
        ("param1", c_double),
        ("param2", c_double),
        ("param3", c_double),
        ("param4", c_double),
        ("param5", c_double),
    ]


class MRCEyeTracking(EyeTrackerBase):
    def __init__(self, dll_path="MRC_Eyetracking.dll"):
        self.lib = ctypes.WinDLL(dll_path)

        self.lib.eye_connect.argtypes = [c_char_p, c_int]
        self.lib.eye_connect.restype = c_int

        self.lib.eye_disconnect.argtypes = []
        self.lib.eye_disconnect.restype = c_int

        self.lib.eye_get_calibration_point.argtypes = [POINTER(c_double)]
        self.lib.eye_get_calibration_point.restype = None

        self.lib.eye_get_calibstate.argtypes = [POINTER(c_double)]
        self.lib.eye_get_calibstate.restype = None

        self.lib.eye_get_events_count.argtypes = [POINTER(c_int)]
        self.lib.eye_get_events_count.restype = None

        self.lib.eye_get_gaze.argtypes = [POINTER(c_double)]
        self.lib.eye_get_gaze.restype = None

        self.lib.eye_get_last_error.argtypes = []
        self.lib.eye_get_last_error.restype = c_char_p

        self.lib.eye_get_parameter.argtypes = [c_char_p, POINTER(c_double)]
        self.lib.eye_get_parameter.restype = c_int

        self.lib.eye_get_pupil_size.argtypes = [POINTER(c_double)]
        self.lib.eye_get_pupil_size.restype = None

        self.lib.eye_get_status.argtypes = [POINTER(c_int)]
        self.lib.eye_get_status.restype = None

        self.lib.eye_get_timestamp.argtypes = [POINTER(c_double)]
        self.lib.eye_get_timestamp.restype = None

        self.lib.eye_get_version.argtypes = []
        self.lib.eye_get_version.restype = c_char_p

        self.lib.eye_select_camera.argtypes = [c_int]
        self.lib.eye_select_camera.restype = c_int

        self.lib.eye_set_display_offset.argtypes = [c_int, c_int]
        self.lib.eye_set_display_offset.restype = c_int

        self.lib.eye_set_display_parameter.argtypes = [
            c_double,
            c_double,
            ctypes.c_double,
            ctypes.c_double,
        ]
        self.lib.eye_set_display_parameter.restype = c_int

        self.lib.eye_set_displaymode.argtypes = [c_int, c_int]
        self.lib.eye_set_displaymode.restype = c_int

        self.lib.eye_set_parameter.argtypes = [c_char_p, c_char_p]
        self.lib.eye_set_parameter.restype = c_int

        self.lib.eye_set_software_event.argtypes = [c_char_p]
        self.lib.eye_set_software_event.restype = c_int

        self.lib.eye_start_calibrate.argtypes = [c_int]
        self.lib.eye_start_calibrate.restype = c_int

        self.lib.eye_start_stream.argtypes = [c_int]
        self.lib.eye_start_stream.restype = c_int

        self.lib.eye_start_video_recording.argtypes = []
        self.lib.eye_start_video_recording.restype = c_int

        self.lib.eye_stop_calibration.argtypes = []
        self.lib.eye_stop_calibration.restype = c_int

        self.lib.eye_stop_stream.argtypes = []
        self.lib.eye_stop_stream.restype = c_int

        self.lib.eye_stop_video_recording.argtypes = []
        self.lib.eye_stop_video_recording.restype = c_int

        self.lib.eye_get_events_matlab.argtypes = [POINTER(c_int)]
        self.lib.eye_get_events_matlab.restype = POINTER(EyeEvent)

    def eye_connect(self, ip: str, port: int) -> int:
        return self.lib.eye_connect(ip.encode("utf-8"), port)

    def eye_disconnect(self) -> int:
        return self.lib.eye_disconnect()

    def eye_get_calibration_point(self):
        data = (c_double * 3)()
        self.lib.eye_get_calibration_point(data)
        return list(data)

    def eye_get_calibstate(self):
        data = (c_double * 2)()
        self.lib.eye_get_calibstate(data)
        return list(data)

    def eye_get_events(self, count: int):
        c_count = c_int(count)
        events = []
        for _ in range(count):
            ptr = self.lib.eye_get_events_matlab(byref(c_count))
            if ptr:
                evt = ptr.contents
                events.append(
                    {
                        "eye": evt.eye,
                        "event_type": evt.event_type,
                        "timestamp": evt.timestamp,
                        "event_text": evt.event_text.decode("utf-8"),
                        "param1": evt.param1,
                        "param2": evt.param2,
                        "param3": evt.param3,
                        "param4": evt.param4,
                        "param5": evt.param5,
                    }
                )
        return events

    def eye_get_events_count(self) -> int:
        count = c_int(-1)
        self.lib.eye_get_events_count(byref(count))
        return count.value

    def eye_get_gaze(self):
        data = (c_double * 5)()
        self.lib.eye_get_gaze(data)
        return list(data)

    def eye_get_last_error(self) -> str:
        return self.lib.eye_get_last_error().decode("utf-8")

    def eye_get_parameter(self, name: str):
        val = c_double(0.0)
        result = self.lib.eye_get_parameter(name.encode("utf-8"), byref(val))
        return result, val.value

    def eye_get_pupil_size(self):
        data = (c_double * 4)()
        self.lib.eye_get_pupil_size(data)
        return list(data)

    def eye_get_status(self) -> int:
        status = c_int(-1)
        self.lib.eye_get_status(byref(status))
        return status.value

    def eye_get_timestamp(self) -> float:
        ts = c_double(-1)
        self.lib.eye_get_timestamp(byref(ts))
        return ts.value

    def eye_get_version(self) -> str:
        return self.lib.eye_get_version().decode("utf-8")

    def eye_select_camera(self, eye: int) -> int:
        return self.lib.eye_select_camera(eye)

    def eye_set_display_offset(self, width_offset: int, height_offset: int) -> int:
        return self.lib.eye_set_display_offset(width_offset, height_offset)

    def eye_set_display_parameter(
        self, width: float, height: float, distance: float, pixelsize: float
    ) -> int:
        return self.lib.eye_set_display_parameter(width, height, distance, pixelsize)

    def eye_set_displaymode(self, width: int, height: int) -> int:
        return self.lib.eye_set_displaymode(width, height)

    def eye_set_parameter(self, name: str, value: str) -> int:
        return self.lib.eye_set_parameter(name.encode("utf-8"), value.encode("utf-8"))

    def eye_set_software_event(self, value: str) -> int:
        event_bytes = value.encode("ascii") + b"\x00"
        return self.lib.eye_set_software_event(event_bytes)

    def eye_start_calibrate(self, points: int) -> int:
        return self.lib.eye_start_calibrate(points)

    def eye_start_stream(self, parameter: int) -> int:
        return self.lib.eye_start_stream(parameter)

    def eye_start_video_recording(self) -> int:
        return self.lib.eye_start_video_recording()

    def eye_stop_calibration(self) -> int:
        return self.lib.eye_stop_calibration()

    def eye_stop_stream(self) -> int:
        return self.lib.eye_stop_stream()

    def eye_stop_video_recording(self) -> int:
        return self.lib.eye_stop_video_recording()

    def connect(self, ip="localhost"):
        self.eye_connect(ip, 5257)
        version = self.eye_get_version()
        print(f"MRC Eye Tracker Version: {version}")

    def calibrate(
        self,
        win,
        calibration_points=int(9),
        screen_width=float(1920),
        screen_height=float(1080),
        distance_to_screen=float(130),
        pixel_size=float(0.333),
        dot_color=[1, 1, 1],
        dot_size=float(20),
    ):
        # Please set screen_width and height as well as distance to screen and pixel size
        # Calibration is made for a quadratic window equal to the full height of the screen and positioned in the center of the screen. Adjust vertical_goesse and x_displace if nessecary for a not quadratic fixation
        if self.eye_get_status() != -1:
            self.win = win
            screen_width = float(screen_width)
            screen_height = float(screen_height)
            tracking_groesse = float(screen_height)
            vertical_groesse = float(
                tracking_groesse
            )  # if the presentation window region of interest is not quadratic, adjust the x-coordinate here
            x_displace = int(
                ((screen_width - screen_height) / 2) - 8
            )  # the -8 represent the number of pixels of the windows window vertical border.
            y_displace = int(
                -30
            )  # the -30 ensure that the top part of the windows window are not interfering with localisation. Adjust depending on the thickness of your windows top-bars or if using a different operating system
            dot_color = dot_color
            dot_size = float(dot_size)
            display = self.eye_set_display_parameter(
                vertical_groesse, tracking_groesse, distance_to_screen, pixel_size
            )  # width, height, distance, pixel size
            offset = self.eye_set_display_offset(
                x_displace, y_displace
            )  # this variable places the presentation window of the software and defines the area in which recording takes place
            print(display)
            print(offset)
            calibration_running = False
            print(self.eye_get_status())
            if self.eye_get_status() != 2:
                self.eye_start_stream(0)
                self.eye_start_calibrate(calibration_points)
                calibration_running = True

            point = [0, 0, 0]
            while calibration_running == True:
                keys = event.getKeys()
                if "escape" in keys or "q" in keys:
                    print("Calibration aborted")
                    self.eye_stop_calibration()
                    self.eye_stop_stream()
                    break
                if self.eye_get_status() == 2:
                    print("calibration done")
                    self.eye_stop_calibration()
                    calibration_running = False
                    self.eye_stop_stream()
                point = self.eye_get_calibration_point()
                stimulus = visual.Circle(
                    win=win,
                    radius=dot_size / 2,
                    fillColor=dot_color,
                    lineColor=dot_color,
                    pos=(
                        point[1] - tracking_groesse / 2,
                        tracking_groesse / 2 - point[2],
                    ),
                )
                stimulus.draw()
                win.flip()
        else:
            print("error. Eyetracker not connected?")

    def start_recording(self):
        self.eye_set_parameter("eye_save_tracking", "true")

    def stop_recording(self):
        self.eye_set_parameter("eye_save_tracking", "false")

    def send_message(self, msg):
        self.eye_set_software_event(msg)

    def download_data(self):
        pass

    def drift_correction(self):
        pass
