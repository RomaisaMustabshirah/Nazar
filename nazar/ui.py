"""Tkinter windows: the control panel, the gaze rail on the screen edge, and calibration."""
import queue
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from . import winapi
from .gaze import CALIB_POINTS, Calibration

PAPER, INK, SOFT, TEAL, LINE = "#faf7f1", "#1d1b18", "#6f685e", "#0f7c80", "#d9d2c5"
KEY = "#010203"   # transparent colour for the rail window
RAIL_W = 22
FROZEN = getattr(sys, "frozen", False)   # running as Nazar.exe


def resource(name):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / name


class App:
    def __init__(self, cfg, engine):
        self.cfg, self.engine = cfg, engine
        self.events = queue.Queue()        # hotkey threads -> UI thread
        self.calibrating = False
        self.auto_calibrated = False

        self.root = tk.Tk()
        self.root.title("Nazar")
        self.root.configure(bg=PAPER)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.attributes("-topmost", True)
        try:
            if winapi.IS_WINDOWS:
                self.root.iconbitmap(str(resource("nazar.ico")))
            else:
                self.root.iconphoto(True, tk.PhotoImage(file=str(resource("nazar.png"))))
        except Exception:
            pass
        self._build_panel()
        self._build_rail()

        failed = winapi.register_hotkeys([
            (winapi.MOD_CONTROL | winapi.MOD_ALT, "N", lambda: self.events.put("pause")),
            (winapi.MOD_CONTROL | winapi.MOD_ALT, "C", lambda: self.events.put("calibrate")),
        ])
        if failed:
            self.hint.config(text=self.hint.cget("text") + f"\n(Hotkey Ctrl+Alt+{'/'.join(failed)} is used by another app.)")

    # ---------- control panel ----------
    def _build_panel(self):
        r = self.root
        pad = {"padx": 18}
        head = tk.Frame(r, bg=PAPER)
        head.pack(fill="x", pady=(16, 4), **pad)
        tk.Label(head, text="Nazar", font=("Georgia", 20, "bold"), fg=INK, bg=PAPER).pack(side="left")
        tk.Label(head, text="scroll with your eyes", font=("Segoe UI", 10), fg=TEAL, bg=PAPER).pack(side="left", padx=10, pady=(8, 0))

        self.status = tk.Label(r, text="Starting…", font=("Segoe UI", 11), fg=SOFT, bg=PAPER, anchor="w", justify="left", wraplength=300)
        self.status.pack(fill="x", **pad)

        btns = tk.Frame(r, bg=PAPER)
        btns.pack(fill="x", pady=12, **pad)
        style = {"font": ("Segoe UI", 10, "bold"), "relief": "flat", "bd": 0, "padx": 14, "pady": 8, "cursor": "hand2"}
        self.cal_btn = tk.Button(btns, text="Calibrate", bg=TEAL, fg="white", activebackground="#0b6367", activeforeground="white",
                                 command=self.start_calibration, **style)
        self.cal_btn.pack(side="left")
        self.pause_btn = tk.Button(btns, text="Pause", bg="#ece6db", fg=INK, activebackground=LINE, command=self.toggle_pause, **style)
        self.pause_btn.pack(side="left", padx=8)

        row = tk.Frame(r, bg=PAPER)
        row.pack(fill="x", **pad)
        tk.Label(row, text="Speed", font=("Segoe UI", 10), fg=SOFT, bg=PAPER).pack(side="left")
        self.speed = tk.DoubleVar(value=self.cfg.speed)
        ttk.Scale(row, from_=2, to=15, variable=self.speed, command=self._speed_changed, length=200).pack(side="left", padx=10)

        self.rail_var = tk.BooleanVar(value=self.cfg.show_rail)
        tk.Checkbutton(r, text="Show gaze dot on screen edge", variable=self.rail_var, command=self._rail_toggled,
                       font=("Segoe UI", 10), fg=INK, bg=PAPER, activebackground=PAPER, selectcolor=PAPER,
                       anchor="w").pack(fill="x", pady=(6, 0), **pad)
        if FROZEN and winapi.IS_WINDOWS:
            self.auto_var = tk.BooleanVar(value=winapi.get_autostart())
            tk.Checkbutton(r, text="Start Nazar when Windows starts", variable=self.auto_var,
                           command=lambda: winapi.set_autostart(self.auto_var.get()),
                           font=("Segoe UI", 10), fg=INK, bg=PAPER, activebackground=PAPER, selectcolor=PAPER,
                           anchor="w").pack(fill="x", **pad)

        self.hint = tk.Label(r, font=("Segoe UI", 9), fg=SOFT, bg=PAPER, justify="left", anchor="w", wraplength=300, text=(
            "Scrolls whatever window is under your mouse pointer.\n"
            "Double blink or Ctrl+Alt+N: pause / resume\n"
            "Ctrl+Alt+C: calibrate again"))
        self.hint.pack(fill="x", pady=(10, 16), **pad)

    def _speed_changed(self, _=None):
        self.cfg.speed = round(self.speed.get(), 1)

    def _rail_toggled(self):
        self.cfg.show_rail = self.rail_var.get()
        self.cfg.save()

    def toggle_pause(self):
        if self.engine.calib:
            self.engine.toggle_pause()

    # ---------- gaze rail ----------
    def _build_rail(self):
        self.rail = tk.Toplevel(self.root)
        self.rail.overrideredirect(True)
        self.rail.attributes("-topmost", True)
        self.rail.configure(bg=KEY)
        if winapi.IS_WINDOWS:
            self.rail.attributes("-transparentcolor", KEY)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.rail_h = sh
        self.rail.geometry(f"{RAIL_W}x{sh}+{sw - RAIL_W}+0")
        c = self.rail_canvas = tk.Canvas(self.rail, width=RAIL_W, height=sh, bg=KEY, highlightthickness=0)
        c.pack()
        x = RAIL_W // 2
        c.create_line(x, 8, x, sh - 8, fill=LINE, width=4, capstyle="round")
        self.z_up = c.create_line(x, 8, x, sh * self.cfg.zone_up, fill="#9fcfd0", width=4, capstyle="round")
        self.z_down = c.create_line(x, sh * self.cfg.zone_down, x, sh - 8, fill="#9fcfd0", width=4, capstyle="round")
        self.dot = c.create_oval(0, 0, 0, 0, fill=TEAL, outline="white", width=2)
        self.rail.update_idletasks()
        winapi.make_click_through(self.rail)
        if not self.cfg.show_rail:
            self.rail.withdraw()

    def _draw_dot(self):
        e = self.engine
        y = max(0.0, min(1.0, e.gaze)) * self.rail_h
        r = 8
        x = RAIL_W // 2
        self.rail_canvas.coords(self.dot, x - r, y - r, x + r, y + r)
        dim = e.paused or not e.face or not e.calib
        self.rail_canvas.itemconfig(self.dot, fill="#8fbfc0" if dim else TEAL)

    # ---------- calibration ----------
    def start_calibration(self):
        if self.calibrating or self.engine.error:
            return
        self.calibrating = True
        self.rail.withdraw()
        w = self.cal = tk.Toplevel(self.root)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w.geometry(f"{sw}x{sh}+0+0")
        w.attributes("-fullscreen", True)
        w.attributes("-topmost", True)
        w.configure(bg=PAPER, cursor="none")
        w.bind("<Escape>", lambda e: self._end_calibration(None))
        self.cal_canvas = tk.Canvas(w, bg=PAPER, highlightthickness=0)
        self.cal_canvas.pack(fill="both", expand=True)
        w.update_idletasks()
        self.cal_w, self.cal_h = sw, sh
        self._cal_msg("Looking for your face…\n\nSit facing the camera, about an arm's length away.", 0.5)
        self.cal_values = {}
        self._wait_for_face()

    def _cal_msg(self, text, y):
        c = self.cal_canvas
        c.delete("all")
        c.create_text(self.cal_w / 2, self.cal_h * y, text=text, font=("Segoe UI", 18), fill=INK, justify="center")

    def _wait_for_face(self):
        if not self.calibrating:
            return
        if self.engine.face:
            self._cal_msg("Move only your eyes to each dot. Keep your head still.", 0.5)
            self.root.after(1500, lambda: self._cal_point(0))
        else:
            self.root.after(150, self._wait_for_face)

    def _cal_point(self, i):
        if not self.calibrating:
            return
        if i == len(CALIB_POINTS):
            v = self.cal_values
            if Calibration.is_valid(v["top"], v["mid"], v["bottom"]):
                self._end_calibration(Calibration(v["top"], v["mid"], v["bottom"]))
            else:
                self._end_calibration(None, failed=True)
            return
        key, y = CALIB_POINTS[i]
        labels = {"top": "Look at the dot", "mid": "Now the middle dot", "bottom": "Now the bottom dot"}
        c = self.cal_canvas
        c.delete("all")
        cx, cy, r = self.cal_w / 2, self.cal_h * y, 17
        c.create_oval(cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10, fill="#cfe6e6", outline="")
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=TEAL, outline="")
        c.create_text(cx, self.cal_h * (0.62 if y < 0.5 else 0.38), text=labels[key], font=("Segoe UI", 18), fill=INK)
        self.engine.begin_point()
        self.root.after(700, self._collect_on)                      # eyes travel to the dot first
        self.root.after(1700, lambda: self._cal_store(i, key))

    def _collect_on(self):
        self.engine.collect = True

    def _cal_store(self, i, key):
        if not self.calibrating:
            return
        self.cal_values[key] = self.engine.end_point()
        self._cal_point(i + 1)

    def _end_calibration(self, calib, failed=False):
        self.calibrating = False
        self.engine.sampling, self.engine.collect = None, False
        if getattr(self, "cal", None):
            self.cal.destroy()
            self.cal = None
        if calib:
            self.engine.set_calibration(calib)
            self.engine.paused = False
            self.cfg.calibration = calib.to_dict()
            self.cfg.save()
            self.flash = "Calibrated. Read normally; look low to scroll down, high to go back."
        elif failed:
            self.flash = "Calibration was unclear. Move only your eyes to each dot, face a light, and try again."
        self.flash_until = self.root.tk.call("clock", "milliseconds") + 4000
        if self.cfg.show_rail:
            self.rail.deiconify()

    # ---------- loop ----------
    def _tick(self):
        e = self.engine
        while not self.events.empty():
            ev = self.events.get()
            if ev == "pause":
                self.toggle_pause()
            elif ev == "calibrate":
                self.start_calibration()

        if self.cfg.show_rail and not self.calibrating:
            if self.rail.state() == "withdrawn":
                self.rail.deiconify()
            self._draw_dot()
        elif not self.cfg.show_rail and self.rail.state() != "withdrawn":
            self.rail.withdraw()

        # first run: calibrate as soon as the camera is up
        if not e.calib and not self.auto_calibrated and not self.calibrating and not e.error and not e.status:
            self.auto_calibrated = True
            self.start_calibration()

        now = self.root.tk.call("clock", "milliseconds")
        if e.error:
            text, colour = e.error, "#b3261e"
        elif getattr(self, "flash_until", 0) > now:
            text, colour = self.flash, TEAL
        elif e.status:
            text, colour = e.status, SOFT
        elif self.calibrating:
            text, colour = "Calibrating…", SOFT
        elif not e.face:
            text, colour = "Can't see your face. Sit facing the camera.", SOFT
        elif e.paused:
            text, colour = "Paused. Double blink or Ctrl+Alt+N to resume.", SOFT
        else:
            text, colour = f"Eyes on  ·  {e.fps:.0f} fps", TEAL
        if self.status.cget("text") != text:
            self.status.config(text=text, fg=colour)
        self.pause_btn.config(text="Resume" if e.paused else "Pause")
        self.root.after(33, self._tick)

    def run(self):
        self.root.after(100, self._tick)
        self.root.mainloop()

    def quit(self):
        self.cfg.save()
        self.engine.stop()
        self.root.destroy()
