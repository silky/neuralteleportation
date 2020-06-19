from neuralteleportation.neuralteleportationmodel import NeuralTeleportationModel
from neuralteleportation.models.model_zoo.vggcob import vgg16COB
import numpy as np
import matplotlib.pyplot as plt
import torch


def plot_histogram_teleported_gradients(network, input_shape=(100, 1, 28, 28), nb_iterations=200, n_iter=20,
                                        network_descriptor='') -> None:
    """
    This method computes an histogram of angles between the gradient of a network with gradients of teleportations
    of it while the change of basis increases and is centered around 1. We assume that network is a ReLU network
    or a teleportation of it (with any change of basis),and computes statistics within the same landscape
    by applying only positive changes of basis.

    Args:
        network :               The COB model (use swap_model_modules_for_COB_modules to network before passing it
                                to this method) that we want statistics from its landscape.

        input_shape :           The shape of the input.  By default, simulate batched of 100 grayscale 28x28 images
                                (it will be used by the networkgrapher of the model,
                                the values is not important for the test at hand)

        nb_iterations:          The number of times the network is teleported and the scalar product calculated. An
                                average is then calculated.

        n_iter:                 The number of partitions of the interval [0.001, 0.7] to sample the change of basis

        network_descriptor:     String describing the content of the network
    """

    model = NeuralTeleportationModel(network=network, input_shape=input_shape)

    w1 = model.get_weights().detach().numpy()

    loss_func = torch.nn.MSELoss()

    # This measures the increase of the change of basis in each iteration
    cob = np.linspace(0.001, 0.7, n_iter)

    for i in range(n_iter):
        rand_angle_results = []
        rand_rand_angle_results = []
        grad_grad_angle_results = []

        for _ in range(nb_iterations):
            x = torch.rand(input_shape, dtype=torch.float)
            y = torch.rand((input_shape[0], 10), dtype=torch.float)

            grad = model.get_grad(x, y, loss_func, zero_grad=False)
            model.set_weights(w1)
            model.random_teleport(cob_range=cob[i])
            grad_tele = model.get_grad(x, y, loss_func, zero_grad=False)

            random_vector = torch.rand(grad.shape, dtype=torch.float)-0.5
            random_vector2 = torch.rand(grad.shape, dtype=torch.float)-0.5

            # Normalized scalar product
            grad_grad_prod = np.longfloat(np.dot(grad, grad_tele) /
                                          (np.linalg.norm(grad)*np.linalg.norm(grad_tele)))
            grad_grad_angle = np.degrees(np.arccos(grad_grad_prod))

            rand_dot_prod = np.longfloat(np.dot(grad, random_vector) /
                                         (np.linalg.norm(grad)*np.linalg.norm(random_vector)))
            rand_angle = np.degrees(np.arccos(rand_dot_prod))

            rand_rand_dot_prod = np.longfloat(np.dot(random_vector2, random_vector) /
                                              (np.linalg.norm(random_vector2)*np.linalg.norm(random_vector)))
            rand_rand_angle = np.degrees(np.arccos(rand_rand_dot_prod))

            rand_angle_results.append(rand_angle)
            rand_rand_angle_results.append(rand_rand_angle)
            grad_grad_angle_results.append(grad_grad_angle)

        rand_angle_results = np.array(rand_angle_results)
        rand_rand_angle_results = np.array(rand_rand_angle_results)
        grad_grad_angle = np.array(grad_grad_angle)

        # Limits manually fixed to appreciate difference between the angles
        delta = np.maximum(1.0, rand_rand_angle_results.std() * 3)
        x_min = 90 - delta
        x_max = 90 + delta

        plt.subplot(3, 1, 1)

        bin_height, bin_boundary = np.histogram(np.array(grad_grad_angle_results))
        width = bin_boundary[1] - bin_boundary[0]
        bin_height = bin_height / float(max(bin_height))
        plt.subplot(3, 1, 1)
        plt.bar(bin_boundary[:-1], bin_height, width=np.maximum(width, 0.1), color='r')
        plt.title(f'{network_descriptor}: COB range: {cob[i]}, 'f'{nb_iterations:} iterations')
        plt.xlim(0, 100)
        plt.legend(['Gradient \n vs \n Teleported gradient'])

        bin_height, bin_boundary = np.histogram(np.array(rand_angle_results))
        width = bin_boundary[1] - bin_boundary[0]
        bin_height = bin_height / float(max(bin_height))
        plt.subplot(3, 1, 2)
        plt.bar(bin_boundary[:-1], bin_height, width=np.maximum(width, 0.1), color='b')
        plt.xlim(x_min, x_max)
        plt.legend(['Gradient\n vs \n Random Vector'])

        bin_height, bin_boundary = np.histogram(np.array(rand_rand_angle_results))
        width = bin_boundary[1] - bin_boundary[0]
        bin_height = bin_height / float(max(bin_height))
        plt.subplot(3, 1, 3)
        plt.bar(bin_boundary[:-1], bin_height, width=np.maximum(width, 0.1), color='g')
        plt.xlim(x_min, x_max)
        plt.legend(['Random Vector\n vs \n Random Vector'])

        plt.xlabel('Angle in degrees')
        plt.show()


