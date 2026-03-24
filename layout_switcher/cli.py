from __future__ import annotations

import argparse
import logging
import time

from .config import load_config
from .doctor import run_doctor
from .executor import Executor
from .listener import InputListener
from .processor import Processor
from .translator import Translator


def main() -> None:
    parser = argparse.ArgumentParser(description="Wayland layout fixer daemon")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the layout switcher daemon")
    run_parser.add_argument("--config", help="Path to config.json", default=None)

    subparsers.add_parser("doctor", help="Check local system readiness")

    parser.add_argument("--config", help=argparse.SUPPRESS, default=None)
    args = parser.parse_args()

    command = args.command or "run"
    if command == "doctor":
        raise SystemExit(run_doctor())

    config = load_config(getattr(args, "config", None))
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper(), logging.INFO),
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )

    translator = Translator(config.language.primary, config.language.secondary)
    executor = Executor(config.executor, config.notifications)
    processor = Processor(config, translator, executor)
    listener = InputListener(config.input, processor.handle_key_event)

    listener.start()
    if not listener.wait_until_started(3.0):
        listener.stop()
        message = listener.start_error or "Input listener did not start"
        raise SystemExit(message)
    try:
        while listener.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
