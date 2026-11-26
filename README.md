# Nazar (نظر)

**Read hands-free. Your eyes scroll the page.**

Nazar is a web reader that scrolls using only your webcam and your eyes. Read normally in the middle of the screen; when your gaze reaches the bottom, the text rises to meet you. Look near the top to go back. Double blink to pause.

**Try it:** https://romaisamustabshirah.github.io/Nazar/

## How it works

| Your eyes | What happens |
|---|---|
| Reading the middle of the screen | Nothing moves |
| Looking near the bottom | Scrolls down, faster the lower you look |
| Looking near the top | Scrolls back up |
| Double blink | Pause / resume |

- **Face tracking:** [MediaPipe Face Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker) finds 478 points on the face, including both irises.
- **Gaze height:** where each iris sits between the eyelids, combined with head tilt from the face's transformation matrix.
- **Calibration:** 5 seconds. Look at a top dot, then a bottom dot. The median of each sample set becomes your personal range (saved in the browser).
- **No "Midas touch":** the middle of the screen is a dead zone, so reading never moves the page. Scroll speed grows smoothly toward the edges.
- **Blinks:** MediaPipe's eye-blink blendshape scores. A single blink is ignored; two within 0.7 s toggle pause.
- **Your own text:** paste notes, articles or chapters. Urdu text switches automatically to right-to-left Nastaliq.

## Privacy

Everything runs in your browser. Video never leaves your device and nothing is recorded.

## Run locally

The camera needs `https` or `localhost`:

```
cd docs
python -m http.server 8000
```

Then open http://localhost:8000.

## Tips

- Sit facing the camera with light in front of you, not a bright window behind.
- Recalibrate if you change chairs or posture.

## Roadmap

- Desktop version that scrolls **any** window (PDFs, browsers, documents), like [Ishara](https://github.com/RomaisaMustabshirah/Ishara).
- Adjustable speed and zones in the page.

## License

MIT © Romaisa Mustabshirah
