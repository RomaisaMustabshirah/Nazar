# Nazar (نظر)

**Scroll with your eyes.** No hands, no special hardware, just your webcam.

Read normally in the middle of the screen. When your eyes reach the bottom, the page rises to meet you. Look near the top to go back. Double blink to pause.

Nazar comes in two forms:

| | What it scrolls | Try it |
|---|---|---|
| **Desktop app** (Windows) | **Any** window: PDFs, browsers, Word, notes | `python -m nazar` |
| **Web reader** | Text you paste into the page | https://romaisamustabshirah.github.io/Nazar/ |

## Your eyes are the controls

| Your eyes | What happens |
|---|---|
| Reading the middle of the screen | Nothing moves |
| Looking near the bottom | Scrolls down, faster the lower you look |
| Looking near the top | Scrolls back up |
| Double blink | Pause / resume |

Desktop hotkeys: **Ctrl+Alt+N** pause / resume, **Ctrl+Alt+C** calibrate again.

## Desktop app

### Install

Use Python 3.10 – 3.12 (MediaPipe may not support the newest Python yet).

```
cd D:\Nazar
python -m pip install -r requirements.txt
```

### Run

```
python -m nazar
```

1. The first run downloads the face model (about 4 MB) to `~/.nazar/`.
2. Calibration: look at the top, middle and bottom dots, moving only your eyes. Press **Esc** to cancel.
3. Open anything you want to read and keep your **mouse pointer over it**. Nazar scrolls the window under the pointer.

A slim gaze rail on the right edge of the screen shows where Nazar thinks you are looking. Mouse clicks pass straight through it.

### Settings

The control panel has a **Speed** slider and a toggle for the gaze rail. More settings live in `~/.nazar/config.json`:

| Setting | Default | Meaning |
|---|---|---|
| `camera` | `0` | Webcam index. Try `1` if you have two cameras. |
| `speed` | `6.0` | Mouse-wheel clicks per second at the very edge |
| `wheel_step` | `30` | Smallest scroll sent (120 = one wheel click). Set to `120` if an app ignores small scrolls. |
| `zone_up` | `0.30` | Looking above this fraction of the screen scrolls up |
| `zone_down` | `0.72` | Looking below this fraction scrolls down |

### Tests

```
python -m pytest tests
```

## How it works

- **Face tracking:** [MediaPipe Face Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker) finds 478 points on the face, including both irises, plus blendshape scores.
- **Gaze height:** MediaPipe's eye-direction scores (look up / look down), plus where each iris sits between the eyelids and head tilt from the face's transformation matrix. The eye-direction scores matter for looking up, where the upper eyelid lifts with the eye and hides the movement.
- **Calibration:** look at a top, middle and bottom dot. The median of each set of samples is stored, and the signal is mapped piece by piece so looking up and looking down are each scaled to fit.
- **No "Midas touch":** the middle of the screen is a dead zone, so reading never moves the page.
- **Smooth scrolling:** jitter is filtered (median + adaptive smoothing), the zones have hysteresis so their edges don't stutter, and speed eases in and out instead of jumping.
- **Blinks:** blink blendshape scores. One blink is ignored; two within 0.7 s toggle pause. Scrolling keeps its momentum through a blink.
- **Desktop scrolling:** Windows `SendInput` mouse-wheel events in small steps, so it works in any app that responds to a mouse wheel.

```
nazar/
  gaze.py      gaze signal, calibration, filtering, blink and scroll logic (pure, unit-tested)
  tracker.py   camera + MediaPipe on a background thread
  winapi.py    mouse wheel, global hotkeys, click-through window
  ui.py        control panel, gaze rail, calibration screen
  config.py    settings in ~/.nazar/config.json
docs/
  index.html   the web reader (GitHub Pages)
```

## Tips

- Sit facing the camera with light in front of you, not a bright window behind.
- Raise the laptop or tilt the screen so the camera looks straight at your eyes, not up at your chin.
- Recalibrate (Ctrl+Alt+C) if you change chairs or posture.

## Privacy

Everything runs on your device. Video is never saved or sent anywhere.

## License

MIT © Romaisa Mustabshirah
