from neuralteleportation.neuralteleportationmodel import NeuralTeleportationModel
import numpy as np
import torch


def test_set_weights(network, input_shape=(1, 1, 28, 28)):
    model = NeuralTeleportationModel(network, input_shape)
    w1 = model.get_weights().detach().numpy()
    model = NeuralTeleportationModel(network, input_shape)
    # w2 = model.get_weights().detach().numpy()

    model.set_weights(w1)
    w3 = model.get_weights().detach().numpy()

    # assert not np.allclose(w1, w2)
    assert np.allclose(w1, w3)


def test_dot_product(network, input_shape=(1, 1, 28, 28), verbose=False):
    model = NeuralTeleportationModel(network=network, input_shape=input_shape)
    x = torch.rand(input_shape, dtype=torch.float)
    y = torch.rand((1, 1, 10, 10), dtype=torch.float)
    pred1 = model(x).detach().numpy()
    w1 = model.get_weights().detach().numpy()

    loss_func = torch.nn.MSELoss()

    grad = model.get_grad(x, y, loss_func, zero_grad=False)

    model.random_teleport(cob_range=0.0001)

    pred2 = model(x).detach().numpy()
    w2 = model.get_weights().detach().numpy()

    diff_average = (w1 - w2).mean()
    dot_prod = np.dot(grad, (w2 - w1))

    print(f'The result of the scalar product is: {dot_prod}')

    # assert np.log10(dot_prod) < -8

    return diff_average


def test_reset_weights(network, input_shape=(1, 1, 28, 28)):
    model = NeuralTeleportationModel(network, input_shape=input_shape)
    w1 = model.get_weights().detach().numpy()
    model.reset_weights()
    w2 = model.get_weights().detach().numpy()

    assert not np.allclose(w1, w2)

if __name__ == '__main__':
    import torch.nn as nn
    from torch.nn.modules import Flatten
    from neuralteleportation.layers.layer_utils import swap_model_modules_for_COB_modules

    cnn_model = torch.nn.Sequential(
        nn.Conv2d(1, 32, 3, 1),
        nn.ReLU(),
        nn.Conv2d(32, 64, 3, stride=2),
        nn.ReLU(),
        Flatten(),
        nn.Linear(9216, 128),
        nn.ReLU(),
        nn.Linear(128, 10)
    )

    mlp_model = torch.nn.Sequential(
        Flatten(),
        nn.Linear(784, 128),
        nn.ReLU(),
        nn.Linear(128, 10)
    )

    cnn_model = swap_model_modules_for_COB_modules(cnn_model)
    mlp_model = swap_model_modules_for_COB_modules(mlp_model)

    test_set_weights(network=mlp_model)
    test_dot_product(network=mlp_model)
    test_reset_weights(network=mlp_model)

    test_set_weights(network=cnn_model)
    test_dot_product(network=cnn_model)
    test_reset_weights(network=cnn_model)
