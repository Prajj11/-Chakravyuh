"""Bounded signal diagnostics. These measurements do not identify deepfakes."""

import json
import math
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import cv2
import imagehash
import numpy as np
from PIL import Image


def inspect_file(path: Path, mime: str) -> dict[str, float]:
    if mime == "audio/wav":
        with wave.open(str(path), "rb") as stream:
            frames, rate = stream.getnframes(), stream.getframerate()
            channels, sample_width = stream.getnchannels(), stream.getsampwidth()
            if sample_width != 2:
                raise ValueError("Signal diagnostics currently require 16-bit PCM")
            samples = np.frombuffer(stream.readframes(min(frames, rate * 60)), dtype="<i2")
        if not len(samples) or not rate:
            raise ValueError("Empty audio")
        scaled = samples.astype(np.float64) / 32768
        return {
            "duration_seconds": frames / rate,
            "sample_rate_hz": float(rate),
            "channels": float(channels),
            "analyzed_seconds": len(samples) / channels / rate,
            "rms_amplitude": float(np.sqrt(np.mean(scaled**2))),
            "clipped_sample_ratio": float(np.mean(np.abs(scaled) >= 0.999)),
        }
    capture = cv2.VideoCapture(str(path))
    try:
        count, fps = capture.get(cv2.CAP_PROP_FRAME_COUNT), capture.get(cv2.CAP_PROP_FPS)
        width, height = (
            capture.get(cv2.CAP_PROP_FRAME_WIDTH),
            capture.get(cv2.CAP_PROP_FRAME_HEIGHT),
        )
        if not all(math.isfinite(v) and v > 0 for v in (count, fps, width, height)):
            raise ValueError("Invalid video metadata")
        if width * height > 24_000_000 or count / fps > 3600:
            raise ValueError("Video exceeds pixel or one-hour duration limit")
        hashes = []
        for frame in np.linspace(0, count - 1, min(int(count), 12)).astype(int):
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame))
            ok, decoded = capture.read()
            if not ok:
                continue
            rgb = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)
            hashes.append(str(imagehash.phash(Image.fromarray(rgb))))
        if not hashes:
            raise ValueError("Video has no decodable frames")
        return {
            "duration_seconds": count / fps,
            "frame_rate_fps": fps,
            "width": width,
            "height": height,
            "sampled_frames": float(len(hashes)),
            "distinct_sampled_phashes": float(len(set(hashes))),
        }
    finally:
        capture.release()


def inspect_bytes(data: bytes, mime: str) -> dict[str, float]:
    if len(data) > 25 * 1024 * 1024:
        raise ValueError("Media exceeds 25 MiB")
    with tempfile.TemporaryDirectory(prefix="chakravyuh-av-") as directory:
        path = Path(directory) / ("input.wav" if mime == "audio/wav" else "input.mp4")
        path.write_bytes(data)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "app.media_forensics.av", str(path), mime],
                capture_output=True,
                timeout=25,
                check=True,
            )
            return json.loads(result.stdout)
        except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
            raise ValueError("Media decoding failed or exceeded 25-second deadline") from exc


if __name__ == "__main__":
    print(json.dumps(inspect_file(Path(sys.argv[1]), sys.argv[2]), allow_nan=False))
