"""Shared logging setup for the Fabric-notebook-equivalent entrypoints under
python/. Reads configs/logging.yml so behaviour is consistent whether a
script is run locally, in CI, or as a scheduled Fabric notebook.
"""
from __future__ import annotations

import logging
import logging.config
from pathlib import Path

import yaml

from supply_chain.config import ROOT


def configure_logging(config_path: Path | None = None) -> None:
    config_path = config_path or ROOT / "configs/logging.yml"
    if config_path.exists():
        logging.config.dictConfig(yaml.safe_load(config_path.read_text()))
    else:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
