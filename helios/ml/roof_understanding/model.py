"""Compact shared-encoder U-Net baseline with two RID2 label heads."""

from __future__ import annotations


def build_model(base_channels: int = 32):
    import torch
    from torch import nn

    class ConvBlock(nn.Module):
        def __init__(self, in_channels: int, out_channels: int) -> None:
            super().__init__()
            self.layers = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
            )

        def forward(self, inputs):
            return self.layers(inputs)

    class RoofUnderstandingUNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            b = base_channels
            self.enc1 = ConvBlock(3, b)
            self.enc2 = ConvBlock(b, b * 2)
            self.enc3 = ConvBlock(b * 2, b * 4)
            self.bottleneck = ConvBlock(b * 4, b * 8)
            self.pool = nn.MaxPool2d(2)
            self.up3 = nn.ConvTranspose2d(b * 8, b * 4, 2, stride=2)
            self.dec3 = ConvBlock(b * 8, b * 4)
            self.up2 = nn.ConvTranspose2d(b * 4, b * 2, 2, stride=2)
            self.dec2 = ConvBlock(b * 4, b * 2)
            self.up1 = nn.ConvTranspose2d(b * 2, b, 2, stride=2)
            self.dec1 = ConvBlock(b * 2, b)
            self.segment_head = nn.Conv2d(b, 6, 1)
            self.superstructure_head = nn.Conv2d(b, 6, 1)

        def forward(self, inputs):
            e1 = self.enc1(inputs)
            e2 = self.enc2(self.pool(e1))
            e3 = self.enc3(self.pool(e2))
            center = self.bottleneck(self.pool(e3))
            d3 = self.dec3(torch.cat((self.up3(center), e3), dim=1))
            d2 = self.dec2(torch.cat((self.up2(d3), e2), dim=1))
            d1 = self.dec1(torch.cat((self.up1(d2), e1), dim=1))
            return {
                "segment_logits": self.segment_head(d1),
                "superstructure_logits": self.superstructure_head(d1),
            }

    return RoofUnderstandingUNet()
