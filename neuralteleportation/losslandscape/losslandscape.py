import torch
import torch.nn as nn
import numpy as np

from typing import Tuple, List
from dataclasses import dataclass

from torch.utils.data.dataset import Dataset
from sklearn.decomposition import PCA

from neuralteleportation.neuralteleportationmodel import NeuralTeleportationModel
from neuralteleportation.training.training import test, train_epoch
from neuralteleportation.training.config import TrainingConfig, TrainingMetrics


@dataclass
class LandscapeConfig(TrainingConfig):
    training_split: float = 0.5,
    cob_range: float = 0.5,
    cob_sampling: str = 'positive'


def generate_random_2d_vector(weights: torch.Tensor, normalize: bool = True, seed: int = 12345) -> torch.Tensor:
    """
        Generates a random vector of size equals to the weights of the model.
    """
    # torch.manual_seed(seed)
    direction = torch.randn(weights.size())
    if normalize:
        normalize_direction(direction, weights)
    return direction


def normalize_direction(direction: torch.Tensor, weights: torch.Tensor):
    """
        Apply a filter normalization to the direction vector.
        d <- d/||d|| * ||w||

        This process is a inplace operation.
    """
    assert len(direction) == len(weights), "Direction must have the same size as model weights"
    w = weights.detach().cpu()
    direction.mul_(w) / direction.norm()


def compute_angle(vec1: torch.Tensor, vec2: torch.Tensor) -> torch.Tensor:
    """
        Calculate the angle in degree between two torch tensors.
    """
    # For some reasons torch.rad2deg and torch.deg2rad function are not there anymore...
    return torch.acos(torch.dot(vec1, vec2) / (vec1.norm() * vec2.norm()))


def generate_teleportation_training(model: NeuralTeleportationModel,
                                    trainset: Dataset,
                                    metric: TrainingMetrics,
                                    config: LandscapeConfig) -> Tuple[List[torch.Tensor], torch.Tensor]:
    """
        Training function wrapper to get all the weights after a full training epochs.

        Return:
            list of torch.Tensor of the model's weights for each epochs,
            list of values of the loss at each epochs,
            the last set of weights.
    """
    w = [model.get_weights().clone().detach().cpu()]
    trainloader = DataLoader(trainset, batch_size=config.batch_size, drop_last=True)
    optim = torch.optim.Adam(model.parameters(), lr=config.lr)

    for e in range(config.epochs):
        train_epoch(model, metric.criterion, train_loader=trainloader, optimizer=optim, epoch=e, device=config.device)
        w.append(model.get_weights().clone().detach().cpu())

        if e == int(config.epochs * config.training_split):
            print("Teleporting Model...")
            model.random_teleport(config.cob_range, config.cob_sampling)
            w.append(model.get_weights().clone().detach().cpu())
            optim = torch.optim.Adam(model.parameters(), lr=config.lr)

    final = w[-1::][0]
    return w, final


def generate_contour_loss_values(model: NeuralTeleportationModel, directions: Tuple[torch.Tensor, torch.Tensor],
                                 surface: torch.Tensor, trainset: Dataset, metric: TrainingMetrics,
                                 config: TrainingConfig) -> Tuple[List, List]:
    """
        Generate a tensor containing the loss values from a given model.
    """
    w = model.get_weights()
    loss = []
    acc = []
    delta, eta = directions
    for _, x in enumerate(surface[0]):
        for _, y in enumerate(surface[1]):
            print("Evaluating [{:.3f}, {:.3f}]".format(x.item(), y.item()))
            x, y = x.to(config.device), y.to(config.device)

            # L (w + alpha*delta + beta*eta)
            model.set_weights(w + (delta * x + eta * y).to(config.device))
            results = test(model, trainset, metric, config)

            loss.append(results['loss'])
            acc.append(results['accuracy'])

    return loss, acc


