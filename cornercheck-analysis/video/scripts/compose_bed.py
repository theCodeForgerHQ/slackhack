"""Original ambient bed for the CornerCheck demo (175s), composed in code.

License-clean by construction (no samples, no third-party audio). v2 character
(2026-06-10, Stephen: "a little more happy, too dark before"): D MAJOR warmth
instead of the minor drone, a sixth in the air chord, livelier shimmer, and a
sparse music-box pluck pattern on the D-major pentatonic that only plays in the
no-speech gaps. Still melody-light so it cannot fight the voiceover. Structure
unchanged: near-silent under the cold open, blooms at the title card and at each
beat boundary, warms under the close, resolves before the end card finishes.

Run: python3 scripts/compose_bed.py  ->  public/vo/music-bed.wav
"""

import wave
from pathlib import Path

import numpy as np

SR = 48000
DUR = 175.0
t = np.arange(int(SR * DUR)) / SR

# Beat boundaries where a small swell breathes between VO lines.
BOUNDARIES = [22.0, 25.0, 48.0, 72.0, 90.0, 107.0, 125.0, 140.0, 153.0, 163.0]
END_BLOOM = 171.8

rng = np.random.default_rng(20260610)  # deterministic render


def lfo(freq: float, phase: float = 0.0) -> np.ndarray:
    return 0.5 * (1.0 + np.sin(2 * np.pi * freq * t + phase))


def tone(freq: float, detune_hz: float = 0.0) -> np.ndarray:
    return np.sin(2 * np.pi * (freq + detune_hz) * t)


def envelope() -> np.ndarray:
    """Global dynamics: fade-in, low under speech, swells in gaps, out by 174.5s."""
    env = np.full_like(t, 0.55)  # base bed level (ducking happens in the mix too)
    env *= np.clip(t / 2.5, 0, 1)  # fade in
    env *= np.clip((174.5 - t) / 2.5, 0, 1)  # fade out before the video ends
    for b in BOUNDARIES:
        env += 0.25 * np.exp(-((t - b) ** 2) / (2 * 1.0**2))
    env += 0.30 * np.exp(-((t - END_BLOOM) ** 2) / (2 * 1.2**2))
    # Title card (22-25) holds the bloom rather than dipping between two swells.
    env += 0.18 * ((t > 22.2) & (t < 24.8)).astype(float)
    return np.clip(env, 0, 1.1)


def plucks() -> np.ndarray:
    """Sparse music-box plucks on the D-major pentatonic, gaps only.

    Each pluck is a sine with a fast exponential decay plus a quiet octave
    partial: bright, friendly, and short enough never to smear into speech."""
    penta = [587.33, 659.25, 739.99, 880.0, 987.77]  # D5 E5 F#5 A5 B5
    out = np.zeros_like(t)
    windows = [(22.2, 24.8), (171.6, 174.0)] + [(b - 0.4, b + 0.9) for b in BOUNDARIES[2:]]
    step = 0
    for start, end in windows:
        when = start + 0.1
        while when < end:
            f = penta[step % len(penta)] if step % 7 != 3 else penta[(step + 2) % len(penta)]
            step += 1
            i0 = int(when * SR)
            n = int(0.9 * SR)
            if i0 + n > len(t):
                break
            seg = np.arange(n) / SR
            decay = np.exp(-seg / 0.22)
            out[i0 : i0 + n] += (
                0.16
                * decay
                * (np.sin(2 * np.pi * f * seg) + 0.35 * np.sin(2 * np.pi * 2 * f * seg))
            )
            when += 0.42 if (step % 3) else 0.63  # lilting, not metronomic
    return out


def compose() -> np.ndarray:
    d2, a2 = 73.416, 110.0  # D2 and its fifth
    d4, fs4, a4, b4 = 293.66, 369.99, 440.0, 493.88  # D major add-6 air chord

    sub = 0.42 * tone(d2) + 0.42 * tone(d2, 0.22)  # slightly quicker shimmer than v1
    fifth = (0.36 * tone(a2) + 0.10 * tone(a2 * 3)) * lfo(0.07, 1.3)
    air = (
        0.15 * tone(d4, 0.24) * lfo(0.06, 0.0)
        + 0.14 * tone(fs4, -0.20) * lfo(0.075, 2.1)  # the major third = the smile
        + 0.11 * tone(a4, 0.15) * lfo(0.066, 4.2)
        + 0.09 * tone(b4, 0.18) * lfo(0.09, 1.0)  # added sixth = warm, hopeful
    )
    noise = rng.standard_normal(t.shape)
    kernel = np.ones(900) / 900.0  # crude lowpass via moving average
    breath = 0.08 * np.convolve(noise, kernel, mode="same")

    env = envelope()
    swell_only = np.clip(env - 0.55, 0, None) / 0.55  # extras ride the swells only
    mono = (0.36 * sub + 0.28 * fifth + air) * env
    mono += breath * swell_only * 0.45
    mono += plucks() * np.clip(env / 0.55, 0, 1)

    # Stereo width: right channel gets an 11ms delayed blend.
    delay = int(0.011 * SR)
    right = np.copy(mono)
    right[delay:] = 0.82 * mono[delay:] + 0.18 * mono[:-delay]
    stereo = np.stack([mono, right], axis=1)
    stereo /= np.max(np.abs(stereo)) * 1.25  # ~-2 dBFS headroom, mix gain set in Remotion
    return stereo


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "public" / "vo" / "music-bed.wav"
    data = (compose() * 32767).astype(np.int16)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f"wrote {out} ({DUR}s)")


if __name__ == "__main__":
    main()