def plot_difference_teleported_gradients(network, input_shape=(4, 3, 32, 32), nb_teleportations=100,
                                         network_descriptor=''):
    """
    This method plots the difference of the gradient of model and the gradient of a teleportation, by increasing the
    cob_range from 0.1 to 0.9 in n_iter iterations for within_landscape cob_sampling. Each gradient is normalized by the norm of
    the weights producing the corresponding gradient.

    Args:
        network:                COB model to test.

        input_shape:            The shape of the input.

        nb_teleportations:      Number of teleportations computed for each cob_range.

        network_descriptor:     Name of the model for distinction
    """
    model = NeuralTeleportationModel(network=network, input_shape=input_shape)

    x = torch.rand(input_shape, dtype=torch.float)
    y = torch.randint(low=0, high=9, size=(input_shape[0],))

    loss_func = torch.nn.CrossEntropyLoss()

    original_weights = model.get_weights().detach().numpy()
    original_grad = model.get_grad(x, y, loss_func, zero_grad=False).numpy()
    original_grad = original_grad / np.linalg.norm(original_weights)

    differences = []
    variance = []

    # Grid to sample the change of basis
    n_iter = 20
    x_axis = np.linspace(0.1, 0.9, n_iter)

    for i in range(n_iter):
        to_compute_mean = []
        for _ in range(nb_teleportations):
            model.set_weights(original_weights)
            model.random_teleport(cob_range=x_axis[i], sampling_type='within_landscape')

            teleported_weights = model.get_weights().detach().numpy()
            teleported_grad = model.get_grad(x, y, loss_func, zero_grad=False).numpy()
            teleported_grad = teleported_grad / np.linalg.norm(teleported_weights)

            diff = abs(np.linalg.norm(original_grad)-np.linalg.norm(teleported_grad))
            to_compute_mean.append(diff)

        variance.append(np.std(to_compute_mean))
        differences.append(np.mean(to_compute_mean))

    variance = np.array(variance)
    differences = np.array(differences)
    x_axis = np.array(x_axis)

    plt.errorbar(x_axis, differences, yerr=variance)
    plt.plot(x_axis, differences)

    plt.title('Difference of normalized magnitude between teleportations of the gradient')
    plt.title(f'{network_descriptor}, 'f'{nb_teleportations:} iterations')
    plt.ylabel('| ||Grad||/||W|| - ||Tel.Grad||/||Tel.W|| |')
    plt.xlabel('cob_range')
    plt.show()


if __name__ == '__main__':
    import torch.nn as nn
    from torch.nn.modules import Flatten
    from neuralteleportation.layers.layer_utils import swap_model_modules_for_COB_modules
    from neuralteleportation.models.model_zoo.mlpcob import MLPCOB

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

    mlp_model = MLPCOB(num_classes=10, hidden_layers=(128, 128,))
    input_shape_mlp = (100, 1, 28, 28)

    cnn_model = swap_model_modules_for_COB_modules(cnn_model)
    vgg16_model = vgg16COB(num_classes=10)

    plot_histogram_teleported_gradients(network=mlp_model, input_shape=input_shape_mlp, network_descriptor='MLP')
    plot_histogram_teleported_gradients(network=cnn_model, network_descriptor='CNN')
    plot_histogram_teleported_gradients(network=vgg16_model, input_shape=(32, 3, 32, 32), network_descriptor='VGG16')

    plot_difference_teleported_gradients(network=mlp_model, input_shape=input_shape_mlp, network_descriptor='MLP')
    plot_difference_teleported_gradients(network=cnn_model, input_shape=(100, 1, 28, 28), network_descriptor='CNN')
    plot_difference_teleported_gradients(network=vgg16_model, input_shape=(32, 3, 32, 32), network_descriptor='VGG16')
