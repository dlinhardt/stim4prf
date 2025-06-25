import random
from abc import ABC, abstractmethod

import numpy as np
from psychopy import event, visual

from stim4prf import logger


# ----------- Fixation Base and Variants -----------
class Fixation(ABC):
    """Abstract base class for fixation markers."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    @abstractmethod
    def draw(self) -> None:
        pass

    @abstractmethod
    def update(self, now: float = None) -> None:
        pass


class FixationDot(Fixation):
    """A colored dot fixation marker that occasionally changes color."""

    def __init__(
        self,
        win,
        size: int = 8,
        colors: tuple = ("magenta", "green"),
        color_switch_prob: float = 0.01,
        min_switch_interval: float = 2.0,
        verbose: bool = False,
    ):
        super().__init__(verbose)
        self.win = win
        self.radius = size / 2
        self.colors = colors
        self.color_switch_prob = color_switch_prob
        self.current_color = colors[0]
        self.last_switch_time = None
        self.switch_log = []
        self.min_switch_interval = min_switch_interval
        self.circle = visual.Circle(
            win,
            radius=self.radius,
            fillColor=self.current_color,
            lineColor=self.current_color,
            pos=(0, 0),
            units="pix",
        )

    def update(self, now: float = None) -> None:
        if now is None:
            return
        if (
            self.last_switch_time is None
            or (now - self.last_switch_time) >= self.min_switch_interval
        ):
            if random.random() < self.color_switch_prob:
                self.current_color = (
                    self.colors[1]
                    if self.current_color == self.colors[0]
                    else self.colors[0]
                )
                self.circle.fillColor = self.current_color
                self.circle.lineColor = self.current_color
                self.last_switch_time = now
                self.switch_log.append((now, self.current_color))
                if self.verbose:
                    logger.info(f"Fixation color switched to {self.current_color}")

    def draw(self) -> None:
        self.circle.draw()


class FixationCross(Fixation):
    """A colored cross fixation marker that occasionally changes color."""

    def __init__(
        self,
        win,
        size: int = 30,
        colors: tuple = ("magenta", "green"),
        color_switch_prob: float = 0.01,
        min_switch_interval: float = 2.0,
        verbose: bool = False,
    ):
        super().__init__(verbose)
        self.win = win
        self.size = size
        self.colors = colors
        self.color_switch_prob = color_switch_prob
        self.current_color = colors[0]
        self.last_switch_time = None
        self.switch_log = []
        self.min_switch_interval = min_switch_interval
        self.text = visual.TextStim(
            win, text="+", color=self.current_color, height=self.size, pos=(0, 0)
        )

    def update(self, now: float = None) -> None:
        if now is None:
            return
        if (
            self.last_switch_time is None
            or (now - self.last_switch_time) >= self.min_switch_interval
        ):
            if random.random() < self.color_switch_prob:
                self.current_color = (
                    self.colors[1]
                    if self.current_color == self.colors[0]
                    else self.colors[0]
                )
                self.text.color = self.current_color
                self.last_switch_time = now
                self.switch_log.append((now, self.current_color))
                if self.verbose:
                    logger.info(f"Fixation color switched to {self.current_color}")

    def draw(self) -> None:
        self.text.draw()


class ABCTargetFixation:
    """
    ABC Target Fixation as described in:
    L. Thaler et al. (2013). What is the best fixation target? The effect of target shape on stability of fixational eye movements.
    Vision Research, 76, 31-42. https://doi.org/10.1016/j.visres.2012.10.012

    Draws a fixation target with two concentric circles and a central cross, following the design in the referenced paper.
    """

    def __init__(
        self,
        win,
        width_cm=39,
        dist_cm=60,
        d1_deg=0.6,
        d2_deg=0.1,
        color_oval=[-1, -1, -1],
        color_cross=[1, 1, 1],
        color_dot=[1, 0, 0],
        verbose=False,
    ):
        self.win = win
        self.width_cm = width_cm
        self.dist_cm = dist_cm
        self.d1_deg = d1_deg
        self.d2_deg = d2_deg
        self.color_oval = color_oval
        self.color_cross = color_cross
        self.color_dot = color_dot
        self.verbose = verbose

        # Calculate pixels per degree
        win_width_pix = win.size[0]
        self.ppd = np.pi * win_width_pix / np.arctan(width_cm / dist_cm / 2) / 360

        self._create_shapes()

    def _create_shapes(self):
        # Outer circle
        self.outer_circle = visual.Circle(
            self.win,
            radius=(self.d1_deg / 2) * self.ppd,
            edges=128,
            lineColor=None,
            fillColor=self.color_oval,
            pos=(0, 0),
        )
        # Inner circle
        self.inner_circle = visual.Circle(
            self.win,
            radius=(self.d2_deg / 2) * self.ppd,
            edges=128,
            lineColor=None,
            fillColor=self.color_oval,
            pos=(0, 0),
        )
        # Horizontal line
        self.hor_line = visual.Line(
            self.win,
            start=(-self.d1_deg / 2 * self.ppd, 0),
            end=(self.d1_deg / 2 * self.ppd, 0),
            lineColor=self.color_cross,
            lineWidth=self.d2_deg * self.ppd,
        )
        # Vertical line
        self.ver_line = visual.Line(
            self.win,
            start=(0, -self.d1_deg / 2 * self.ppd),
            end=(0, self.d1_deg / 2 * self.ppd),
            lineColor=self.color_cross,
            lineWidth=self.d2_deg * self.ppd,
        )

    def update(self, color=None, now=None):
        """
        Update the color of the central dot.
        Parameters:
            color: new color for the central dot (e.g., [1, 0, 0] for red)
            now: (optional) current time or frame, ignored here
        """
        if color is not None:
            self.color_dot = color

    def draw(self):
        self.outer_circle.draw()
        self.hor_line.draw()
        self.ver_line.draw()
        self.inner_circle.draw()
