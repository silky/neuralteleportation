from dataclasses import dataclass
from typing import Dict, Tuple, Union
import sys

##TODO take off for PR
import sys
sys.path.append('/content/drive/My Drive/repos/neuralteleportation/')
sys.path.append('/content/drive/My Drive/repos/neuralteleportation/neuralteleportation/')
sys.path.append('/content/drive/My Drive/repos/neuralteleportation/training')
sys.path.append('/content/drive/My Drive/repos/neuralteleportation/neuralteleportation/experiments')

import torch.optim as optim
from torch import nn
from torch.optim.optimizer import Optimizer
from torch.utils.data import DataLoader, Dataset

from utils.micro_tp_utils import *
from neuralteleportation.training.config import TrainingMetrics, TrainingConfig
from neuralteleportation.training.training import test, train_epoch


@dataclass
class MicroTeleportationTrainingConfig(TrainingConfig):
    input_shape: Tuple[int, int, int] = (1, 28, 28)
    starting_epoch: int = 1
    num_teleportations: int = 1


def train(model: Union[nn.Module, Tuple[str, nn.Module]], train_dataset: Dataset, metrics: TrainingMetrics,
          config: MicroTeleportationTrainingConfig, val_dataset: Dataset = None, optimizer: Optimizer = None) \
        -> Dict[str, nn.Module]:
    # If the model is not named (at the first iteration), initialize its name based on its class
    if type(model) is tuple:
        model_name, model = model
    else:
        model_name = model.__class__.__name__

    # Initialize an optimizer if there isn't already one
    if optimizer is None:
        optimizer = optim.SGD(model.parameters(), lr=config.lr)

    train_loader = DataLoader(train_dataset, batch_size=config.batch_size)

    # Always move model to GPU before training
    if torch.cuda.is_available():
        model.cuda()

    stopping_epoch = max(config.starting_epoch, config.epochs + 1)
    for epoch in range(config.starting_epoch, stopping_epoch):
        print(f'Training epoch {epoch} for {model_name} ...')
        train_epoch(model, metrics.criterion, optimizer, train_loader, epoch, device=config.device)
        if val_dataset:
            val_res = test(model, val_dataset, metrics, config)
            print("Validation: {}".format(val_res))

    # Always move model off-GPU after training
    model.cpu()

    trained_models = {f'{model_name}_0': model}

    return trained_models

if __name__ == '__main__':
    from neuralteleportation.training.experiment_setup import *
    from neuralteleportation.metrics import accuracy
    from neuralteleportation.training.experiment_run import run_multi_output_training

    metrics = TrainingMetrics(nn.CrossEntropyLoss(), [accuracy])

    # Run on CIFAR10
    cifar10_train, cifar10_val, cifar10_test = get_dataset_subsets("cifar10")

    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    config = MicroTeleportationTrainingConfig(input_shape=(3, 32, 32), device=device, batch_size=10,
                                              num_teleportations=1, epochs=5)

    models = get_models_for_dataset("cifar10")
    models.append(MLPCOB(num_classes=10, input_shape=config.input_shape, hidden_layers=(512, 1024, 512)))
    model = MLPCOB(num_classes=10, input_shape=config.input_shape, hidden_layers=(10, 10, 10))
    models = [model]

    Path('models').mkdir(parents=True, exist_ok=True)

    for model in models:
        # compute gradient difference without training
        get_raw_random_teleportations_data(network=model, dataset=cifar10_test,
                                           network_descriptor=f'{model.__class__.__name__} on CIFAR10',
                                           device=device)

        # either fetch saved trained model or train the models
        if Path(f'models/{model.__class__.__name__}_cifar10').exists():

            print(f'fetchning existing model: models/{model.__class__.__name__}_untrained')
            model.load_state_dict(torch.load(f'models/{model.__class__.__name__}_untrained'))
        else:
            # train the network and then compute difference of grandients
            print(f'training model: {model.__class__.__name__}_cifar10')
            run_multi_output_training(train, [model], config, metrics, cifar10_train, cifar10_test,
                                      val_set=cifar10_val)
            torch.save(model.state_dict(), f'models/{model.__class__.__name__}_cifar10')

        # compute gradient difference with trained model
        get_raw_random_teleportations_data(network=model, dataset=cifar10_test,
                                           network_descriptor=f'{model.__class__.__name__} on CIFAR10',
                                           device=device)



    # # Run on CIFAR100
    cifar100_train, cifar100_val, cifar100_test = get_dataset_subsets("cifar100")

    models = get_models_for_dataset("cifar100")
    models.append(MLPCOB(num_classes=100, input_shape=config.input_shape, hidden_layers=(10, 10, 10)))

    for model in models:
        # compute gradient difference without training
        get_raw_random_teleportations_data(network=model, dataset=cifar100_test,
                                           network_descriptor=f'{model.__class__.__name__} on CIFAR10',
                                           device=device)

        # either fetch saved trained model or train the models
        if Path(f'models/{model.__class__.__name__}_cifar100').exists():

            print(f'fetchning existing model: models/{model.__class__.__name__}_untrained')
            model.load_state_dict(torch.load(f'models/{model.__class__.__name__}_untrained'))
        else:
            # train the network and then compute difference of grandients
            print(f'training model: {model.__class__.__name__}_cifar100')
            run_multi_output_training(train, [model], config, metrics, cifar100_train, cifar100_test,
                                      val_set=cifar100_val)
            torch.save(model.state_dict(), f'models/{model.__class__.__name__}_cifar100')

        # compute gradient difference with trained model
        get_raw_random_teleportations_data(network=model, dataset=cifar100_test,
                                           network_descriptor=f'{model.__class__.__name__} on CIFAR10',
                                           device=device)

    print()
