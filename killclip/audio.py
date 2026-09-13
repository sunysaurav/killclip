"""Find the elimination sound by matching a reference sting against the spectrogram."""
import logging

import cv2
import numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks, stft

from .media import SR

log = logging.getLogger("killclip.audio")
N_FFT = 512
HOP = 160  # 10 ms per spectrogram column


def log_spec(y, fmin, fmax):
    f, _, Z = stft(y.astype(np.float32), fs=SR, nperseg=N_FFT, noverlap=N_FFT - HOP,
                   boundary=None, padded=False)
    band = (f >= fmin) & (f <= fmax)
    return np.log1p(1000.0 * np.abs(Z[band])).astype(np.float32)


def scores(y, ref, fmin, fmax):
    """Similarity (-1..1) of the reference sting starting at each 10 ms column."""
    S = log_spec(y, fmin, fmax)
    R = log_spec(ref, fmin, fmax)
    log.debug("spectrogram %dx%d, reference %dx%d (band %d-%d Hz)", *S.shape, *R.shape, fmin, fmax)
    if S.shape[1] < R.shape[1]:
        log.warning("audio shorter than the reference sting; no matches possible")
        return np.zeros(1, np.float32)
    return cv2.matchTemplate(S, R, cv2.TM_CCOEFF_NORMED)[0]


def peaks(sc, threshold, min_gap):
    """[(time, score)] of local maxima above threshold, at least min_gap seconds apart."""
    idx, props = find_peaks(sc, height=threshold, distance=max(1, int(min_gap * SR / HOP)))
    return [(i * HOP / SR, float(h)) for i, h in zip(idx, props["peak_heights"])]


def cut_ref(y, start, dur):
    return y[int(start * SR): int((start + dur) * SR)]


def save_wav(path, y):
    wavfile.write(path, SR, y.astype(np.float32))


def load_wav(path):
    sr, y = wavfile.read(path)
    if sr != SR:
        raise ValueError(f"{path}: expected {SR} Hz, got {sr}")
    if y.dtype != np.float32:
        y = y.astype(np.float32) / np.iinfo(y.dtype).max
    if y.ndim > 1:
        y = y.mean(axis=1)
    return y
