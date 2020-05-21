import torch
import torch.nn as nn

from neuralteleportation.layers.layer_utils import swap_model_modules_for_COB_modules
from neuralteleportation.neuralteleportationmodel import NeuralTeleportationModel


def test_swap_module(network, model_name="MLP", input_shape=(1, 1, 28, 28)):
    cob_module = swap_model_modules_for_COB_modules(network, inplace=False)

    assert not any(
        type(module) in [nn.Linear, nn.Conv2d] for module in cob_module.modules()
    )

    print("Successfully swaped Linear and Conv2d layers for COB layers in " + model_name + " model.")
    cob_module = NeuralTeleportationModel(cob_module, input_shape)
    assert not cob_module.random_teleport(), "Teleportation failed for model " + model_name
    print("Succesfully teleported swaped models " + model_name + " model.")


if __name__ == '__main__':
    mlp_model = torch.nn.Sequential(
        nn.Flatten(),
        nn.Linear(784, 128),
        nn.ReLU(),
        nn.Linear(128, 10)
    )

    cnn_model = torch.nn.Sequential(
        nn.Conv2d(1, 32, 3, 1),
        nn.ReLU(),
        nn.Conv2d(32, 64, 3, stride=2),
        nn.ReLU(),
        nn.Flatten(),
        nn.Linear(9216, 128),
        nn.ReLU(),
        nn.Linear(128, 10)
    )

    test_swap_module(mlp_model, model_name="MLP")
    test_swap_module(cnn_model, model_name="Convolutional")
