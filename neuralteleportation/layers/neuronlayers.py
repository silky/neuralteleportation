import torch.nn as nn
from neuralteleportation.layers.layers_v3 import NeuronLayerMixin
import torch

from neuralteleportation.utils import get_random_cob
import numpy as np


class LinearCOB(nn.Linear, NeuronLayerMixin):

    def apply_cob(self, prev_cob, next_cob):

        if len(prev_cob) != self.in_features:  # if previous layer is Conv2D
            hw = self.in_features // len(prev_cob)  # size of feature maps
            cob = []
            for i, c in enumerate(prev_cob):
                cob.extend(np.repeat(c, repeats=hw).tolist())
            prev_cob = np.array(cob)

        w = torch.tensor(next_cob[..., None] / prev_cob[None, ...], dtype=torch.float32)
        self.weight = nn.Parameter(self.weight * w, requires_grad=True)

        if self.bias is not None:
            self.bias = torch.nn.Parameter(self.bias * torch.tensor(next_cob, dtype=torch.float32), requires_grad=True)

    def get_cob(self, basis_range=10):
        """
        Returns:
            cob for the output neurons
        """
        return get_random_cob(range=basis_range, size=self.out_features)

    def get_input_cob(self):
        return np.ones(shape=self.in_features)

    def get_output_cob(self):
        return np.ones(shape=self.out_features)


class Conv2dCOB(nn.Conv2d, NeuronLayerMixin):

    def apply_cob(self, prev_cob, next_cob):
        shape = self.weight.shape
        for i in range(shape[0]):
            if self.bias is not None:
                self.bias[i] *= next_cob[i]
            for j in range(shape[1]):
                self.weight[i, j] *= next_cob[i] / prev_cob[j]

    def get_cob(self, basis_range=10):
        """
        Returns:
            cob for the output feature maps.
        """
        return get_random_cob(range=basis_range, size=self.out_channels)

    def get_input_cob(self):
        return np.ones(shape=self.in_channels)

    def get_output_cob(self):
        return np.ones(shape=self.out_channels)