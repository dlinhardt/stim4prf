import random
from abc import ABC, abstractmethod
from stim4prf import logger
from psychopy import visual

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
        radius: int = 8,
        colors: tuple = ('magenta', 'green'),
        color_switch_prob: float = 0.01,
        min_switch_interval: float = 2.0,
        verbose: bool = False
    ):
        super().__init__(verbose)
        self.win = win
        self.radius = radius
        self.colors = colors
        self.color_switch_prob = color_switch_prob
        self.current_color = colors[0]
        self.last_switch_time = None
        self.switch_log = []
        self.min_switch_interval = min_switch_interval
        self.circle = visual.Circle(win, radius=self.radius, fillColor=self.current_color,
                                   lineColor=self.current_color, pos=(0,0), units='pix')

    def update(self, now: float = None) -> None:
        if now is None:
            return
        if self.last_switch_time is None or (now - self.last_switch_time) >= self.min_switch_interval:
            if random.random() < self.color_switch_prob:
                self.current_color = self.colors[1] if self.current_color == self.colors[0] else self.colors[0]
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
        colors: tuple = ('magenta', 'green'),
        color_switch_prob: float = 0.01,
        min_switch_interval: float = 2.0,
        verbose: bool = False
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
        self.text = visual.TextStim(win, text='+', color=self.current_color,
                                   height=self.size, pos=(0,0))

    def update(self, now: float = None) -> None:
        if now is None:
            return
        if self.last_switch_time is None or (now - self.last_switch_time) >= self.min_switch_interval:
            if random.random() < self.color_switch_prob:
                self.current_color = self.colors[1] if self.current_color == self.colors[0] else self.colors[0]
                self.text.color = self.current_color
                self.last_switch_time = now
                self.switch_log.append((now, self.current_color))
                if self.verbose:
                    logger.info(f"Fixation color switched to {self.current_color}")

    def draw(self) -> None:
        self.text.draw()