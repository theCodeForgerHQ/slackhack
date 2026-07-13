import React from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Audio, Video } from "@remotion/media";
import { BEATS, END_CARD_AT, FPS, type Beat } from "./beats";
import captionsData from "./captions.json";

type CaptionSpan = { text: string; from: number; to: number };
const CAPTION_SPANS: Record<string, CaptionSpan[]> = captionsData;

const BG = "#0b1220";
const TEXT = "#e6edf3";
const SUB = "#9fb3c8";
const GREEN = "#7ee2b8";

// Beat 1: animated title card from the committed PNG. Slow scale + fade,
// deterministic, text stays pixel-perfect (the reason this is not AI b-roll).
const TitleCard: React.FC = () => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 3 * FPS], [1.0, 1.05], {
    extrapolateRight: "clamp",
  });
  const opacity = interpolate(frame, [0, 8, 3 * FPS - 8, 3 * FPS], [0, 1, 1, 0]);
  return (
    <AbsoluteFill style={{ backgroundColor: BG, opacity }}>
      <Img
        src={staticFile("title.png")}
        style={{ width: "100%", height: "100%", transform: `scale(${scale})` }}
      />
    </AbsoluteFill>
  );
};

// Beat 10 tail: end card fades in once the close line has landed.
const EndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ backgroundColor: BG, opacity }}>
      <Img src={staticFile("end.png")} style={{ width: "100%", height: "100%" }} />
    </AbsoluteFill>
  );
};

// Dip-to-dark beat transitions: each beat fades in from the background color.
const FadeIn: React.FC<{ frames: number; children: React.ReactNode }> = ({
  frames,
  children,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, frames], [0, 1], {
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ backgroundColor: BG, opacity }}>{children}</AbsoluteFill>;
};

// Placeholder shown until real footage lands in public/footage/.
const Placeholder: React.FC<{ beat: Beat }> = ({ beat }) => (
  <AbsoluteFill
    style={{
      backgroundColor: BG,
      justifyContent: "center",
      alignItems: "center",
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      color: TEXT,
      padding: 120,
    }}
  >
    <div style={{ color: GREEN, fontSize: 34, letterSpacing: "0.18em", fontWeight: 700 }}>
      {beat.mode.toUpperCase()}
    </div>
    <div style={{ fontSize: 64, fontWeight: 800, margin: "18px 0 30px" }}>{beat.title}</div>
    <div style={{ fontSize: 30, color: SUB, maxWidth: 1400, lineHeight: 1.5, textAlign: "center" }}>
      drop footage at public/footage/{beat.id}.mp4 and set `footage` in beats.ts
    </div>
  </AbsoluteFill>
);

// Burned-in captions: the beat's script split into sentences, each shown for a
// share of the speech window proportional to its word count. Judges often watch
// muted; the captions carry the argument without sound.
const Captions: React.FC<{ beat: Beat; startSec: number; durationSec: number }> = ({
  beat,
  startSec,
  durationSec,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // Word-aligned spans from the recorded audio (whisper.cpp); proportional fallback.
  let spans: CaptionSpan[] | undefined = CAPTION_SPANS[beat.id];
  if (!spans || spans.length === 0) {
    const sentences = beat.script
      .split(/(?<=[.!?])\s+/)
      .map((s) => s.trim())
      .filter(Boolean);
    const totalWords = sentences.reduce((n, s) => n + s.split(/\s+/).length, 0);
    if (totalWords === 0) return null;
    let cursor = startSec;
    spans = sentences.map((s) => {
      const share = (s.split(/\s+/).length / totalWords) * durationSec;
      const span = { text: s, from: cursor, to: cursor + share };
      cursor += share;
      return span;
    });
  }
  const t = frame / fps;
  const active = spans.find((s) => t >= s.from && t < s.to);
  if (!active) return null;
  return (
    <div
      style={{
        position: "absolute",
        bottom: 64,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          background: "rgba(7, 12, 22, 0.86)",
          color: TEXT,
          borderRadius: 14,
          padding: "16px 30px",
          fontSize: 34,
          lineHeight: 1.35,
          maxWidth: 1320,
          textAlign: "center",
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          textShadow: "0 1px 2px rgba(0,0,0,0.8)",
        }}
      >
        {active.text}
      </div>
    </div>
  );
};

// Music ducking: quiet under speech, opens up in the no-speech gaps (title card,
// beat boundaries, end card). The bed itself also swells at these moments; the two
// together read as the score "breathing" between lines.
const MUSIC_LO = 0.07;
const MUSIC_HI = 0.16;
const OPEN_WINDOWS: Array<[number, number]> = [
  [21.8, 25.2], // title card
  ...[48, 72, 90, 107, 125, 140, 153, 163].map(
    (b): [number, number] => [b - 0.5, b + 0.7],
  ),
  [171.5, 175], // end card
];

const musicVolumeAt = (s: number): number => {
  let v = MUSIC_LO;
  for (const [a, b] of OPEN_WINDOWS) {
    const ramp = Math.max(
      0,
      Math.min(1, (s - a) / 0.4, (b - s) / 0.4),
    );
    v = Math.max(v, MUSIC_LO + (MUSIC_HI - MUSIC_LO) * ramp);
  }
  return v;
};

export const Demo: React.FC<{ showCaptions: boolean }> = ({ showCaptions }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: BG }}>
      <Audio
        src={staticFile("vo/music-bed.wav")}
        volume={(f) => musicVolumeAt(f / fps)}
      />
      {BEATS.map((beat) => {
        const from = Math.round(beat.from * fps);
        const duration = Math.round((beat.to - beat.from) * fps);
        const voDelay = beat.voDelay ?? 0.6;
        // Speech window for caption pacing: camera beats speak from ~1s in;
        // voiceover beats follow the VO start and its trimmed length (~slot).
        const speechStart = beat.mode === "camera" ? 1.0 : voDelay;
        const speechDuration = Math.max(2, beat.to - beat.from - speechStart - 1.2);
        return (
          <Sequence key={beat.id} from={from} durationInFrames={duration} premountFor={fps}>
            {beat.id === "beat1" ? (
              <TitleCard />
            ) : beat.footage ? (
              <FadeIn frames={beat.from === 0 ? 12 : 6}>
                {/* Screen clips carry stray mic audio; the camera bookends keep theirs. */}
                <Video
                  src={staticFile(`footage/${beat.footage}`)}
                  muted={beat.mode !== "camera"}
                  trimBefore={Math.round((beat.clipStart ?? 0) * fps)}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
                {beat.vo ? (
                  <Sequence from={Math.round(voDelay * fps)} layout="none" premountFor={fps}>
                    <Audio src={staticFile(`vo/${beat.vo}`)} />
                  </Sequence>
                ) : null}
                {showCaptions && beat.script ? (
                  <Captions beat={beat} startSec={speechStart} durationSec={speechDuration} />
                ) : null}
              </FadeIn>
            ) : (
              <Placeholder beat={beat} />
            )}
            {beat.id === "beat10" ? (
              <Sequence from={Math.round(END_CARD_AT * fps)} layout="none" premountFor={fps}>
                <EndCard />
              </Sequence>
            ) : null}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
