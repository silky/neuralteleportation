import torch.nn as nn

from neuralteleportation.layers.activationlayers import ReLUCOB
from neuralteleportation.layers.mergelayers import Concat
from neuralteleportation.layers.neuralteleportationlayers import FlattenCOB
from neuralteleportation.layers.neuronlayers import Conv2dCOB, LinearCOB


class DenseNet(nn.Module):
    def __init__(self):
        super(DenseNet, self).__init__()
        self.conv1 = Conv2dCOB(in_channels=1, out_channels=3, kernel_size=3, padding=1)
        self.conv2 = Conv2dCOB(in_channels=3, out_channels=3, kernel_size=3, padding=1)
        self.conv3 = Conv2dCOB(in_channels=6, out_channels=3, kernel_size=3, padding=1)
        self.conv4 = Conv2dCOB(in_channels=3, out_channels=3, kernel_size=3, padding=1)
        self.relu1 = ReLUCOB()
        self.relu2 = ReLUCOB()
        self.relu3 = ReLUCOB()
        self.relu4 = ReLUCOB()
        self.concat1 = Concat()
        self.flatten = FlattenCOB()
        self.fc1 = LinearCOB(2352, 10)

    def forward(self, x):
        x1 = self.relu1(self.conv1(x))
        x2 = self.relu2(self.conv2(x1))

        # x2 += x1
        x2 = self.concat1(x1, x2)

        x3 = self.relu3(self.conv3(x2))
        x4 = self.conv4(x3)
        x = self.flatten(x4)
        x = self.relu4(self.fc1(x))

        return x


class DenseNet2(nn.Module):
    def __init__(self):
        super(DenseNet2, self).__init__()
        self.conv1 = Conv2dCOB(in_channels=1, out_channels=3, kernel_size=3, padding=1)
        self.conv2 = Conv2dCOB(in_channels=3, out_channels=3, kernel_size=3, padding=1)
        self.conv3 = Conv2dCOB(in_channels=3, out_channels=3, kernel_size=3, padding=1)
        self.conv4 = Conv2dCOB(in_channels=9, out_channels=1, kernel_size=3, padding=1)
        self.relu1 = ReLUCOB()
        self.relu2 = ReLUCOB()
        self.relu3 = ReLUCOB()
        # self.relu4 = ReLUCOB()
        self.concat1 = Concat()
        # self.flatten = FlattenCOB()
        # self.fc1 = LinearCOB(2352, 10)

    def forward(self, x):
        x1 = self.relu1(self.conv1(x))
        x2 = self.relu2(self.conv2(x1))

        x3 = self.relu3(self.conv3(x2))
        x3 = self.concat1(x1, x2, x3)
        x4 = self.conv4(x3)
        # x = self.flatten(x4)
        # x = self.relu4(self.fc1(x))

        return x4


class SplitConcatModel(nn.Module):
    def __init__(self):
        super(SplitConcatModel, self).__init__()
        self.conv1 = Conv2dCOB(in_channels=1, out_channels=3, kernel_size=3, padding=1)
        self.conv21 = Conv2dCOB(in_channels=3, out_channels=3, kernel_size=3, padding=1)
        self.conv22 = Conv2dCOB(in_channels=3, out_channels=3, kernel_size=3, padding=1)
        self.conv3 = Conv2dCOB(in_channels=6, out_channels=3, kernel_size=3, padding=1)
        self.relu1 = ReLUCOB()
        self.relu21 = ReLUCOB()
        self.relu22 = ReLUCOB()
        # self.relu3 = ReLUCOB()
        # self.relu4 = ReLUCOB()
        self.concat1 = Concat()
        # self.flatten = FlattenCOB()
        # self.fc1 = LinearCOB(2352, 10)

    def forward(self, x):
        x1 = self.relu1(self.conv1(x))
        x21 = self.relu21(self.conv21(x1))
        x22 = self.relu22(self.conv22(x1))

        x2 = self.concat1(x21, x22)
        x3 = self.conv3(x2)

        return x3

class DenseNet3(nn.Module):
    def __init__(self):
        super(DenseNet3, self).__init__()
        self.conv1 = Conv2dCOB(in_channels=1, out_channels=3, kernel_size=3, padding=1)
        self.conv11 = Conv2dCOB(in_channels=3, out_channels=3, kernel_size=3, padding=1)
        self.conv2 = Conv2dCOB(in_channels=3, out_channels=3, kernel_size=3, padding=1)
        self.conv3 = Conv2dCOB(in_channels=6, out_channels=3, kernel_size=3, padding=1)
        self.conv4 = Conv2dCOB(in_channels=3, out_channels=3, kernel_size=3, padding=1)
        self.relu1 = ReLUCOB()
        self.relu11 = ReLUCOB()
        self.relu2 = ReLUCOB()
        self.relu3 = ReLUCOB()
        self.relu4 = ReLUCOB()
        self.concat1 = Concat()
        self.flatten = FlattenCOB()
        self.fc1 = LinearCOB(2352, 10)

    def forward(self, x):
        x1 = self.relu1(self.conv1(x))
        x11 = self.relu11(self.conv11(x1))
        x2 = self.relu2(self.conv2(x1))

        # x2 += x1
        x2 = self.concat1(x11, x2)

        x3 = self.relu3(self.conv3(x2))
        x4 = self.conv4(x3)
        x = self.flatten(x4)
        x = self.relu4(self.fc1(x))

        return x


if __name__ == '__main__':
    from tests.model_test import test_teleport

    models = [DenseNet, DenseNet2, DenseNet3, SplitConcatModel]
    input_shape = (1, 1, 28, 28)

    for model in models:
        try:
            diff_avg = test_teleport(model(), input_shape)
            print("{} model passed with avg diff: {}".format(model, diff_avg))
        except Exception as e:
            print("Teleportation failed for model: {} with error {}".format(model, e))

    print("All tests are done")