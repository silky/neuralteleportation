from copy import deepcopy
from typing import Callable, Sequence

from torch import nn
from torch.optim import Optimizer
from torchvision.datasets import VisionDataset

from neuralteleportation.neuralteleportationmodel import NeuralTeleportationModel
from neuralteleportation.training.config import TrainingConfig, TrainingMetrics, config_to_dict
from neuralteleportation.training.training import test, train


def run_model(model: nn.Module, config: TrainingConfig, metrics: TrainingMetrics,
              train_set: VisionDataset, test_set: VisionDataset, val_set: VisionDataset = None,
              optimizer: Optimizer = None) -> None:
    if isinstance(model, NeuralTeleportationModel):
        model_cls = model.network.__class__
    else:
        model_cls = model.__class__
    print(f"Training {model_cls.__name__}")

    # Always log parameters (to enable useful filtering options in the web interface)
    config.comet_logger.log_parameters(config_to_dict(config))

    with config.comet_logger.train():
        trained_model = train(model, train_set, metrics, config,
                              val_dataset=val_set, optimizer=optimizer)

    # Ensure the model is on the correct device before testing
    # This avoids problem in case models are shuffled between CPU and GPU during training
    trained_model.to(config.device)

    with config.comet_logger.test():
        print("Testing {}: {} \n".format(model.__class__.__name__,
                                         test(trained_model, test_set, metrics, config)))
        print()


def run_multi_output_training(train_fct: Callable, models: Sequence[nn.Module],
                              config: TrainingConfig, metrics: TrainingMetrics,
                              train_set: VisionDataset, test_set: VisionDataset,
                              val_set: VisionDataset = None) -> None:
    for model in models:
        print(f"Training {model.__class__.__name__}")
        trained_models = train_fct(model, train_dataset=train_set, metrics=metrics, config=deepcopy(config),
                                   val_dataset=val_set)
        for id, trained_model in trained_models.items():
            # Ensure the model is on the correct device before testing
            # This avoids problem in case models are shuffled between CPU and GPU during training
            trained_model.to(config.device)

            print("Testing {}: {} \n".format(
                id, test(trained_model, test_set, metrics, config)))
        print()
