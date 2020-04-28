import torch.nn as nn

from neuralteleportation.layers.activationlayers import ReLUCOB
from neuralteleportation.layers.mergelayers import Concat
from neuralteleportation.layers.neuralteleportationlayers import BatchNorm2dCOB
from neuralteleportation.layers.neuronlayers import Conv2dCOB, ConvTranspose2dCOB
from neuralteleportation.layers.poolinglayers import MaxPool2dCOB, UpsampleCOB


class UNet(nn.Module):
    '''
    Architecture based on U-Net: Convolutional Networks for Biomedical Image Segmentation
    Link - https://arxiv.org/abs/1505.04597

    Parameters:
    num_classes (int) - Number of output classes required (default 19 for KITTI dataset)
    bilinear (bool) - Whether to use bilinear interpolation or transposed
    convolutions for upsampling.
    '''

    def __init__(self, input_channels: int, output_channels: int, nb_feature_maps: int = 32, bilinear: bool = False):
        super().__init__()
        self.layer1 = DoubleConv(input_channels, nb_feature_maps // 2)
        self.layer2 = Down(nb_feature_maps // 2, nb_feature_maps)
        self.layer3 = Down(nb_feature_maps, nb_feature_maps * 2)
        self.layer4 = Down(nb_feature_maps * 2, nb_feature_maps * 4)
        self.layer5 = Down(nb_feature_maps * 4, nb_feature_maps * 8)
        self.layer6 = Down(nb_feature_maps * 8, nb_feature_maps * 16)

        self.layer7 = Up(nb_feature_maps * 16, nb_feature_maps * 8, bilinear=bilinear)
        self.layer8 = Up(nb_feature_maps * 8, nb_feature_maps * 4, bilinear=bilinear)
        self.layer9 = Up(nb_feature_maps * 4, nb_feature_maps * 2, bilinear=bilinear)
        self.layer10 = Up(nb_feature_maps * 2, nb_feature_maps, bilinear=bilinear)
        self.layer11 = Up(nb_feature_maps, nb_feature_maps // 2, bilinear=bilinear)

        self.layer12 = Conv2dCOB(nb_feature_maps // 2, output_channels, kernel_size=1)

    def forward(self, x):
        x1 = self.layer1(x)
        x2 = self.layer2(x1)
        x3 = self.layer3(x2)
        x4 = self.layer4(x3)
        x5 = self.layer5(x4)
        x6 = self.layer6(x5)

        out = self.layer7(x6, x5)
        out = self.layer8(out, x4)
        out = self.layer9(out, x3)
        out = self.layer10(out, x2)
        out = self.layer11(out, x1)

        return self.layer12(out)


class DoubleConv(nn.Module):
    """
    Double Convolution and BN and ReLU
    (3x3 conv -> BN -> ReLU) ** 2
    """

    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.net = nn.Sequential(
            Conv2dCOB(in_ch, out_ch, kernel_size=3, padding=1),
            BatchNorm2dCOB(out_ch),
            ReLUCOB(inplace=False),
            Conv2dCOB(out_ch, out_ch, kernel_size=3, padding=1),
            BatchNorm2dCOB(out_ch),
            ReLUCOB(inplace=False),
        )

    def forward(self, x):
        return self.net(x)


class Down(nn.Module):
    """
    Combination of MaxPool2d and DoubleConv in series
    """

    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.net = nn.Sequential(
            MaxPool2dCOB(kernel_size=2, stride=2),
            DoubleConv(in_ch, out_ch)
        )

    def forward(self, x):
        return self.net(x)


class Up(nn.Module):
    """
    Upsampling (by either bilinear interpolation or transpose convolutions)
    followed by concatenation of feature map from contracting path,
    followed by double 3x3 convolution.
    """

    def __init__(self, in_ch, out_ch, bilinear=False):
        super().__init__()
        self.upsample = None
        if bilinear:
            self.upsample = UpsampleCOB(scale_factor=2, mode='bilinear', align_corners=True)
        else:
            self.upsample = ConvTranspose2dCOB(in_ch, in_ch // 2, kernel_size=2, stride=2)

        self.conv = DoubleConv(in_ch, out_ch)
        self.cat = Concat()

    def forward(self, x1, x2):
        x1 = self.upsample(x1)

        # Pad x1 to the size of x2
        diff_h = x2.shape[2] - x1.shape[2]
        diff_w = x2.shape[3] - x1.shape[3]

        # x1 = F.pad(x1, [diff_w // 2, diff_w - diff_w // 2, diff_h // 2, diff_h - diff_h // 2])

        # Concatenate along the channels axis
        x = self.cat(x2, x1, dim=1)

        return self.conv(x)


if __name__ == '__main__':
    from torchsummary import summary
    from tests.model_test import test_teleport

    model = UNet(input_channels=1, output_channels=4, bilinear=False)

    # summary(model, (1, 256, 256), device='cpu')

    test_teleport(model, (1, 1, 256, 256))


