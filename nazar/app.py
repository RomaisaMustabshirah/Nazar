"""Nazar desktop: scroll any window with your eyes."""
import traceback

from . import winapi
from .config import CONFIG_DIR, Config


def main():
    try:
        winapi.make_dpi_aware()
        from .tracker import Engine
        from .ui import App
        cfg = Config.load()
        engine = Engine(cfg)
        engine.start()
        App(cfg, engine).run()
    except Exception:
        # Nazar.exe has no console, so write the error somewhere you can find it
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        log = CONFIG_DIR / "error.log"
        log.write_text(traceback.format_exc(), encoding="utf-8")
        try:
            from tkinter import Tk, messagebox
            Tk().withdraw()
            messagebox.showerror("Nazar", f"Nazar couldn't start.\n\nDetails were saved to:\n{log}")
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
