"""Nazar desktop: scroll any window with your eyes."""
from . import winapi
from .config import Config
from .tracker import Engine
from .ui import App


def main():
    winapi.make_dpi_aware()
    cfg = Config.load()
    engine = Engine(cfg)
    engine.start()
    App(cfg, engine).run()


if __name__ == "__main__":
    main()