def generate_weights_direction(origin_weight, M: List[torch.Tensor]) -> Tuple[torch.Tensor, torch.Tensor]:
    """
        Generate a tensor of the 2 most explanatory directions from the matrix
        M = [W0 - Wn, ... ,Wn-1 - Wn]

        This technic was use by:
            Authors: Hao Li, Zheng Xu, Gavin Taylor, Christoph Studer and Tom Goldstein.
            Title: Visualizing the Loss Landscape of Neural Nets. NIPS, 2018.
            Source Code: https://github.com/tomgoldstein/loss-landscape

        returns:
            Tuple containing the x and y directions vectors. (only use x if doing a 1D plotting)
    """
    M = [m.numpy() for m in M]
    print("Appliying PCA on matrix...")
    pca = PCA(n_components=2)
    pca.fit(M)
    pc1 = torch.tensor(pca.components_[0], dtype=original_w.dtype)
    pc2 = torch.tensor(pca.components_[1], dtype=original_w.dtype)

    angle = compute_angle(pc1, pc2)

    print("Angle between pc1 and pc2 is {:3f}".format(angle))
    assert torch.isclose(angle, torch.tensor(1.0, dtype=torch.float), atol=1), "The PCA component " \
                                                                               "are not indenpendent "
    return torch.mul(pc1, origin_weight.cpu()), torch.mul(pc2, origin_weight.cpu())


def generate_weight_trajectory(checkpoints: List[torch.Tensor],
                               direction: Tuple[torch.Tensor, torch.Tensor]) -> Tuple[torch.Tensor, torch.Tensor]:
    """
        Draw the model weight trajectory over all the train epochs. It is always using a orthogonal projection
        to the 2D space.
    """
    x_direction = direction[0]
    y_direction = direction[1]
    x = []
    y = []
    for w in checkpoints:
        x.append(torch.dot(w, x_direction) / x_direction.norm())
        y.append(torch.dot(w, y_direction) / y_direction.norm())
    x = torch.tensor(x)
    y = torch.tensor(y)
    return x, y


def plot_contours(x: torch.Tensor, y: torch.Tensor, loss: np.ndarray,
                  weight_traj: Tuple[torch.Tensor, torch.Tensor] = None, teleport_idx: int = 0, levels: int = 25, ):
    # plt.figure()
    plt.contourf(x, y, loss, cmap='coolwarm', origin='lower', levels=levels)
    plt.colorbar()
    plt.contour(x, y, loss, colors='black', origin='lower', levels=levels)

    if weight_traj:
        # Plot all the weight points and highlight the teleported one.
        plt.plot(weight_traj[0], weight_traj[1], '-o', c='black')
        plt.plot(weight_traj[0][teleport_idx], weight_traj[1][teleport_idx], '-o', c='yellow')

        for wx, wy in zip(weight_traj[0], weight_traj[1]):
            idx = (wx - x).abs().argmin()
            idy = (wy - y).abs().argmin()
            loss_xy = loss[idx][idy]
            label = "{:.5f}".format(loss_xy)
            plt.annotate(label, (wx, wy), textcoords="offset points", xytext=(10, 10), ha='center')


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    from neuralteleportation.metrics import accuracy
    from torch.utils.data.dataloader import DataLoader
    from neuralteleportation.models.model_zoo.resnetcob import resnet18COB
    from neuralteleportation.training.experiment_setup import get_cifar10_datasets

    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    metric = TrainingMetrics(
        criterion=nn.CrossEntropyLoss(),
        metrics=[accuracy]
    )
    config = LandscapeConfig(
        lr=5e-4,
        epochs=10,
        batch_size=32,
        cob_range=1e-5,
        training_split=0.5,
        device=device
    )
    model = resnet18COB(num_classes=10)
    trainset, valset, testset = get_cifar10_datasets()
    trainset.data = trainset.data[:1000]  # For the example, don't use all the data.
    trainloader = DataLoader(trainset, batch_size=config.batch_size, drop_last=True)

    x = torch.linspace(-1, 1, 5)
    y = torch.linspace(-1, 1, 5)
    surface = torch.stack((x, y))

    model = NeuralTeleportationModel(model, input_shape=(config.batch_size, 3, 32, 32)).to(device)

    w_checkpoints, final_w = generate_teleportation_training(model, trainset, metric=metric, config=config)
    delta, eta = generate_random_2d_vector(final_w), generate_random_2d_vector(final_w)
    loss, _ = generate_contour_loss_values(model, (delta, eta), surface, trainset, metric, config)
    original_w = w_checkpoints[0]

    loss = np.array(loss)
    loss = np.resize(loss, (len(x), len(y)))

    teleport_idx = config.training_split[0] + 1 if config.training_split[1] != 0 else 0
    w_diff = [(w - final_w) for w in w_checkpoints]
    w_x_direction, w_y_direction = generate_weights_direction(original_w, w_diff)
    weight_traj = generate_weight_trajectory(w_diff, (w_x_direction, w_y_direction))

    plt.figure()
    plot_contours(x, y, loss, weight_traj, teleport_idx=teleport_idx)
    plt.show()
