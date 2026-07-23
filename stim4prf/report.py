"""Write a self-contained HDF5 report for a single run.

The report sits next to the TSV timing log (``..._report.h5``) and captures how
the run was configured (all parameters given to every sub-module, which stimulus
and fixation target were used) together with the behavioral outcome (button
presses, number correct, mean reaction time) and the raw event arrays.
"""

import json
import socket
from datetime import datetime

import h5py
import numpy as np

from stim4prf import logger

REPORT_SCHEMA_VERSION = 1


def _stim4prf_version():
    """Best-effort package version, ``"unknown"`` if it cannot be determined."""
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version("stim4prf")
        except PackageNotFoundError:
            return "unknown"
    except Exception:
        return "unknown"


def _attr_safe(value):
    """Coerce ``value`` into something h5py can store as an attribute.

    Native scalars, strings and (nested) sequences of them are returned as-is;
    anything else (class objects, ``None``, dicts, ...) is JSON-encoded so the
    report never fails on an unexpected kwarg.
    """
    if value is None:
        return "None"
    if isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (list, tuple)):
        # h5py can store homogeneous lists of str/number; fall back to JSON
        # for anything mixed or nested.
        if all(isinstance(v, (str, bool, int, float, np.generic)) for v in value):
            return [
                v.item() if isinstance(v, np.generic) else v for v in value
            ]
        return json.dumps(list(value), default=str)
    return json.dumps(value, default=str)


def _set_attrs(group, mapping):
    """Store every key/value of ``mapping`` as an attribute on ``group``."""
    for key, value in mapping.items():
        try:
            group.attrs[key] = _attr_safe(value)
        except Exception:
            group.attrs[key] = json.dumps(value, default=str)


def write_run_report(
    report_path,
    *,
    presenter,
    run_args,
    button_events,
    switch_log,
    scan_trigger_times,
    n_frames_presented,
    run_duration,
    behavior,
    aborted,
):
    """Write the HDF5 run report.

    Parameters
    ----------
    report_path : str
        Destination ``..._report.h5`` path.
    presenter : PRFStimulusPresenter
        The presenter instance (source of all sub-module parameters).
    run_args : dict
        Arguments passed to ``run()`` (subject, session, run, outdir,
        button_keys, ip).
    button_events : list of (time, key)
    switch_log : list of (time, color)
    scan_trigger_times : list of float
    n_frames_presented : int
    run_duration : float
        Time of the last frame onset.
    behavior : dict
        ``n_hits``, ``n_switches``, ``hit_ratio``, ``mean_rt``, ``reaction_times``.
    aborted : bool
    """
    loader = presenter.loader
    eyetracker_class = presenter.eyetracker_class

    with h5py.File(report_path, "w") as f:
        # --- Top-level metadata ---
        _set_attrs(
            f,
            {
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "subject": run_args.get("subject"),
                "session": run_args.get("session"),
                "run": run_args.get("run"),
                "hostname": socket.gethostname(),
                "stim4prf_version": _stim4prf_version(),
                "report_schema_version": REPORT_SCHEMA_VERSION,
            },
        )

        # --- Parameters given to every sub-module ---
        params = f.create_group("params")

        _set_attrs(
            params.create_group("presenter"),
            {
                "screen": presenter.screen,
                "trigger_key": presenter.trigger_key,
                "abort_key": presenter.abort_key,
                "frame_log_interval": presenter.frame_log_interval,
                "end_screen_wait": presenter.end_screen_wait,
                "flipVert": presenter.flipVert,
                "flipHoriz": presenter.flipHoriz,
                "verbose": presenter.verbose,
            },
        )

        fix_grp = params.create_group("fixation")
        fix_grp.attrs["class"] = presenter.fixation_class.__name__
        _set_attrs(fix_grp, presenter.fixation_kwargs)

        eye_grp = params.create_group("eyetracker")
        eye_grp.attrs["class"] = (
            eyetracker_class.__name__ if eyetracker_class is not None else "None"
        )
        _set_attrs(eye_grp, presenter.eyetracker_kwargs)

        stim_grp = params.create_group("stimulus")
        _set_attrs(
            stim_grp,
            {
                "loader_class": type(loader).__name__,
                "source_path": getattr(loader, "h5_path", None)
                or getattr(loader, "mat_path", None),
                "frame_duration": presenter.frame_duration,
                "nFrames": presenter.nFrames,
            },
        )
        _set_attrs(stim_grp, getattr(loader, "params", {}))

        _set_attrs(params.create_group("run"), run_args)

        # --- Event arrays ---
        events = f.create_group("events")
        str_dt = h5py.string_dtype(encoding="utf-8")

        bp = events.create_group("button_presses")
        bp.create_dataset(
            "time", data=np.array([t for t, _ in button_events], dtype="float64")
        )
        bp.create_dataset(
            "key", data=np.array([k for _, k in button_events], dtype=object), dtype=str_dt
        )

        fs = events.create_group("fixation_switches")
        fs.create_dataset(
            "time", data=np.array([t for t, _ in switch_log], dtype="float64")
        )
        fs.create_dataset(
            "color",
            data=np.array([c for _, c in switch_log], dtype=object),
            dtype=str_dt,
        )

        st = events.create_group("scanner_triggers")
        st.create_dataset(
            "time", data=np.array(scan_trigger_times, dtype="float64")
        )

        # --- Behavioral summary ---
        beh = f.create_group("behavior")
        _set_attrs(
            beh,
            {
                "n_hits": behavior.get("n_hits"),
                "n_switches": behavior.get("n_switches"),
                "hit_ratio": behavior.get("hit_ratio"),
                "mean_rt": behavior.get("mean_rt"),
            },
        )
        beh.create_dataset(
            "reaction_times",
            data=np.array(behavior.get("reaction_times", []), dtype="float64"),
        )

        # --- Timing summary (no per-frame onset array) ---
        _set_attrs(
            f.create_group("timing"),
            {
                "n_frames_presented": n_frames_presented,
                "run_duration": run_duration,
                "expected_nFrames": presenter.nFrames,
                "aborted": aborted,
            },
        )

    logger.info(f"Saved run report: {report_path}")
