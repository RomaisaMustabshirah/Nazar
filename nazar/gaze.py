"""Pure gaze logic: no camera, no Windows. Everything here is unit-tested."""
import math

# Where the three calibration dots sit, as a fraction of screen height.
CALIB_POINTS = (("top", 0.12), ("mid", 0.50), ("bottom", 0.88))


def gaze_signal(lm, scores, matrix=None):
    """One number that grows as you look further down the screen.

    lm      face landmarks (objects with .y), MediaPipe Face Mesh indices
    scores  dict of blendshape name -> score
    matrix  4x4 facial transformation matrix (or None)
    """
    s = scores.get
    # 1) MediaPipe's own eye-direction scores. These still work when you look UP,
    #    where the upper eyelid lifts with the eye and hides the movement.
    look = ((s("eyeLookDownLeft", 0) - s("eyeLookUpLeft", 0)) +
            (s("eyeLookDownRight", 0) - s("eyeLookUpRight", 0))) / 2

    # 2) Iris position between the eyelids (left: iris 468, lids 159/145; right: 473, 386/374).
    def ratio(iris, up, lo):
        return (lm[iris].y - lm[up].y) / max(1e-4, lm[lo].y - lm[up].y)
    lid = (ratio(468, 159, 145) + ratio(473, 386, 374)) / 2 - 0.5

    # 3) Head pitch: people nod a little as they read down a page.
    pitch = 0.0
    if matrix is not None:
        pitch = math.asin(max(-1.0, min(1.0, -float(matrix[2][1]))))

    return look + lid * 0.5 + pitch * 1.2


class Calibration:
    """Maps the raw signal to a screen position (0 = top, 1 = bottom) through three points."""

    def __init__(self, top, mid, bottom):
        self.top, self.mid, self.bottom = top, mid, bottom

    @staticmethod
    def is_valid(top, mid, bottom):
        return (mid - top) > 0.02 and (bottom - mid) > 0.02

    @classmethod
    def from_dict(cls, d):
        if not d:
            return None
        try:
            c = cls(float(d["top"]), float(d["mid"]), float(d["bottom"]))
        except (KeyError, TypeError, ValueError):
            return None
        return c if cls.is_valid(c.top, c.mid, c.bottom) else None

    def to_dict(self):
        return {"top": self.top, "mid": self.mid, "bottom": self.bottom}

    def to_screen(self, raw):
        (_, ya), (_, yb), (_, yc) = CALIB_POINTS
        if raw < self.mid:   # upper half, and beyond
            return yb + (raw - self.mid) / (self.top - self.mid) * (ya - yb)
        return yb + (raw - self.mid) / (self.bottom - self.mid) * (yc - yb)


class GazeFilter:
    """Median of the last few frames, then adaptive smoothing:
    small wobbles are smoothed heavily, a real eye movement comes through quickly."""

    def __init__(self, window=5):
        self.window = window
        self.recent = []
        self.value = 0.5

    def reset(self, value=0.5):
        self.recent = []
        self.value = value

    def update(self, x):
        self.recent.append(x)
        if len(self.recent) > self.window:
            self.recent.pop(0)
        target = sorted(self.recent)[len(self.recent) // 2]
        a = min(0.6, 0.08 + abs(target - self.value) * 1.5)
        self.value += (target - self.value) * a
        return self.value


class BlinkDetector:
    """Two blinks within `window` seconds -> True (toggle pause)."""

    def __init__(self, threshold=0.5, window=0.7):
        self.threshold, self.window = threshold, window
        self.closed = False
        self.times = []

    def update(self, blink_score, t):
        closed = blink_score > self.threshold
        fired = False
        if closed and not self.closed:
            self.times = [b for b in self.times if t - b < self.window] + [t]
            if len(self.times) >= 2:
                self.times = []
                fired = True
        self.closed = closed
        return fired


WHEEL_NOTCH = 120  # Windows: one mouse-wheel click


class Scroller:
    """Turns gaze into mouse-wheel movement.

    - nothing in the middle of the screen
    - gentle start inside a zone, faster the deeper you look
    - hysteresis so the edge of a zone doesn't stutter
    - speed eases in and out; leftover fractions carry over
    Returns a wheel delta for this frame (Windows sign: positive = scroll up).
    """

    def __init__(self, hysteresis=0.04):
        self.hyst = hysteresis
        self.vel = 0.0    # wheel units per second, + = down
        self.carry = 0.0
        self.dir = 0

    def stop(self):
        self.vel = self.carry = 0.0
        self.dir = 0

    def update(self, gaze, dt, active, eyes_closed, zone_up, zone_down, speed, step):
        """speed: wheel notches per second at the very edge. step: smallest wheel delta to send."""
        want = 0.0
        if active and eyes_closed:
            want = self.vel                      # a blink doesn't jolt the page to a stop
        elif active:
            down_edge = zone_down - self.hyst if self.dir == 1 else zone_down
            up_edge = zone_up + self.hyst if self.dir == -1 else zone_up
            w = 0.0
            if gaze > down_edge:
                self.dir = 1
                w = min(1.0, (gaze - down_edge) / max(1e-3, 1 - down_edge))
            elif gaze < up_edge:
                self.dir = -1
                w = -min(1.0, (up_edge - gaze) / max(1e-3, up_edge))
            else:
                self.dir = 0
            if w:
                want = math.copysign(0.15 + 0.85 * w * w, w) * speed * WHEEL_NOTCH
        else:
            self.dir = 0

        self.vel += (want - self.vel) * min(1.0, dt * 5)
        if abs(self.vel) < 5 and not want:
            self.vel = 0.0
        self.carry += self.vel * dt
        n = int(self.carry / step)
        if n:
            self.carry -= n * step
            return -n * step
        return 0
