"""Checkpoints en un único archivo .npz: metadatos JSON + arreglos NumPy (sin pickle)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple, Union

import numpy as np

META_KEY = "__meta__"


def save_checkpoint(path: Union[str, Path], meta: dict, arrays: Dict[str, np.ndarray]) -> Path:
    path = Path(path).with_suffix(".npz")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **{META_KEY: np.array(json.dumps(meta))}, **arrays)
    return path


def load_checkpoint(path: Union[str, Path]) -> Tuple[dict, Dict[str, np.ndarray]]:
    with np.load(Path(path), allow_pickle=False) as data:
        meta = json.loads(data[META_KEY].item())
        arrays = {key: data[key] for key in data.files if key != META_KEY}
    return meta, arrays
