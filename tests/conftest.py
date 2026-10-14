import importlib.util
import pytest


def _cuda_ok() -> bool:
    if importlib.util.find_spec("torch") is None:
        return False
    import torch
    return torch.cuda.is_available()


def pytest_collection_modifyitems(config, items):
    if _cuda_ok():
        return
    skip = pytest.mark.skip(reason="no CUDA / torch on this host")
    for item in items:
        if "cuda" in item.keywords:
            item.add_marker(skip)
