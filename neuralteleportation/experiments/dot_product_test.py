# This script validates that the scalar product between a line defined by a set of weights and its teleporation
# and the gradient calculated a that point is null. It does this for many sampling types
# (see change get_random_cob in changeofbaseutils.py)

from neuralteleportation.neuralteleportationmodel import NeuralTeleportationModel

import numpy as np
import torch
import matplotlib.pyplot as plt

red = "\033[31m"
reset = "\033[0m"


def test_dot_product(network, input_shape=(100, 1, 28, 28), nb_teleport=200, network_descriptor='',
                     sampling_types=['usual', 'symmetric', 'negative', 'zero']) -> None:
    """
    This method tests the scalar product between the teleporation line and the gradient, as well as between a random
    vector and the gradient for nullity. It then displays the histograms of the calculated scalar products.

    Args:
        network :               the model to which we wish to assign weights

        input_shape :           the shape of the input.  By default, simulate batched of 100 grayscale 28x28 images
                                (it will be used by the networkgrapher of the model,
                                the values is not important for the test at hand)

        nb_teleport:            The number of time the network is teleported and the scalar product calculated. An
                                average is then calculated.

        network_descriptor:     String describing the content of the network

        sampling_types :        Teleportation sampling types
    """

    model = NeuralTeleportationModel(network=network, input_shape=input_shape)

    w1 = model.get_weights().detach().numpy()

    iterations = range(0, nb_teleport)
    loss_func = torch.nn.MSELoss()

    tol = 1e-2

    for sampling_type in sampling_types:
        for power in range(-3, 1):
            cob = 10 ** power
            angle_results = []
            rand_angle_results = []
            rand_rand_angle_results = []
            rand_micro_angle_results = []
            grad_grad_angle_results = []

            for _ in iterations:
                x = torch.rand(input_shape, dtype=torch.float)
                y = torch.rand((100, 10), dtype=torch.float)
                grad = model.get_grad(x, y, loss_func, zero_grad=False)

                model.set_weights(w1)
                model.random_teleport(cob_range=cob, sampling_type=sampling_type)
                w2 = model.get_weights().detach().numpy()
                grad_tele = model.get_grad(x, y, loss_func, zero_grad=False)
                micro_teleport_vec = (w2 - w1)

                random_vector = torch.rand(grad.shape, dtype=torch.float)-0.5
                random_vector2 = torch.rand(grad.shape, dtype=torch.float)-0.5

                # Normalized scalar product
                dot_prod = np.longfloat(np.dot(grad, micro_teleport_vec) /
                                        (np.linalg.norm(grad)*np.linalg.norm(micro_teleport_vec)))
                angle = np.degrees(np.arccos(dot_prod))

                grad_grad_prod = np.longfloat(np.dot(grad, grad_tele) /
                                              (np.linalg.norm(grad)*np.linalg.norm(grad_tele)))
                grad_grad_angle = np.degrees(np.arccos(grad_grad_prod))

                rand_dot_prod = np.longfloat(np.dot(grad, random_vector) /
                                             (np.linalg.norm(grad)*np.linalg.norm(random_vector)))
                rand_angle = np.degrees(np.arccos(rand_dot_prod))

                rand_rand_dot_prod = np.longfloat(np.dot(random_vector2, random_vector) /
                                                  (np.linalg.norm(random_vector2)*np.linalg.norm(random_vector)))
                rand_rand_angle = np.degrees(np.arccos(rand_rand_dot_prod))

                rand_micro_dot_prod = np.longfloat(np.dot(random_vector2, micro_teleport_vec) /
                                                  (np.linalg.norm(random_vector2)*np.linalg.norm(micro_teleport_vec)))
                rand_micro_angle = np.degrees(np.arccos(rand_micro_dot_prod))


                # Arbitrary precision threshold for nullity comparison
                failed = (not np.allclose(dot_prod, 0, atol=tol))
                rand_failed = (not np.allclose(rand_dot_prod, 0, atol=tol))
                target_angle = 90

                angle_results.append(angle)
                rand_angle_results.append(rand_angle)
                rand_rand_angle_results.append(rand_rand_angle)
                rand_micro_angle_results.append(rand_micro_angle)
                grad_grad_angle_results.append(grad_grad_angle)

            angle_results = np.array(angle_results)
            rand_angle_results = np.array(rand_angle_results)
            rand_rand_angle_results = np.array(rand_rand_angle_results)
            rand_micro_angle_results = np.array(rand_micro_angle_results)
            grad_grad_angle = np.array(grad_grad_angle)

            print(f'The result of the scalar product between the gradient and a micro-teleporation vector is: '
                  f'{red * failed}{np.round(angle_results.mean(), abs(int(np.log10(tol))))}',
                  f' (!=0 => FAILED!)' * failed,
                  f'{reset}',
                  f' using {sampling_type} sampling type',
                  f', the angle is {angle}°',
                  f', the delta in angle is {angle - target_angle}°\n',
                  f'The scalar product  between the gradient and a random vector is: ',
                  f'{red * rand_failed}{rand_angle_results.mean()}',
                  f' (!=0 => FAILED!)' * rand_failed,
                  f'{reset}',
                  f', and the angle is {rand_angle}°',
                  f', the delta in angle is {rand_angle - target_angle}°\n',
                  sep='')

            # This conditional display is necessary because some sampling type/COB combinations produce such a narrow
            # distribution for micro-teleportation that pyplot is not able to display them at all
            delta = np.maximum(1.0, rand_rand_angle_results.std()*3)
            x_min = 90-delta
            x_max = 90+delta

            plt.subplot(5, 1, 1)

            bin_height, bin_boundary = np.histogram(np.array(angle_results))
            width = bin_boundary[1] - bin_boundary[0]
            bin_height = bin_height / float(max(bin_height))
            plt.bar(bin_boundary[:-1], bin_height, width=np.maximum(width, 0.05))
            plt.title(f'{network_descriptor}: Sampling type: {sampling_type}, cob range: {cob}, 'f'{nb_teleport:} iter')
            plt.legend(['Micro-teleportation\n vs \n Gradient'])
            plt.xlim(x_min, x_max)

            bin_height, bin_boundary = np.histogram(np.array(rand_micro_angle_results))
            width = bin_boundary[1] - bin_boundary[0]
            bin_height = bin_height / float(max(bin_height))
            plt.subplot(5, 1, 2)
            plt.bar(bin_boundary[:-1], bin_height, width=np.maximum(width, 0.1), color='g')
            plt.xlim(x_min, x_max)
            plt.legend(['Micro-teleportation\n vs \n Random Vector'])

            bin_height, bin_boundary = np.histogram(np.array(rand_angle_results))
            width = bin_boundary[1] - bin_boundary[0]
            bin_height = bin_height / float(max(bin_height))
            plt.subplot(5, 1, 3)
            plt.bar(bin_boundary[:-1], bin_height, width=np.maximum(width, 0.1), color='g')
            plt.xlim(x_min, x_max)
            plt.legend(['Gradient\n vs \n Random Vector'])

            bin_height, bin_boundary = np.histogram(np.array(rand_rand_angle_results))
            width = bin_boundary[1] - bin_boundary[0]
            bin_height = bin_height / float(max(bin_height))
            plt.subplot(5, 1, 4)
            plt.bar(bin_boundary[:-1], bin_height, width=np.maximum(width, 0.1), color='g')
            plt.xlim(x_min, x_max)
            plt.legend(['Random Vector\n vs \n Random Vector'])

            bin_height, bin_boundary = np.histogram(np.array(grad_grad_angle_results))
            width = bin_boundary[1] - bin_boundary[0]
            bin_height = bin_height / float(max(bin_height))
            plt.subplot(5, 1, 5)
            plt.bar(bin_boundary[:-1], bin_height, width=np.maximum(width, 0.1), color='g')
            plt.xlim(0, 100)
            plt.legend(['Grad \n vs \n Teleported grad'])

            plt.xlabel('Angle in degrees')
            plt.show()


if __name__ == '__main__':
    import torch.nn as nn
    from torch.nn.modules import Flatten
    from neuralteleportation.layers.layer_utils import swap_model_modules_for_COB_modules
    plt.close('all')

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
        nn.Linear(2, 5),
        nn.ReLU(),
        nn.Linear(5, 5),
        nn.ReLU(),
        nn.Linear(5, 10)
    )

    cnn_model = swap_model_modules_for_COB_modules(cnn_model)
    mlp_model = swap_model_modules_for_COB_modules(mlp_model)

    test_dot_product(network=mlp_model, input_shape=(100, 1, 2, 1), network_descriptor='MLP')
    test_dot_product(network=cnn_model, network_descriptor='CNN')
