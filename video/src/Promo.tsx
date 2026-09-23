import React from "react";
import {
  AbsoluteFill, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Easing,
} from "remotion";
import { Audio } from "@remotion/media";
import { loadFont as loadAnton } from "@remotion/google-fonts/Anton";
import { loadFont as loadBitter } from "@remotion/google-fonts/Bitter";
import T from "./timeline.json";
import D from "./data.json";

const { fontFamily: ANTON } = loadAnton("normal", { weights: ["400"], subsets: ["latin", "latin-ext"] });
const { fontFamily: BITTER } = loadBitter("normal", { weights: ["400", "800"], subsets: ["latin", "latin-ext"] });

const C = { yellow: "#F3DC07", yellow2: "#F6E74E", red: "#C93118", oxblood: "#730A03", ink: "#000", paper: "#fff" };
const BAR = `linear-gradient(90deg, ${C.yellow} 0%, #EDB10C 28%, #DE7414 52%, ${C.red} 76%, ${C.oxblood} 100%)`;
const fmt = (n: number) => n.toLocaleString("da-DK", { maximumFractionDigits: 1 });
const scoreColor = (s: number) => (s >= 8.5 ? C.yellow : s >= 7.5 ? "#EDB10C" : s >= 6.5 ? "#DE7414" : s >= 5 ? C.red : C.oxblood);
const scoreInk = (s: number) => (s < 6.5 ? C.paper : C.ink);

// ---------- building blocks ----------
const shout = (size: number, extra: React.CSSProperties = {}): React.CSSProperties => ({
  fontFamily: ANTON, fontSize: size, lineHeight: 0.95, color: C.paper, textTransform: "uppercase",
  WebkitTextStroke: `${size * 0.09}px ${C.ink}`, paintOrder: "stroke fill", textShadow: `${size * 0.06}px ${size * 0.07}px 0 ${C.ink}`,
  ...extra,
});

const Halftone: React.FC<{ color?: string }> = ({ color = C.yellow2 }) => (
  <AbsoluteFill style={{ backgroundColor: color, backgroundImage: "radial-gradient(rgba(115,10,3,0.12) 3px, transparent 3.4px)", backgroundSize: "26px 26px" }} />
);

/** Analog TV snow, deterministic per frame. */
const Snow: React.FC<{ opacity?: number }> = ({ opacity = 1 }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ opacity }}>
      <svg width="100%" height="100%" preserveAspectRatio="none">
        <filter id={`n${f}`}><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={f * 13 + 1} /><feColorMatrix type="saturate" values="0" /></filter>
        <rect width="100%" height="100%" filter={`url(#n${f})`} />
      </svg>
      <AbsoluteFill style={{ background: "repeating-linear-gradient(0deg, rgba(0,0,0,.35) 0 3px, transparent 3px 7px)" }} />
    </AbsoluteFill>
  );
};

/** Decaying camera shake after a hit. */
const shakeAt = (frame: number, hits: number[], amp = 26) => {
  const last = hits.filter((h) => h <= frame).pop();
  if (last === undefined) return { x: 0, y: 0 };
  const t = frame - last;
  const a = amp * Math.exp(-t / 3.5);
  return { x: Math.sin(t * 2.7) * a, y: Math.cos(t * 3.3) * a };
};

const ScoreDisc: React.FC<{ score: number; size: number; pop?: number; rot?: number }> = ({ score, size, pop = 1, rot = -8 }) => (
  <div style={{
    width: size, height: size, borderRadius: "50%", background: scoreColor(score), color: scoreInk(score),
    border: `${size * 0.07}px solid ${C.ink}`, boxShadow: `${size * 0.06}px ${size * 0.06}px 0 ${C.ink}`,
    display: "grid", placeItems: "center", fontFamily: ANTON, fontSize: size * 0.42, transform: `scale(${pop}) rotate(${rot}deg)`,
  }}>{fmt(score)}</div>
);

