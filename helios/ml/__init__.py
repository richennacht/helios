"""Machine-learning modules for evidence-producing Helios features.

Optional heavyweight model dependencies are imported lazily so rooftop
inference remains usable without the solar challenger extras.
"""

from typing import Any

__all__ = ["SolarOutputModel", "train_and_evaluate"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from helios.ml.solar_output import SolarOutputModel, train_and_evaluate

        return {
            "SolarOutputModel": SolarOutputModel,
            "train_and_evaluate": train_and_evaluate,
        }[name]
    raise AttributeError(name)
