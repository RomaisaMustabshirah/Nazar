"""Camera + MediaPipe Face Landmarker on a background thread. Reads your gaze and scrolls."""
import statistics
import threading
import time
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

from . import winapi
from .config import CONFIG_DIR
from .gaze import BlinkDetector, Calibration, GazeFilter, Scroller

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
             "face_landmarker/float16/1/face_landmarker.task")
MODEL_FILE = CONFIG_DIR / "face_landmarker.task"
FACE_LOST_AFTER = 0.6  # seconds without a face before scrolling stops


def ensure_model(status):
    if MODEL_FILE.exists() and MODEL_FILE.stat().st_size > 1_000_000:
        return MODEL_FILE.read_bytes()
    status("Downloading face model (about 4 MB, first run only)…")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = MODEL_FILE.with_suffix(".part")
    urllib.request.urlretrieve(MODEL_URL, tmp)
    tmp.replace(MODEL_FILE)
    return MODEL_FILE.read_bytes()


class Engine:
    def __init__(self, cfg):
        self.cfg = cfg
        self.calib = Calibration.from_dict(cfg.calibration)
        self.filter = GazeFilter()
        self.blinks = BlinkDetector()
        self.scroller = Scroller()

        # read by the UI
        self.gaze = 0.5
        self.face = False
        self.paused = False
        self.status = "Starting…"
        self.error = None
        self.fps = 0.0

        # calibration sampling (driven by the UI)
        self.sampling = None   # list while a calibration dot is showing
        self.collect = False   # True once the eyes have had time to reach the dot
        self.last_raw = None

        self._running = False
        self._thread = None

    # ---- control ----
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="nazar-tracker")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def toggle_pause(self):
        self.paused = not self.paused
        self.scroller.stop()

    # ---- calibration ----
    def begin_point(self):
        self.collect = False
        self.sampling = []

    def end_point(self):
        samples, self.sampling, self.collect = self.sampling or [], None, False
        if samples:
            return statistics.median(samples)
        return self.last_raw if self.last_raw is not None else 0.0

    def set_calibration(self, calib):
        self.calib = calib
        self.filter.reset()
        self.scroller.stop()

    # ---- worker ----
    def _set_status(self, s):
        self.status = s

    def _run(self):
        try:
            model = ensure_model(self._set_status)
            self._set_status("Loading face tracking…")
            options = vision.FaceLandmarkerOptions(
                base_options=mp_tasks.BaseOptions(model_asset_buffer=model),
                running_mode=vision.RunningMode.VIDEO,
                num_faces=1,
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
            )
            landmarker = vision.FaceLandmarker.create_from_options(options)
        except Exception as e:
            self.error = f"Couldn't load face tracking: {e}"
            return

        self._set_status("Opening camera…")
        backend = cv2.CAP_DSHOW if winapi.IS_WINDOWS else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.cfg.camera, backend)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not cap.isOpened():
            self.error = f"Couldn't open camera {self.cfg.camera}. Close other apps using it, or change \"camera\" in {CONFIG_DIR / 'config.json'}."
            landmarker.close()
            return
        self._set_status("")

        t0 = last = time.monotonic()
        last_face = 0.0
        last_ts = -1
        frames, fps_t = 0, t0
        try:
            while self._running:
                ok, frame = cap.read()
                now = time.monotonic()
                dt = min(0.1, now - last)
                last = now
                eyes_closed = self.blinks.closed
                if ok:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    ts = max(last_ts + 1, int((now - t0) * 1000))
                    last_ts = ts
                    res = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
                    if res.face_landmarks:
                        last_face = now
                        lm = res.face_landmarks[0]
                        scores = {c.category_name: c.score for c in (res.face_blendshapes[0] if res.face_blendshapes else [])}
                        blink = (scores.get("eyeBlinkLeft", 0) + scores.get("eyeBlinkRight", 0)) / 2
                        if self.blinks.update(blink, now) and self.calib and self.sampling is None:
                            self.toggle_pause()
                        eyes_closed = self.blinks.closed
                        if not eyes_closed:
                            matrix = res.facial_transformation_matrixes[0] if res.facial_transformation_matrixes else None
                            raw = self._signal(lm, scores, matrix)
                            self.last_raw = raw
                            if self.sampling is not None and self.collect:
                                self.sampling.append(raw)
                            if self.calib:
                                self.gaze = self.filter.update(self.calib.to_screen(raw))
                    frames += 1
                    if now - fps_t >= 1:
                        self.fps, frames, fps_t = frames / (now - fps_t), 0, now
                else:
                    time.sleep(0.01)

                self.face = (now - last_face) < FACE_LOST_AFTER
                active = self.calib is not None and not self.paused and self.sampling is None and self.face
                c = self.cfg
                delta = self.scroller.update(self.gaze, dt, active, eyes_closed, c.zone_up, c.zone_down, c.speed, c.wheel_step)
                if delta:
                    winapi.scroll(delta)
        finally:
            cap.release()
            landmarker.close()

    @staticmethod
    def _signal(lm, scores, matrix):
        from .gaze import gaze_signal
        return gaze_signal(lm, scores, matrix)
