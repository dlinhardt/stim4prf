from stim4prf.eyetracking import MRCEyeTracking

eyetracker = MRCEyeTracking(
                os.path.abspath("DLL_1_5_3/MRC_Eyetracking.dll")
            )

eyetracker.connect()
eyetracker.calibrate()
#self.eyetracker.drift_correction()
eyetracker.start_recording()
eyetracker.send_message(f"EXPERIMENT_START {subject} {session} {run}")
