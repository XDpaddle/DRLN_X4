import math
import paddle
import paddle.nn as nn
#import param_init as init
import paddle.nn.functional as F
import os,sys
sys.path.append(os.getcwd()+'/')
def init_weights(named_children):
    pass
   

class MeanShift(nn.Layer):
    def __init__(self, mean_rgb, sub):
        super(MeanShift, self).__init__()

        sign = -1 if sub else 1
        r = mean_rgb[0] * sign
        g = mean_rgb[1] * sign
        b = mean_rgb[2] * sign

        self.shifter = nn.Conv2D(3, 3, 1, 1, 0) #3 is size of output, 3 is size of input, 1 is kernel 1 is padding, 0 is group 
        self.shifter.weight.data = paddle.reshape(paddle.eye(3),[3, 3, 1, 1]) # view(3,3,1,1) convert a shape into (3,3,1,1) eye(3) is a 3x3 matrix and diagonal is 1.
        self.shifter.bias.data   = paddle.to_tensor([r, g, b])
        #in_channels, out_channels,ksize=3, stride=1, pad=1
        # Freeze the mean shift layer
        for params,v in self.shifter.named_parameters():
            v.stop_gradient = True

    def forward(self, x):
        x = self.shifter(x)
        return x


class BasicBlock(nn.Layer):
    def __init__(self,
                 in_channels, out_channels,
                 ksize=3, stride=1, pad=1, dilation=1):
        super(BasicBlock, self).__init__()

        self.body = nn.Sequential(
            nn.Conv2D(in_channels, out_channels, ksize, stride, pad, dilation),
            nn.ReLU()
        )



    def forward(self, x):
        out = self.body(x)
        return out


class BasicBlockSig(nn.Layer):
    def __init__(self,
                 in_channels, out_channels,
                 ksize=3, stride=1, pad=1):
        super(BasicBlockSig, self).__init__()

        self.body = nn.Sequential(
            nn.Conv2D(in_channels, out_channels, ksize, stride, pad),
            nn.Sigmoid()
        )


    def forward(self, x):
        out = self.body(x)
        return out


class ResidualBlock(nn.Layer):
    def __init__(self, 
                 in_channels, out_channels):
        super(ResidualBlock, self).__init__()

        self.body = nn.Sequential(
            nn.Conv2D(in_channels, out_channels, 3, 1, 1),
            nn.ReLU(),
            nn.Conv2D(out_channels, out_channels, 3, 1, 1),
        )

        init_weights(self.named_children)
        
    def forward(self, x):
        out = self.body(x)
        out = F.relu(out + x)
        return out


class EResidualBlock(nn.Layer):
    def __init__(self, 
                 in_channels, out_channels,
                 group=1):
        super(EResidualBlock, self).__init__()

        self.body = nn.Sequential(
            nn.Conv2D(in_channels, out_channels, 3, 1, 1, groups=group),
            nn.ReLU(),
            nn.Conv2D(out_channels, out_channels, 3, 1, 1, groups=group),
            nn.ReLU(),
            nn.Conv2D(out_channels, out_channels, 1, 1, 0),
        )

        init_weights(self.named_children)
        
    def forward(self, x):
        out = self.body(x)
        out = F.relu(out + x)
        return out


class UpsampleBlock(nn.Layer):
    def __init__(self, 
                 n_channels, scale, multi_scale, 
                 group=1):
        super(UpsampleBlock, self).__init__()

        if multi_scale:
            self.up2 = _UpsampleBlock(n_channels, scale=2, group=group)
            self.up3 = _UpsampleBlock(n_channels, scale=3, group=group)
            self.up4 = _UpsampleBlock(n_channels, scale=4, group=group)
        else:
            self.up =  _UpsampleBlock(n_channels, scale=scale, group=group)

        self.multi_scale = multi_scale

    def forward(self, x, scale):
        if self.multi_scale:
            if scale == 2:
                return self.up2(x)
            elif scale == 3:
                return self.up3(x)
            elif scale == 4:
                return self.up4(x)
        else:
            return self.up(x)


class _UpsampleBlock(nn.Layer):
    def __init__(self, 
				 n_channels, scale, 
				 group=1):
        super(_UpsampleBlock, self).__init__()

        named_children = []
        if scale == 2 or scale == 4 or scale == 8:
            for _ in range(int(math.log(scale, 2))):
                #modules += [nn.Conv2d(n_channels, 4*n_channels, 3, 1, 1, groups=group), nn.ReLU(inplace=True)]
                named_children += [nn.Conv2D(n_channels, 4*n_channels, 3, 1, 1, groups=group)]
                named_children += [nn.PixelShuffle(2)]
        elif scale == 3:
            #modules += [nn.Conv2d(n_channels, 9*n_channels, 3, 1, 1, groups=group), nn.ReLU(inplace=True)]
            named_children += [nn.Conv2D(n_channels, 9*n_channels, 3, 1, 1, groups=group)]
            named_children += [nn.PixelShuffle(3)]

        self.body = nn.Sequential(*named_children)
        init_weights(self.named_children)
        
    def forward(self, x):
        out = self.body(x)
        return out