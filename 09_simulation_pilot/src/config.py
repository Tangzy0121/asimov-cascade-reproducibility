"""Configuration loader with frozen-hash verification.

Loads config/preregistered.yaml and (outside of test contexts) asserts that its
SHA-256 matches config/preregistered.sha256. The frozen hash is the guard that
no parameter changed after preregistration.
"""
import hashlib
import os

import yaml

_WORK = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_PATH = os.path.join(_WORK, "config", "preregistered.yaml")
HASH_PATH = os.path.join(_WORK, "config", "preregistered.sha256")


def config_sha256(path=CONFIG_PATH):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def frozen_hash(path=HASH_PATH):
    with open(path) as f:
        return f.read().split()[0].strip()


class Config:
    """Thin attribute wrapper over the preregistered YAML dict."""

    def __init__(self, data, sha256):
        self._data = data
        self.sha256 = sha256
        for k, v in data.items():
            setattr(self, k, v)

    def as_dict(self):
        return self._data


def load_config(verify_hash=False):
    """Load the preregistered configuration.

    verify_hash=True enforces a match with config/preregistered.sha256; the main
    experiment runner uses this before any main trial starts (plan Task 1).
    Tests use verify_hash=False so a mid-calibration config can still be tested.
    """
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    digest = config_sha256()
    if verify_hash:
        frozen = frozen_hash()
        if digest != frozen:
            raise RuntimeError(
                f"configuration hash mismatch: file={digest} frozen={frozen}")
    return Config(data, digest)
