"""Settings, saved to ~/.nazar/config.json."""
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".nazar"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    camera: int = 0            # webcam index (try 1 if you have two cameras)
    speed: float = 6.0         # wheel notches per second at the very edge
    wheel_step: int = 30       # smallest scroll sent (120 = one wheel click). Use 120 for old apps.
    zone_up: float = 0.30      # gaze above this (fraction of screen height) scrolls up
    zone_down: float = 0.72    # gaze below this scrolls down
    show_rail: bool = True     # the gaze dot on the right edge of the screen
    calibration: dict = field(default_factory=dict)

    @classmethod
    def load(cls):
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        try:
            return cls(**known)
        except TypeError:
            return cls()

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
