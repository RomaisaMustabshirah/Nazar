from types import SimpleNamespace as P

from nazar.gaze import BlinkDetector, Calibration, GazeFilter, Scroller, gaze_signal


def face(iris_ratio=0.5):
    lm = [P(y=0.5) for _ in range(478)]
    for i, u, l in ((468, 159, 145), (473, 386, 374)):
        lm[u].y, lm[l].y = 0.40, 0.50
        lm[i].y = 0.40 + 0.10 * iris_ratio
    return lm


def scores(down=0.0, up=0.0):
    return {"eyeLookDownLeft": down, "eyeLookDownRight": down, "eyeLookUpLeft": up, "eyeLookUpRight": up}


def test_signal_rises_looking_down():
    assert gaze_signal(face(0.7), scores(down=0.5)) > gaze_signal(face(), scores()) > gaze_signal(face(), scores(up=0.5))


def test_signal_sees_up_even_when_iris_ratio_does_not_change():
    assert gaze_signal(face(0.5), scores(up=0.6)) < gaze_signal(face(0.5), scores())


def test_pitch_from_matrix():
    import math
    flat = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    tilt = [[1, 0, 0, 0], [0, 1, 0, 0], [0, -math.sin(0.2), 1, 0], [0, 0, 0, 1]]
    assert gaze_signal(face(), scores(), tilt) > gaze_signal(face(), scores(), flat)


def test_calibration_maps_points_exactly():
    c = Calibration(-0.5, 0.0, 0.6)
    assert abs(c.to_screen(-0.5) - 0.12) < 1e-9
    assert abs(c.to_screen(0.0) - 0.50) < 1e-9
    assert abs(c.to_screen(0.6) - 0.88) < 1e-9
    assert c.to_screen(0.9) > 0.88 and c.to_screen(-0.8) < 0.12


def test_calibration_validation():
    assert Calibration.is_valid(-0.3, 0, 0.3)
    assert not Calibration.is_valid(0, 0.01, 0.3)
    assert not Calibration.is_valid(0.3, 0, -0.3)
    assert Calibration.from_dict({}) is None
    assert Calibration.from_dict({"top": 0}) is None
    assert Calibration.from_dict({"top": -0.3, "mid": 0, "bottom": 0.3}).mid == 0


def test_filter_ignores_single_spike_and_follows_real_move():
    f = GazeFilter()
    for _ in range(10):
        f.update(0.5)
    f.update(0.95)
    assert abs(f.value - 0.5) < 0.05
    for _ in range(15):
        f.update(0.9)
    assert f.value > 0.85


def test_double_blink():
    b = BlinkDetector()
    assert not b.update(0.9, 0.0)
    assert not b.update(0.0, 0.1)
    assert b.update(0.9, 0.3)
    b2 = BlinkDetector()
    b2.update(0.9, 0.0); b2.update(0.0, 0.1)
    assert not b2.update(0.9, 1.5)   # too slow: two separate blinks


def run(s, gaze, secs, **kw):
    args = dict(active=True, eyes_closed=False, zone_up=0.30, zone_down=0.72, speed=6, step=30)
    args.update(kw)
    total, n = 0, int(secs * 30)
    for _ in range(n):
        total += s.update(gaze, 1 / 30, **args)
    return total


def test_middle_never_scrolls():
    assert run(Scroller(), 0.5, 3) == 0


def test_down_is_negative_wheel_and_eases_in():
    s = Scroller()
    first = run(s, 0.95, 0.2)
    later = run(s, 0.95, 0.2)
    assert first <= 0 and later < first      # negative = down, and it speeds up


def test_up_is_positive_wheel():
    assert run(Scroller(), 0.05, 1) > 0


def test_deeper_is_faster():
    assert run(Scroller(), 0.98, 2) < run(Scroller(), 0.78, 2) < 0


def test_hysteresis_keeps_going_just_inside_edge():
    s = Scroller()
    run(s, 0.9, 1)
    assert run(s, 0.70, 0.5) < 0             # 0.70 is inside the zone edge (0.72) but within hysteresis


def test_inactive_stops_and_step_quantised():
    s = Scroller()
    assert run(s, 0.95, 1, active=False) == 0
    s = Scroller()
    for _ in range(60):
        d = s.update(0.95, 1 / 30, True, False, 0.3, 0.72, 6, 30)
        assert d % 30 == 0


def test_blink_keeps_momentum():
    s = Scroller()
    run(s, 0.95, 1)
    assert run(s, 0.95, 0.15, eyes_closed=True) < 0
