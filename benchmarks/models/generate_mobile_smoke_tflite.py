#!/usr/bin/env python3
"""Generate the tiny redistributable TFLite smoke model.

This script is intentionally offline-only. It uses an already-installed
TensorFlow package when available and otherwise returns a machine-readable
blocker instead of downloading toolchains or model assets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

BLOCKER = {
    "blocker_id": "TFLITE_SMOKE_MODEL_GENERATOR_UNAVAILABLE",
    "blocked_reason": "missing_tensorflow_python_package",
    "pipeline_visible": True,
    "release_blocking": True,
    "resolution": "Install TensorFlow in the benchmark build environment, then rerun this script.",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def generate_model() -> bytes:
    try:
        import numpy as np
        import tensorflow as tf
    except ImportError as exc:
        raise RuntimeError(str(exc)) from exc

    random.seed(7)
    np.random.seed(7)
    tf.random.set_seed(7)

    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(8,), name="input"),
            tf.keras.layers.Dense(
                32,
                activation="relu",
                kernel_initializer=tf.keras.initializers.GlorotUniform(seed=7),
                bias_initializer=tf.keras.initializers.Zeros(),
                name="dense",
            ),
            tf.keras.layers.Dense(
                16,
                activation="relu",
                kernel_initializer=tf.keras.initializers.GlorotUniform(seed=9),
                bias_initializer=tf.keras.initializers.Zeros(),
                name="dense_mid",
            ),
            tf.keras.layers.Dense(
                2,
                activation="softmax",
                kernel_initializer=tf.keras.initializers.GlorotUniform(seed=11),
                bias_initializer=tf.keras.initializers.Zeros(),
                name="scores",
            ),
        ],
        name="mobile_smoke",
    )

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = []
    return converter.convert()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).with_name("mobile_smoke.tflite"),
        help="Output .tflite path.",
    )
    parser.add_argument(
        "--status-json",
        type=Path,
        help="Optional path for machine-readable generation status.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    status: dict[str, object]
    try:
        model = generate_model()
    except RuntimeError:
        status = {"status": "blocked", **BLOCKER, "output": str(args.out)}
        if args.status_json:
            args.status_json.write_text(
                json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        print(json.dumps(status, sort_keys=True), file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(model)
    status = {
        "status": "generated",
        "output": str(args.out),
        "size_bytes": len(model),
        "sha256": sha256_bytes(model),
    }
    if args.status_json:
        args.status_json.write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(status, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