const NameBar: React.FC<{ name: string; sub?: string; size?: number }> = ({ name, sub, size = 92 }) => (
  <div style={{ position: "relative", display: "inline-flex", flexDirection: "column", alignItems: "flex-start", paddingLeft: size * 1.05 }}>
    <Img src={staticFile("durum.webp")} style={{ position: "absolute", left: 0, top: -size * 0.55, width: size * 1.6, zIndex: 2, filter: "drop-shadow(5px 5px 0 #000)" }} />
    <div style={{ background: BAR, border: `${size * 0.09}px solid ${C.ink}`, borderRadius: 999, padding: `${size * 0.12}px ${size * 0.45}px ${size * 0.06}px ${size * 0.75}px`,
      boxShadow: "inset 0 0 0 6px rgba(255,255,255,.55), 6px 6px 0 #000", maxWidth: 820 }}>
      <div style={shout(size, { whiteSpace: "nowrap" })}>{name}</div>
    </div>
    {sub && <div style={{ marginTop: 18, marginLeft: size * 0.7, background: C.ink, color: C.paper, fontFamily: BITTER, fontSize: size * 0.34,
      padding: "4px 18px 6px", boxShadow: `0 0 0 4px ${C.paper}, 0 0 0 8px ${C.ink}` }}>{sub}</div>}
  </div>
);

// ---------- scenes ----------
const Hook: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = ["HVEM HAR", "KØBENHAVNS", "BEDSTE DÜRÜM?"];
  const s = shakeAt(f, T.hookWords, 30);
  return (
    <AbsoluteFill>
      <Halftone />
      <AbsoluteFill style={{ transform: `translate(${s.x}px, ${s.y}px)`, justifyContent: "center", alignItems: "center", gap: 18, paddingBottom: 120 }}>
        {words.map((w, i) => {
          const start = T.hookWords[i];
          const p = spring({ frame: f - start, fps, config: { damping: 11, stiffness: 180 } });
          const size = i === 2 ? 150 : 170;
          return (
            <div key={w} style={{ ...shout(size, i === 2 ? { color: C.red } : {}), opacity: f >= start ? 1 : 0,
              transform: `scale(${interpolate(p, [0, 1], [3.2, 1])}) rotate(${interpolate(p, [0, 1], [i % 2 ? 12 : -12, i === 1 ? 2 : -2])}deg)` }}>{w}</div>
          );
        })}
      </AbsoluteFill>
      <Img src={staticFile("logo.jpg")} style={{ position: "absolute", top: 110, left: "50%", width: 170, marginLeft: -85, borderRadius: "50%", clipPath: "circle(49%)",
        transform: `rotate(${interpolate(f, [0, 60], [-20, 6])}deg)` }} />
      <Img src={staticFile("durum.webp")} style={{ position: "absolute", bottom: 260, right: -40, width: 420, filter: "drop-shadow(10px 10px 0 #000)",
        transform: `rotate(${-18 + Math.sin(f / 5) * 6}deg) translateY(${interpolate(spring({ frame: f - 40, fps }), [0, 1], [600, 0])}px)` }} />
      {f < 9 && <Snow />}
    </AbsoluteFill>
  );
};

