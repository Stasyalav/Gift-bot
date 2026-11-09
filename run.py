"""Точка входа: python run.py."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.bot import run_bot
from app.config import ConfigError, load_config

PROJECT_ROOT = Path(__file__).resolve().parent


def main() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Ошибка настроек: {exc}", file=sys.stderr)
        return 1

    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(logs_dir / "bot.log", encoding="utf-8"),
        ],
    )

    try:
        run_bot(config)
    except KeyboardInterrupt:
        print("\nБот остановлен.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
