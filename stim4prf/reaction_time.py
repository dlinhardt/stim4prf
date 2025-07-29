import numpy as np


# ----------- Reaction Time Analysis Helper -----------
def analyze_reaction_times(
    switch_log, button_events, min_rt: float = 0.3, max_rt: float = 3.0
):
    """
    Analyze reaction times between color switches and button presses.
    Returns (n_hits, n_switches, mean_rt, reaction_times).
    """
    n_switches = len(switch_log)
    n_hits = 0
    reaction_times = []
    button_events_sorted = sorted(button_events, key=lambda x: x[0])
    for switch_time, _ in switch_log:
        for btn_time, _ in button_events_sorted:
            dt = btn_time - switch_time
            if min_rt <= dt <= max_rt:
                n_hits += 1
                reaction_times.append(dt)
                break
    mean_rt = np.mean(reaction_times) if reaction_times else float("nan")
    return n_hits, n_switches, mean_rt, reaction_times
