"""PANNs MobileNetV1: an AudioSet sound tagger, used to hear gunfire, explosions, crashes and
sirens in a recording that has no kill feed.

The network is Kong et al.'s MobileNetV1 from "PANNs: Large-Scale Pretrained Audio Neural Networks
for Audio Pattern Recognition" (2020), adapted from qiuqiangkong/audioset_tagging_cnn
(pytorch/models.py), which is MIT licensed:

    Copyright (c) 2018-2020 Qiuqiang Kong. Permission is hereby granted, free of charge, to any
    person obtaining a copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT
    WARRANTY OF ANY KIND.

Two things differ from upstream. The front end is torch.stft plus the mel filterbank the checkpoint
already carries, so neither torchlibrosa nor librosa is needed, and the training-only parts
(SpecAugment, mixup, dropout) are gone. Layer names are upstream's, so the published checkpoint
loads unchanged. The weights are Zenodo record 3987831 (CC BY 4.0), fetched on first use.

torch is an optional dependency: install with `pip install killclip[sound]`.
"""
import csv
import hashlib
import logging
import os
import urllib.request

import numpy as np

from .paths import HOME

log = logging.getLogger("killclip.panns")

SAMPLE_RATE = 32000          # what the network was trained at; none of these are free parameters
N_FFT, HOP, MEL_BINS, CLASSES = 1024, 320, 64, 527
FMIN, FMAX = 50, 14000
WEIGHTS_URL = "https://zenodo.org/records/3987831/files/MobileNetV1_mAP%3D0.389.pth?download=1"
WEIGHTS_MD5 = "a419303e1c88aa1b9d2ac3811563d371"
LABELS_URL = "http://storage.googleapis.com/us_audioset/youtube_corpus/v1/csv/class_labels_indices.csv"

_model = None
_labels = None


def weights_path():
    return os.path.join(HOME, "models", "panns_mobilenetv1.pth")


def labels_path():
    return os.path.join(HOME, "calib", "audio", "audioset_labels.csv")


def _fetch(url, dest, md5=None):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    log.info("fetching %s", os.path.basename(dest))
    with urllib.request.urlopen(url) as r:
        data = r.read()
    if md5 and hashlib.md5(data, usedforsecurity=False).hexdigest() != md5:
        raise RuntimeError(f"checksum mismatch for {dest}")
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def labels():
    """The 527 AudioSet class names, in the order the network outputs them."""
    global _labels
    if _labels is None:
        p = labels_path()
        if not os.path.exists(p):
            _fetch(LABELS_URL, p)
        with open(p) as f:
            _labels = [row["display_name"] for row in csv.DictReader(f)]
    return _labels


def _network():
    import torch
    import torch.nn as nn

    def conv_bn(inp, oup, stride):
        return nn.Sequential(nn.Conv2d(inp, oup, 3, 1, 1, bias=False), nn.AvgPool2d(stride),
                             nn.BatchNorm2d(oup), nn.ReLU(inplace=True))

    def conv_dw(inp, oup, stride):
        return nn.Sequential(
            nn.Conv2d(inp, inp, 3, 1, 1, groups=inp, bias=False), nn.AvgPool2d(stride),
            nn.BatchNorm2d(inp), nn.ReLU(inplace=True),
            nn.Conv2d(inp, oup, 1, 1, 0, bias=False), nn.BatchNorm2d(oup), nn.ReLU(inplace=True))

    class MobileNetV1(nn.Module):
        def __init__(self):
            super().__init__()
            self.bn0 = nn.BatchNorm2d(MEL_BINS)
            self.features = nn.Sequential(
                conv_bn(1, 32, 2), conv_dw(32, 64, 1), conv_dw(64, 128, 2), conv_dw(128, 128, 1),
                conv_dw(128, 256, 2), conv_dw(256, 256, 1), conv_dw(256, 512, 2),
                *[conv_dw(512, 512, 1) for _ in range(5)],
                conv_dw(512, 1024, 2), conv_dw(1024, 1024, 1))
            self.fc1 = nn.Linear(1024, 1024, bias=True)
            self.fc_audioset = nn.Linear(1024, CLASSES, bias=True)
            self.register_buffer("window", torch.hann_window(N_FFT))
            self.register_buffer("melW", torch.zeros(N_FFT // 2 + 1, MEL_BINS))

        def forward(self, x):
            # torchlibrosa's Spectrogram + LogmelFilterBank, as torch.stft + the checkpoint's melW
            spec = torch.stft(x, N_FFT, hop_length=HOP, win_length=N_FFT, window=self.window,
                              center=True, pad_mode="reflect", return_complex=True)
            power = (spec.real ** 2 + spec.imag ** 2).transpose(1, 2)        # (B, frames, freq)
            mel = torch.matmul(power, self.melW)
            x = 10.0 * torch.log10(torch.clamp(mel, min=1e-10)).unsqueeze(1)  # (B, 1, frames, mel)
            x = self.bn0(x.transpose(1, 3)).transpose(1, 3)
            x = self.features(x)
            x = torch.mean(x, dim=3)
            x = torch.max(x, dim=2)[0] + torch.mean(x, dim=2)
            return torch.sigmoid(self.fc_audioset(torch.relu_(self.fc1(x))))

    return MobileNetV1()


def available():
    try:
        import torch  # noqa: F401
    except ImportError:
        return False
    return True


def load():
    """The network with its weights, cached. Downloads them on first use (23 MB)."""
    global _model
    if _model is not None:
        return _model
    try:
        import torch
    except ImportError:
        raise SystemExit("sound detection needs PyTorch: pip install 'killclip[sound]'")
    p = weights_path()
    if not os.path.exists(p):
        _fetch(WEIGHTS_URL, p, WEIGHTS_MD5)
    state = torch.load(p, map_location="cpu", weights_only=True)
    state = state.get("model", state)
    model = _network()
    # The checkpoint's STFT is a convolution with the window baked in; torch.stft computes the
    # same thing, so only the mel filterbank is kept from it.
    state = {k: v for k, v in state.items() if not k.startswith("spectrogram_extractor.")}
    state["melW"] = state.pop("logmel_extractor.melW")
    state["window"] = model.window
    model.load_state_dict(state)
    model.eval()
    _model = model
    log.info("sound tagger loaded (PANNs MobileNetV1)")
    return model


def tag(windows, batch=64):
    """(n, samples) float32 audio at 32 kHz -> (n, 527) class probabilities."""
    import torch

    model = load()
    out = []
    with torch.inference_mode():
        for i in range(0, len(windows), batch):
            x = torch.from_numpy(np.ascontiguousarray(windows[i:i + batch], dtype=np.float32))
            out.append(model(x).float().numpy())
    return np.concatenate(out) if out else np.zeros((0, CLASSES), np.float32)
