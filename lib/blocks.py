import torch
import torch.nn as nn

from lib.utils import set_norm_layer, set_activate_layer, AdaIN

class Interpolate(nn.Module):
    def __init__(self, scale_factor, mode="bilinear"):
        super(Interpolate, self).__init__()
        self.interp = nn.functional.interpolate
        self.scale_factor = scale_factor
        self.mode = mode
        
    def forward(self, x):
        x = self.interp(x, scale_factor=self.scale_factor, mode=self.mode, align_corners=False)
        return x

#------------------------------------------------------------------------------------------
# ConvBlock
#   1. Upsample / Conv(padding)
#       - padding options : 'zeros'(default), 'reflect', 'replicate' or 'circular'
#       - if you choose upsample option, you have to set stride==1
#   2. Norm
#       - Norm options : 'bn', 'in', 'none'
#   3. activation
#       - activation options : 'relu', 'tanh', 'sig', 'none'
#------------------------------------------------------------------------------------------
class ConvBlock(nn.Module):
    def __init__(self, input_dim ,output_dim, kernel_size=3, stride=2, padding=1, \
        norm_type='bn', activation_type='relu', transpose=False):
        super(ConvBlock, self).__init__()

        if transpose:
            self.up = Interpolate(scale_factor=stride)
            self.conv = nn.Conv2d(input_dim, output_dim, kernel_size, stride=1, padding=padding)
        else:
            self.up = transpose
            self.conv = nn.Conv2d(input_dim, output_dim, kernel_size, stride, padding=padding)
        
        self.norm = set_norm_layer(norm_type, output_dim) # bn, in, none
        self.activation = set_activate_layer(activation_type) # relu, lrelu, tanh, sig, none

    def forward(self, x):
        if self.up:
            x = self.up(x)

        x = self.conv(x)

        if self.norm:
            x = self.norm(x)

        if self.activation:
            x = self.activation(x)
        return x


class ResBlock(nn.Module):
    def __init__(self, in_c, out_c, scale_factor=1, norm='in', activation='lrelu'):
        super(ResBlock, self).__init__()

        self.norm1 = set_norm_layer(norm, out_c)
        self.norm2 = set_norm_layer(norm, out_c)
        self.activ = set_activate_layer(activation)
        self.conv1 = nn.Conv2d(in_channels=in_c, out_channels=out_c, kernel_size=3, stride=1, padding=1, bias=False)
        self.conv2 = nn.Conv2d(in_channels=out_c, out_channels=out_c, kernel_size=3, stride=1, padding=1, bias=False)
        self.conv1x1 = nn.Conv2d(in_channels=in_c, out_channels=out_c, kernel_size=1, stride=1, padding=0, bias=False)
        self.resize = Interpolate(scale_factor=scale_factor)

    def forward(self, feat):
        feat1 = self.norm1(feat)
        feat1 = self.activ(feat1)
        feat1 = self.conv1(feat1)
        feat1 = self.resize(feat1)
        feat1 = self.norm2(feat1)
        feat1 = self.activ(feat1)
        feat1 = self.conv2(feat1)

        feat2 = self.conv1x1(feat)
        feat2 = self.resize(feat2)

        return feat1 + feat2


class AdaINResBlock(nn.Module):
    def __init__(self, in_c, out_c, scale_factor=1, activation='lrelu', styledim=512):
        super(AdaINResBlock, self).__init__()

        self.AdaIN1 = AdaIN(styledim, in_c)
        self.AdaIN2 = AdaIN(styledim, out_c)
        self.activ = set_activate_layer(activation)
        self.conv1 = nn.Conv2d(in_channels=in_c, out_channels=out_c, kernel_size=3, stride=1, padding=1, bias=False)
        self.conv2 = nn.Conv2d(in_channels=out_c, out_channels=out_c, kernel_size=3, stride=1, padding=1, bias=False)
        self.conv1x1 = nn.Conv2d(in_channels=in_c, out_channels=out_c, kernel_size=1, stride=1, padding=0, bias=False)
        self.resize = Interpolate(scale_factor=scale_factor)

    def forward(self, feat, v_sid):
        feat1 = self.AdaIN1(feat, v_sid)
        feat1 = self.activ(feat1)
        feat1 = self.conv1(feat1)
        feat1 = self.resize(feat1)
        feat1 = self.AdaIN2(feat1, v_sid)
        feat1 = self.activ(feat1)
        feat1 = self.conv2(feat1)

        # skip connction
        feat2 = self.conv1x1(feat) # chnnel dim
        feat2 = self.resize(feat2) # size 

        return feat1 + feat2