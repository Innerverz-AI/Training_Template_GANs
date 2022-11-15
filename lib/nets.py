import torch
import torch.nn as nn

class AdaIN(nn.Module):
    def __init__(self, style_dim, num_features):
        super().__init__()
        self.norm = nn.InstanceNorm2d(num_features, affine=False)
        self.fc = nn.Linear(style_dim, num_features*2)

    def forward(self, x, s):
        h = self.fc(s)
        h = h.view(h.size(0), h.size(1), 1, 1)
        gamma, beta = torch.chunk(h, chunks=2, dim=1)
        return (1 + gamma) * self.norm(x) + beta

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
        norm_type='bn', act_type='lrelu', transpose=False):
        super(ConvBlock, self).__init__()

        # convolutional layer and upsampling
        if transpose:
            self.up = Interpolate(scale_factor=stride)
            self.conv = nn.Conv2d(input_dim, output_dim, kernel_size, stride=1, padding=padding)
        else:
            self.up = transpose
            self.conv = nn.Conv2d(input_dim, output_dim, kernel_size, stride, padding=padding)
        
        # normalization
        if norm_type == 'bn':
            self.norm = nn.BatchNorm2d(output_dim)
        elif norm_type == 'in':
            self.norm = nn.InstanceNorm2d(output_dim)
        elif norm_type == 'none':
            self.norm = None
        else:
            assert 0, f"Unsupported normalization: {norm_type}"
        
        # activation
        if act_type == 'relu':
            self.act = nn.ReLU()
        elif act_type == 'lrelu':
            self.act = nn.LeakyReLU(0.2)
        elif act_type == 'tanh':
            self.act = nn.Tanh()
        elif act_type == 'sig':
            self.act = nn.Sigmoid()
        elif act_type == 'none':
            self.act = None
        else:
            assert 0, f"Unsupported activation: {act_type}"


    def forward(self, x):
        if self.up:
            x = self.up(x)

        x = self.conv(x)

        if self.norm:
            x = self.norm(x)

        if self.act:
            x = self.act(x)
        return x


class ResBlock(nn.Module):
    def __init__(self, in_c, out_c, scale_factor=1, norm='in', act='lrelu'):
        super(ResBlock, self).__init__()

        self.norm1 = nn.InstanceNorm2d(out_c)
        self.norm2 = nn.InstanceNorm2d(out_c)
        self.activ = nn.LeakyReLU(0.2)
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
    def __init__(self, in_c, out_c, scale_factor=1, style_dim=512):
        super(AdaINResBlock, self).__init__()

        self.AdaIN1 = AdaIN(style_dim, in_c)
        self.AdaIN2 = AdaIN(style_dim, out_c)
        self.activ = nn.LeakyReLU(0.2)
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