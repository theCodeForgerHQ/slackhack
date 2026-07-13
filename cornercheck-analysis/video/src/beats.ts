// Beat timeline for the CornerCheck demo, mirrors docs/demo-script.md v2.1 exactly.
// All times in seconds at 30 fps. STRICT ceiling 3:00; final cut 2:55.
// clipStart values come from ffmpeg scene/speech detection on the recorded takes
// (2026-06-10): trim the still head so the action lands inside the slot.

export const FPS = 30;

export type Beat = {
  id: string;
  title: string;
  from: number; // seconds, absolute timeline
  to: number; // seconds, absolute timeline
  mode: "camera" | "voiceover" | "card";
  footage?: string; // file inside public/footage/
  clipStart?: number; // seconds into the source clip to start from
  vo?: string; // file inside public/vo/ (silence-trimmed, -16 LUFS)
  voDelay?: number; // seconds after beat start before the VO begins (default 0.6)
  script: string;
};

export const BEATS: Beat[] = [
  {
    id: "beat0",
    title: "Cold open",
    from: 0,
    to: 22,
    mode: "camera",
    footage: "camera-beat0.mp4",
    clipStart: 2.0, // speech starts 3.04s into the take
    script:
      "In 2017, fighter Tim Hague died after a knockout in a boxing match. His medical suspension had lapsed days earlier, and he fought as a late replacement. Nobody re-checked. The records existed. Nothing forced the check. So I built it, inside Slack, where fight operations already work.",
  },
  {
    id: "beat1",
    title: "Title card",
    from: 22,
    to: 25,
    mode: "card",
    script: "",
  },
  {
    id: "beat2",
    title: "The whole card, at once",
    from: 25,
    to: 48,
    mode: "voiceover",
    footage: "beat2.mp4",
    clipStart: 6.0, // board lands ~6-8s; window reaches the final blocker scroll (29.3s)
    vo: "beat2.wav",
    script:
      "Clear a whole lineup at once. Green: no recorded suspension matched. Red: blocked, with the reason cited underneath. And the yellow one says NEEDS PICK, because it refuses to guess who that fighter even is. Every verdict on this board just landed in a tamper-evident audit ledger.",
  },
  {
    id: "beat3",
    title: "The cross-jurisdiction catch",
    from: 48,
    to: 72,
    mode: "voiceover",
    footage: "beat3.mp4",
    clipStart: 0, // retake is 20.8s for a 24s slot; the final card frame holds
    vo: "beat3.wav",
    script:
      "The catch that matters. Blocked: an active indefinite suspension from the California commission, pending neurological clearance after a knockout. Source cited right there. Texas is a different commission, and that gap is what CornerCheck closes. At the bottom, a warning surfaced from the team's own Slack messages. And the footnote: identity confirmed by a calibrated statistical gate.",
  },
  {
    id: "beat4",
    title: "Fail closed on identity",
    from: 72,
    to: 90,
    mode: "voiceover",
    footage: "beat4.mp4",
    clipStart: 2.5,
    vo: "beat4.wav",
    script:
      "Two professional fighters are named Bruno Silva. Clearing the wrong one can be fatal, so it will not guess. It shows both, with weight class and record, and a human picks. The pick itself is written to the ledger.",
  },
  {
    id: "beat5",
    title: "A second source that can only tighten",
    from: 90,
    to: 107,
    mode: "voiceover",
    footage: "beat5.mp4",
    clipStart: 4.0, // card lands ~8s into the slot, right as the VO points at the live line

    vo: "beat5.wav",
    script:
      "Boxing verdicts get corroborated against a live record feed. That line is his actual professional record from the live source. The rule is one-way: live data can tighten a verdict. Nothing it says can ever loosen one.",
  },
  {
    id: "beat6",
    title: "The proof, in the product",
    from: 107,
    to: 125,
    mode: "voiceover",
    footage: "beat6.mp4",
    clipStart: 3.5, // proof renders ~6.1s; window ends before the 21.9s scroll-away
    vo: "beat6.wav",
    voDelay: 0.4,
    script:
      "Every card carries this button. Click it, and the Z3 theorem prover re-proves, right then, that an active suspension can never come out cleared, across every possible date. The second line is a deliberately broken version that must fail. No rubber stamps.",
  },
  {
    id: "beat7",
    title: "An audit you can hand to a commission",
    from: 125,
    to: 140,
    mode: "voiceover",
    footage: "beat7.mp4",
    clipStart: 6.0, // tail-anchored: canvas opens at 15.2s, held to the end
    vo: "beat7.wav",
    voDelay: 0,
    script:
      "Every decision, hash-chained and append-only. Edit one past entry and verification names it. One click exports the whole trail to a Canvas you can hand to a promoter or a commission.",
  },
  {
    id: "beat8",
    title: "It watches the roster on its own",
    from: 140,
    to: 153,
    mode: "voiceover",
    footage: "beat8.mp4",
    clipStart: 1.5,
    vo: "beat8.wav",
    voDelay: 0.4,
    script:
      "And it does not wait to be asked. A daily digest: windows about to lapse, windows just lapsed, new blocks. Deterministic triggers only. Quiet days send nothing.",
  },
  {
    id: "beat9",
    title: "Run the proof yourself",
    from: 153,
    to: 163,
    mode: "voiceover",
    footage: "beat9.mp4",
    clipStart: 2.8, // PROVEN stamp thunks at 5.0s -> lands 2.2s into the beat
    vo: "beat9.wav",
    script:
      "All of it is live right now. Real numbers from the real database, and that proof button works for you too. Milliseconds.",
  },
  {
    id: "beat10",
    title: "Close",
    from: 163,
    to: 175,
    mode: "camera",
    footage: "camera-beat10.mp4",
    clipStart: 1.0, // speech 2.22-9.40s; end card overlays after the line ends
    script:
      "CornerCheck is one cross-check, where fight teams already work, between a fighter and the worst day of someone's life. Thank you for watching.",
  },
];

export const TOTAL_SECONDS = 175; // 2:55
export const TOTAL_FRAMES = TOTAL_SECONDS * FPS;

// End card fades in this many seconds into beat 10 (after "Thank you for watching").
export const END_CARD_AT = 8.8;
