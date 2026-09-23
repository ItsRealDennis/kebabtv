import React from "react";
import { Composition } from "remotion";
import { Promo } from "./Promo";
import T from "./timeline.json";

export const RemotionRoot: React.FC = () => (
  <Composition id="Promo" component={Promo} durationInFrames={T.total} fps={T.fps} width={1080} height={1920} />
);
