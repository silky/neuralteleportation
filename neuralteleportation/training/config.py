import copy
from dataclasses import dataclass, fields
from typing import Sequence, Callable, Dict, Any, Tuple

from comet_ml import Experiment
from torch import Tensor
from torch.nn.modules.loss import _Loss

from neuralteleportation.utils.logger import BaseLogger


@dataclass
class TrainingConfig:
    optimizer: Tuple[str, Dict[str, Any]] = ("Adam", {"lr": 1e-3})
    epochs: int = 10
    batch_size: int = 32
    device: str = 'cpu'
    comet_logger: Experiment = None
    exp_logger: BaseLogger = None
    log_every_n_batch: int = None
    shuffle_batches: bool = False


@dataclass
class TeleportationTrainingConfig(TrainingConfig):
    cob_range: float = 0.5
    cob_sampling: str = 'within_landscape'
    every_n_epochs: int = 1
    # The ``teleport_fn`` field is required to use the pipeline from the ``training`` module,
    # but it must be declared and initialized by the config classes inheriting from ``TeleportationTrainingConfig``
    # NOTE: Default functions should be set using ``field(default=<function_name>)`` to avoid binding the function
    #       as a method of the dataclass


@dataclass
class TrainingMetrics:
    criterion: _Loss
    metrics: Sequence[Callable[[Tensor, Tensor], Tensor]]


_SERIALIZATION_EXCLUDED_FIELDS = ['comet_logger', 'exp_logger']


def config_to_dict(training_config: TrainingConfig) -> Dict[str, Any]:
    """Creates a dict from a ``TrainingConfig`` instance. It replaces the built-in, generic ``asdict`` for dataclasses.

    It is required to customize the conversion of ``TrainingConfig`` objects to dict since complex objects stored in the
    config (i.e. loggers) can't be automatically pickled and cause the built-in ``asdict`` function to crash.
    """
    from neuralteleportation.experiments.teleport_training import __training_configs__
    training_config_cls_label = {v: k for k, v in __training_configs__.items()}[training_config.__class__]
    result = [("teleport", training_config_cls_label)]
    for field in [f for f in fields(training_config) if f.name not in _SERIALIZATION_EXCLUDED_FIELDS]:
        field_value = getattr(training_config, field.name)
        if callable(field_value):
            field_value = field_value.__name__
        else:
            field_value = copy.deepcopy(field_value)
        result.append((field.name, field_value))
    return dict(result)