const Zap: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const idx = Math.min(D.zaps.length - 1, Math.floor(f / T.zapEvery));
  const local = f - idx * T.zapEvery;
  const z = D.zaps[idx];
  const count = Math.round(interpolate(f, [0, 110], [0, D.episodes], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }));
  const pop = spring({ frame: local, fps, config: { damping: 9, stiffness: 260 } });
  return (
    <AbsoluteFill>
      <Halftone />
      <div style={{ position: "absolute", top: 180, width: "100%", textAlign: "center" }}>
        <div style={shout(230, { color: C.yellow })}>{count}</div>
        <div style={shout(96)}>anmeldelser</div>
      </div>
      {/* the TV set */}
      <div style={{ position: "absolute", left: 50, right: 50, top: 700, background: "#1b1b1b", border: "10px solid #000", borderRadius: 60, padding: "40px 40px 0",
        boxShadow: "inset 0 0 0 10px #2c2c2c, 18px 18px 0 #000" }}>
        <div style={{ position: "relative", aspectRatio: "16/9", overflow: "hidden", borderRadius: "40px / 54px", border: "6px solid #000", background: "#000" }}>
          <Img src={staticFile(z.thumb)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          <div style={{ position: "absolute", top: 26, right: 34, fontFamily: ANTON, fontSize: 70, color: "#7CFF5B", textShadow: "0 0 12px rgba(124,255,91,.8), 3px 3px 0 #000" }}>
            <span style={{ fontSize: 42 }}>KAN </span>{95 - idx * 6}
          </div>
          <div style={{ position: "absolute", top: 24, left: 28 }}><ScoreDisc score={z.score} size={150} pop={pop} /></div>
          <AbsoluteFill style={{ background: "repeating-linear-gradient(0deg, rgba(0,0,0,.18) 0 2px, transparent 2px 6px), radial-gradient(140% 120% at 50% 50%, transparent 60%, rgba(0,0,0,.55))" }} />
          {local < 3 && <Snow />}
        </div>
        <div style={{ height: 96, display: "flex", alignItems: "center", gap: 20, padding: "0 10px" }}>
          <div style={{ fontFamily: ANTON, color: C.yellow, fontSize: 52, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", flex: 1 }}>{z.name}</div>
          {[0, 1].map((k) => <div key={k} style={{ width: 50, height: 50, borderRadius: "50%", border: "5px solid #000", background: "conic-gradient(#555,#222,#555,#222,#555)" }} />)}
        </div>
      </div>
      <div style={{ position: "absolute", top: 1560, width: "100%", textAlign: "center", fontFamily: BITTER, fontWeight: 800, fontSize: 56 }}>
        Karakter på hver eneste rulle.
      </div>
    </AbsoluteFill>
  );
};

const Phone: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const inP = spring({ frame: f, fps, config: { damping: 14 } });
  const screenW = 760, screenH = 1400;
  const imgH = (D.hitlistSize[1] / D.hitlistSize[0]) * screenW;
  const scroll = interpolate(f, [18, 115], [0, Math.min(imgH - screenH, 3600)], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  return (
    <AbsoluteFill>
      <Halftone color={C.yellow} />
      <div style={{ position: "absolute", top: 90, width: "100%", textAlign: "center" }}>
        <div style={shout(120)}>Alle karakterer.</div>
        <div style={shout(120, { color: C.yellow2 })}>Ét sted.</div>
      </div>
      <div style={{ position: "absolute", left: (1080 - screenW - 48) / 2, top: 400, width: screenW + 48, height: screenH + 48, background: "#111",
        borderRadius: 96, border: "8px solid #000", padding: 24, boxShadow: "20px 20px 0 #000",
        transform: `translateY(${interpolate(inP, [0, 1], [1400, 0])}px) rotate(${interpolate(inP, [0, 1], [14, -3])}deg)` }}>
        <div style={{ position: "relative", width: screenW, height: screenH, overflow: "hidden", borderRadius: 72, background: C.yellow2 }}>
          <Img src={staticFile("hitlist-full.png")} style={{ position: "absolute", width: screenW, top: -scroll }} />
          <div style={{ position: "absolute", top: 18, left: "50%", width: 150, height: 40, marginLeft: -75, background: "#000", borderRadius: 999 }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const MapScene: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const zoom = interpolate(f, [0, 90], [1.0, 1.35]);
  const pins = [[260, 760], [640, 640], [470, 980], [800, 1120], [330, 1240]];
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Img src={staticFile("map-mobile.png")} style={{ position: "absolute", inset: 0, width: 1080, height: 1920, objectFit: "cover", transform: `scale(${zoom})`, transformOrigin: "55% 40%" }} />
      {pins.map(([x, y], i) => {
        const p = spring({ frame: f - 8 - i * 7, fps, config: { damping: 8, stiffness: 200 } });
        return <Img key={i} src={staticFile("pin.webp")} style={{ position: "absolute", left: x, top: y, width: 150,
          transform: `translateY(${interpolate(p, [0, 1], [-1200, 0])}px)`, filter: "drop-shadow(6px 6px 0 #000)" }} />;
      })}
      <div style={{ position: "absolute", bottom: 330, width: "100%", textAlign: "center" }}>
        <div style={shout(150, { color: C.yellow })}>Kebab-kortet</div>
        <div style={{ display: "inline-block", marginTop: 20, background: C.ink, color: C.paper, fontFamily: BITTER, fontWeight: 800, fontSize: 52, padding: "8px 30px", borderRadius: 999 }}>
          {D.places} steder, farvet efter karakter
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Top3: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const hits = T.topHits.map((h) => h - T.topStart);
  const stamp = T.stampAt - T.topStart;
  const rank = f < hits[1] ? 3 : f < hits[2] ? 2 : 1;
  const item = D.top3[rank - 1];
  const since = f - hits[3 - rank];
  const p = spring({ frame: since, fps, config: { damping: 11, stiffness: 170 } });
  const s = shakeAt(f, [...hits, stamp], rank === 1 ? 34 : 18);
  const stampP = spring({ frame: f - stamp, fps, config: { damping: 9, stiffness: 240 } });
  return (
    <AbsoluteFill>
      <Halftone color={rank === 1 ? C.yellow : C.yellow2} />
      <AbsoluteFill style={{ transform: `translate(${s.x}px, ${s.y}px)` }}>
        <div style={{ position: "absolute", top: 120, width: "100%", textAlign: "center" }}>
          {rank === 1
            ? <div style={shout(92)}>Københavns bedste dürüm</div>
            : <div style={shout(92)}>Top 3 i København</div>}
          <div style={shout(330, { color: rank === 1 ? C.red : C.yellow, transform: `scale(${interpolate(p, [0, 1], [2.4, 1])})`, marginTop: 10 })}>#{rank}</div>
        </div>
        <div style={{ position: "absolute", top: 760, left: 70, right: 70, transform: `translateX(${interpolate(p, [0, 1], [1200, 0])}px) rotate(${rank === 2 ? 2 : -2}deg)` }}>
          <div style={{ position: "relative", border: "10px solid #000", borderRadius: 40, overflow: "hidden", boxShadow: "16px 16px 0 #000", aspectRatio: "16/9" }}>
            <Img src={staticFile(item.thumb)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </div>
          <div style={{ position: "absolute", right: -30, top: -70 }}><ScoreDisc score={item.score} size={230} pop={interpolate(p, [0, 1], [0, 1])} rot={10} /></div>
          <div style={{ marginTop: 70 }}><NameBar name={item.name} sub={item.sub} size={rank === 1 ? 104 : 92} /></div>
        </div>
        {rank === 1 && f >= stamp && (
          <Img src={staticFile("stamp-dum-durum.webp")} style={{ position: "absolute", left: 70, top: 640, width: 330, filter: "drop-shadow(8px 8px 0 #000)",
            transform: `scale(${interpolate(stampP, [0, 1], [4, 1])}) rotate(${interpolate(stampP, [0, 1], [-40, -14])}deg)`, opacity: interpolate(stampP, [0, 0.2], [0, 1], { extrapolateRight: "clamp" }) }} />
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const End: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: f, fps, config: { damping: 12 } });
  const p2 = spring({ frame: f - 10, fps, config: { damping: 12 } });
  return (
    <AbsoluteFill>
      <Halftone />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 40, paddingBottom: 200 }}>
        <Img src={staticFile("logo.jpg")} style={{ width: 460, borderRadius: "50%", clipPath: "circle(49%)", transform: `scale(${p}) rotate(${interpolate(p, [0, 1], [-90, -6])}deg)` }} />
        <div style={shout(110, { transform: `scale(${p2})` })}>Se hele listen</div>
        <div style={{ background: C.ink, color: C.yellow, fontFamily: ANTON, fontSize: 84, padding: "14px 44px 20px", borderRadius: 999, boxShadow: `8px 8px 0 ${C.red}`,
          transform: `translateY(${interpolate(p2, [0, 1], [300, 0])}px)` }}>kebabtv.vercel.app</div>
        <div style={{ fontFamily: BITTER, fontWeight: 800, fontSize: 40, opacity: interpolate(f, [20, 35], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
          Lavet med kebab-kærlighed af jinjrstudio.com
        </div>
      </AbsoluteFill>
      <Img src={staticFile("slogan.webp")} style={{ position: "absolute", bottom: 250, right: 40, width: 330, transform: `rotate(-8deg) scale(${spring({ frame: f - 18, fps })})` }} />
    </AbsoluteFill>
  );
};

/** Thin progress bar on top: people stay to see it fill. */
const Progress: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <div style={{ position: "absolute", top: 0, left: 0, height: 16, width: `${(f / T.total) * 100}%`, background: BAR, borderBottom: "4px solid #000" }} />
  );
};

export const Promo: React.FC = () => (
  <AbsoluteFill style={{ background: C.yellow2 }}>
    <Audio src={staticFile("soundtrack.wav")} />
    <Sequence durationInFrames={T.zapStart}><Hook /></Sequence>
    <Sequence from={T.zapStart} durationInFrames={T.phoneStart - T.zapStart}><Zap /></Sequence>
    <Sequence from={T.phoneStart} durationInFrames={T.mapStart - T.phoneStart}><Phone /></Sequence>
    <Sequence from={T.mapStart} durationInFrames={T.topStart - T.mapStart}><MapScene /></Sequence>
    <Sequence from={T.topStart} durationInFrames={T.endStart - T.topStart}><Top3 /></Sequence>
    <Sequence from={T.endStart}><End /></Sequence>
    {/* short static flash on every scene cut */}
    {[T.zapStart, T.phoneStart, T.mapStart, T.topStart, T.endStart].map((c) => (
      <Sequence key={c} from={c} durationInFrames={4}><Snow opacity={0.85} /></Sequence>
    ))}
    <Progress />
  </AbsoluteFill>
);
