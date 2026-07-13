"""Word-aligned caption spans from the actual recorded audio, via whisper.cpp.

The SCRIPT stays the canonical caption text (whisper may mis-hear a word; the
locked script never does). Whisper supplies word TIMING only: canonical words are
mapped positionally onto whisper's word timeline, then grouped into the script's
sentences. Output: src/captions.json, beat-relative seconds.

Run: python3 scripts/gen_captions.py  (needs whisper-cli + models/ggml-base.en.bin)
"""

# ruff: noqa: E501  (the canonical script lines are long by nature)

import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "ggml-base.en.bin"

# beat id -> (audio source, seconds to subtract to make times beat-relative,
#             seconds to add because the audio starts later than the beat)
SOURCES: dict[str, tuple[Path, float, float]] = {
    # camera bookends: whisper the clip audio; clipStart shifts clip time -> beat time
    "beat0": (ROOT / "public/footage/camera-beat0.mp4", 2.0, 0.0),
    "beat10": (ROOT / "public/footage/camera-beat10.mp4", 1.0, 0.0),
    # voiceover beats: whisper the trimmed VO; voDelay shifts VO time -> beat time
    "beat2": (ROOT / "public/vo/beat2.wav", 0.0, 0.6),
    "beat3": (ROOT / "public/vo/beat3.wav", 0.0, 0.6),
    "beat4": (ROOT / "public/vo/beat4.wav", 0.0, 0.6),
    "beat5": (ROOT / "public/vo/beat5.wav", 0.0, 0.6),
    "beat6": (ROOT / "public/vo/beat6.wav", 0.0, 0.4),
    "beat7": (ROOT / "public/vo/beat7.wav", 0.0, 0.0),
    "beat8": (ROOT / "public/vo/beat8.wav", 0.0, 0.4),
    "beat9": (ROOT / "public/vo/beat9.wav", 0.0, 0.6),
}

SCRIPTS = {
    "beat0": "In 2017, fighter Tim Hague died after a knockout in a boxing match. His medical suspension had lapsed days earlier, and he fought as a late replacement. Nobody re-checked. The records existed. Nothing forced the check. So I built it, inside Slack, where fight operations already work.",
    "beat2": "Clear a whole lineup at once. Green: no recorded suspension matched. Red: blocked, with the reason cited underneath. And the yellow one says NEEDS PICK, because it refuses to guess who that fighter even is. Every verdict on this board just landed in a tamper-evident audit ledger.",
    "beat3": "The catch that matters. Blocked: an active indefinite suspension from the California commission, pending neurological clearance after a knockout. Source cited right there. Texas is a different commission, and that gap is what CornerCheck closes. At the bottom, a warning surfaced from the team's own Slack messages. And the footnote: identity confirmed by a calibrated statistical gate.",
    "beat4": "Two professional fighters are named Bruno Silva. Clearing the wrong one can be fatal, so it will not guess. It shows both, with weight class and record, and a human picks. The pick itself is written to the ledger.",
    "beat5": "Boxing verdicts get corroborated against a live record feed. That line is his actual professional record from the live source. The rule is one-way: live data can tighten a verdict. Nothing it says can ever loosen one.",
    "beat6": "Every card carries this button. Click it, and the Z3 theorem prover re-proves, right then, that an active suspension can never come out cleared, across every possible date. The second line is a deliberately broken version that must fail. No rubber stamps.",
    "beat7": "Every decision, hash-chained and append-only. Edit one past entry and verification names it. One click exports the whole trail to a Canvas you can hand to a promoter or a commission.",
    "beat8": "And it does not wait to be asked. A daily digest: windows about to lapse, windows just lapsed, new blocks. Deterministic triggers only. Quiet days send nothing.",
    "beat9": "All of it is live right now. Real numbers from the real database, and that proof button works for you too. Milliseconds.",
    "beat10": "CornerCheck is one cross-check, where fight teams already work, between a fighter and the worst day of someone's life. Thank you for watching.",
}


def whisper_words(audio: Path) -> list[tuple[str, float, float]]:
    """Return (word, start_s, end_s) merged from whisper.cpp token offsets."""
    with tempfile.TemporaryDirectory() as td:
        wav16 = Path(td) / "in16k.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(audio),
                "-ar",
                "16000",
                "-ac",
                "1",
                str(wav16),
            ],
            check=True,
        )
        out = Path(td) / "tr"
        subprocess.run(
            ["whisper-cli", "-m", str(MODEL), "-f", str(wav16), "-ojf", "-of", str(out), "-np"],
            check=True,
            capture_output=True,
        )
        data = json.loads((out.with_suffix(".json")).read_text())
    words: list[tuple[str, float, float]] = []
    for seg in data.get("transcription", []):
        for tok in seg.get("tokens", []):
            text = tok.get("text", "")
            if not text or text.startswith("[_"):
                continue
            t0 = tok["offsets"]["from"] / 1000.0
            t1 = tok["offsets"]["to"] / 1000.0
            if text.startswith(" ") or not words:
                words.append((text.strip(), t0, t1))
            else:  # subword continuation glues onto the previous word
                w, s, _ = words[-1]
                words[-1] = (w + text.strip(), s, t1)
    return [w for w in words if w[0]]


def main() -> None:
    result: dict[str, list[dict[str, float | str]]] = {}
    for beat, (audio, clip_shift, delay) in SOURCES.items():
        script = SCRIPTS[beat]
        canon = script.split()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script) if s.strip()]
        words = whisper_words(audio)
        if len(words) < 0.6 * len(canon):
            print(
                f"{beat}: whisper got {len(words)} words vs {len(canon)} canonical; SKIP (fallback timing)"
            )
            continue

        # Map each canonical word index onto the whisper timeline positionally.
        def at(
            i: int,
            words: list[tuple[str, float, float]] = words,
            n_canon: int = len(canon),
        ) -> tuple[float, float]:
            j = min(len(words) - 1, round(i * (len(words) - 1) / max(1, n_canon - 1)))
            _, s, e = words[j]
            return s, e

        spans = []
        ci = 0
        for sent in sentences:
            n = len(sent.split())
            s0, _ = at(ci)
            _, e1 = at(ci + n - 1)
            start = max(0.0, s0 - clip_shift + delay - 0.12)
            end = e1 - clip_shift + delay + 0.30
            spans.append({"text": sent, "from": round(start, 2), "to": round(end, 2)})
            ci += n
        # No overlaps after padding.
        for k in range(1, len(spans)):
            if spans[k]["from"] < spans[k - 1]["to"]:
                mid = (spans[k]["from"] + spans[k - 1]["to"]) / 2
                spans[k - 1]["to"] = round(mid, 2)
                spans[k]["from"] = round(mid, 2)
        result[beat] = spans
        print(
            f"{beat}: {len(words)} words -> {len(spans)} caption spans "
            f"({spans[0]['from']}s .. {spans[-1]['to']}s)"
        )
    out = ROOT / "src" / "captions.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
