import os
from psychopy import  gui,data,core,hardware
from stim4prf import HDF5StimulusLoader, MatlabStimulusLoader, PRFStimulusPresenter
from stim4prf.eyetracking import MRCEyeTracking
from stim4prf.fixation import ABCTargetFixation, FixationCross, FixationDot

# --- Choose your loader ---
deviceManager = hardware.DeviceManager()
# ensure that relative paths start from the same directory as this script
_thisDir = os.path.dirname(os.path.abspath(__file__))
# store info about the experiment session
psychopyVersion = '2024.1.5'
expName = 'Full_retina_run'
expInfo = {
    'sessionID': 'Retina_MRI_',
    'skipinstruction': 'on',
    'targetRing': '13',
    'language': 'German',
    'eye_external': 'on',
    'AttemptNumber': '1',
    'VisAtt': 'on',
    'pRF': 'on',
    'date|hid': data.getDateStr(),
    'expName|hid': expName,
    'psychopyVersion|hid': psychopyVersion,
}



def showExpInfoDlg(expInfo):
    """
    Show participant info dialog.
    Parameters
    ==========
    expInfo : dict
        Information about this experiment.
    
    Returns
    ==========
    dict
        Information about this experiment.
    """
    # show participant info dialog
    dlg = gui.DlgFromDict(
        dictionary=expInfo, sortKeys=False, title=expName, alwaysOnTop=True
    )
    if dlg.OK == False:
        core.quit()  # user pressed cancel
    print("this expInfoDlg was called")
    # return expInfo
    return expInfo

# For HDF5 files:
loader = HDF5StimulusLoader(
    os.path.join(
        ".",
        "stimuli",
        "bar_smooth_size-1080_dur-300_ecc-10.6_width-2_tr1_images.h5",
    ),
    verbose=True,
)

# --- Choose fixation class and options ---
fixation_class = FixationDot  # or FixationCross, ABCTargetFixation
fixation_kwargs = {
    "size": 20,  # pix
    "color_switch_prob": 0.01,  # Probability of color switch per frame
    "min_switch_interval": 2.0,  # s no color switch after switch
    "colors": ("magenta", "green"),  # Colors to switch between
    "verbose": True,  # Print extra info
}

# --- Eyetracker options ---
eyetracker_class = MRCEyeTracking  # or EyeLinkTracker if connected
eyetracker_kwargs = {
    "dummy_mode": False,  # Set True for testing without hardware
}

# --- Create the stimulus presenter with all options ---
presenter = PRFStimulusPresenter(
    loader=loader,  # pass the loader instance
    fixation_class=fixation_class,  # pass the fixation class
    fixation_kwargs=fixation_kwargs,
    eyetracker_class=eyetracker_class,  # pass the eyetracker class
    eyetracker_kwargs=eyetracker_kwargs,
    screen=1,  # Which screen to use (0=primary)
    trigger_key="s",  # Key the scanner sends as trigger
    abort_key="escape",  # Key to abort run
    frame_log_interval=100,  # Log every N frames
    end_screen_wait=2.0,  # Seconds to show end screen
    flipVert=False,  # Flip images vertically
    flipHoriz=True,  # Flip images horizontally
    verbose=True,  # Print extra info
)

if __name__ == '__main__':
    expInfo = showExpInfoDlg(expInfo=expInfo)
    if expInfo['pRF'] == 'on':
        subject = expInfo["sessionID"]
        session = expInfo["AttemptNumber"]
        runs = ["01", "02"]
        if expInfo['eye_external'] == 'on':
                    ip = "169.254.197.24"
        else:
                    ip = "169.254.60.154"
        # List of runs to execute

        for run in runs:
            presenter.run(ip = ip,
                subject=subject,
                session=session,
                run=run,
                outdir=os.path.join(".", "data"),
                button_keys=["1", "2", "3", "4"],  # List of buttons to accept during the run
            )