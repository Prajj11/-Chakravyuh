import wave
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.media_forensics.av import inspect_bytes


def test_pcm_signal_diagnostics(tmp_path: Path) -> None:
    path = tmp_path / "test.wav"
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(np.full(8000, 16384, dtype="<i2").tobytes())
    result = inspect_bytes(path.read_bytes(), "audio/wav")
    assert result["duration_seconds"] == 1
    assert result["rms_amplitude"] == 0.5
    assert result["clipped_sample_ratio"] == 0


def test_video_sample_is_bounded(tmp_path: Path) -> None:
    path = tmp_path / "test.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 64))
    assert writer.isOpened()
    for _ in range(20):
        writer.write(np.zeros((64, 64, 3), dtype=np.uint8))
    writer.release()
    result = inspect_bytes(path.read_bytes(), "video/mp4")
    assert result["sampled_frames"] == 12
    assert result["duration_seconds"] == 2
    assert result["distinct_sampled_phashes"] == 1


def test_corrupt_video_rejected() -> None:
    with pytest.raises(ValueError):
        inspect_bytes(b"invalid", "video/mp4")
