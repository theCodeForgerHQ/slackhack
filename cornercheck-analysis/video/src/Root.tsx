import "./index.css";
import { Composition } from "remotion";
import { Demo } from "./Demo";
import { FPS, TOTAL_FRAMES } from "./beats";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Demo"
        component={Demo}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ showCaptions: true }}
      />
    </>
  );
};
