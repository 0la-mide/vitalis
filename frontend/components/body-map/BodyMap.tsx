"use client";

/**
 * VITALIS body map: original anatomical line art (front, back, zoomed head) for male, female, pregnant, child and
 * sex-not-recorded adults. Each tappable region's code matches backend/data/symptoms.json.
 */

import { useId } from "react";
import { body, type BodyType, type Landmarks } from "./geometry";

export type BodyView = "front" | "back" | "head";
type Region = { region: string; d: string };

const rect = (x: number, y: number, w: number, h: number) => `M${x},${y} h${w} v${h} h${-w} Z`;
const poly = (pts: [number, number][]) => `M${pts.map((p) => p.join(",")).join(" L")} Z`;
const mirror = (pts: [number, number][]) => pts.map(([x, y]) => [200 - x, y] as [number, number]);

/** Regions in paint order: later ones win where they overlap (arms and hands sit over the torso bands). */
function regions(lm: Landmarks, view: "front" | "back"): Region[] {
  const [ax, ay] = lm.armpit;
  const [wx, wy] = lm.innerWrist;
  const arm: [number, number][] = [[0, lm.chestTop + 2], [ax + 1, lm.chestTop + 2], [ax + 1, ay], [wx + 1, wy], [0, wy]];
  const hand: [number, number][] = [[0, wy], [wx + 3, wy], [wx + 8, lm.handBottom + 6], [0, lm.handBottom + 6]];
  const leg: [number, number][] = [[0, lm.legLine], [100, lm.crotch + 6], [100, lm.ankle], [0, lm.ankle]];
  const hip: [number, number][] = [
    [0, lm.pelvisTop], [200, lm.pelvisTop], [200, lm.legLine], [100, lm.crotch + 6], [0, lm.legLine],
  ];
  const torso =
    view === "front"
      ? [
          { region: "chest", d: rect(0, lm.chestTop, 200, lm.upperAbdTop - lm.chestTop) },
          { region: "upper_abdomen", d: rect(0, lm.upperAbdTop, 200, lm.lowerAbdTop - lm.upperAbdTop) },
          { region: "lower_abdomen", d: rect(0, lm.lowerAbdTop, 200, lm.pelvisTop - lm.lowerAbdTop) },
          { region: "pelvis", d: poly(hip) },
        ]
      : [
          { region: "back_upper", d: rect(0, lm.chestTop, 200, lm.backSplit - lm.chestTop) },
          // Lower back and buttocks: the back of the pelvis is not "private parts".
          { region: "back_lower", d: rect(0, lm.backSplit, 200, lm.pelvisTop - lm.backSplit).concat(" ", poly(hip)) },
        ];
  return [
    { region: "head", d: rect(0, 0, 200, lm.neckTop) },
    { region: "neck", d: rect(70, lm.neckTop, 60, lm.chestTop - lm.neckTop) },
    ...torso,
    { region: "legs", d: `${poly(leg)} ${poly(mirror(leg))}` },
    { region: "feet", d: `${rect(0, lm.ankle, 200, 60)}` },
    { region: "arms", d: `${poly(arm)} ${poly(mirror(arm))}` },
    { region: "hands", d: `${poly(hand)} ${poly(mirror(hand))}` },
  ];
}

/** Clinical line art: shows which way the body faces and what kind of body it is. Not tappable. */
function Anatomy({ type, view, lm }: { type: BodyType; view: "front" | "back"; lm: Landmarks }) {
  const c = lm.crotch;
  const both = (d: string, key: string) => (
    <g key={key}>
      <path d={d} />
      <path d={d} transform="translate(200,0) scale(-1,1)" />
    </g>
  );
  const head = type === "child" ? { eyeY: 50, mouthY: 66, cx: 100 } : { eyeY: 36, mouthY: 52, cx: 100 };
  if (view === "back") {
    return (
      <g>
        {/* hairline / back of head */}
        <path d={type === "child" ? "M76,40 Q100,22 124,40" : "M80,28 Q100,14 120,28"} />
        {/* spine */}
        <path d={`M100,${lm.chestTop + 2} L100,${lm.pelvisTop + 6}`} strokeDasharray="2 3" />
        {/* shoulder blades */}
        {both(`M${78},${lm.chestTop + 16} Q${72},${lm.chestTop + 34} ${84},${lm.chestTop + 48}`, "scap")}
        {/* buttocks: cleft and folds */}
        <path d={`M100,${lm.pelvisTop + 8} L100,${c + 2}`} />
        {both(`M${lm.armpit[0] + 2},${c - 2} Q${84},${c + 8} ${99},${c + 3}`, "glute")}
        {/* backs of knees and heels */}
        {both(`M78,${lm.ankle - 82} Q84,${lm.ankle - 78} 90,${lm.ankle - 82}`, "knee")}
        {both(`M80,${lm.ankle + 22} Q86,${lm.ankle + 28} 92,${lm.ankle + 22}`, "heel")}
      </g>
    );
  }
  const adult = type !== "child";
  return (
    <g>
      {/* face */}
      {both(`M${head.cx - 11},${head.eyeY} q4,-3 8,0`, "eye")}
      <path d={`M100,${head.eyeY + 3} l-2,${type === "child" ? 7 : 8} h4`} />
      <path d={`M${95},${head.mouthY - 4} q5,4 10,0`} />
      {adult ? both(`M98,${lm.chestTop + 2} Q86,${lm.chestTop + 6} 72,${lm.chestTop + 6}`, "clavicle") : null}

      {type === "male" ? (
        <>
          {both(`M70,${lm.chestTop + 44} Q84,${lm.chestTop + 54} 98,${lm.chestTop + 46}`, "pec")}
          {both(`M85,${lm.chestTop + 40} m-1.2,0 a1.2,1.2 0 1,0 2.4,0 a1.2,1.2 0 1,0 -2.4,0`, "nip")}
        </>
      ) : null}
      {type === "female" || type === "pregnant" ? (
        <>
          {both(
            type === "pregnant"
              ? `M69,${lm.chestTop + 36} Q70,${lm.chestTop + 66} 86,${lm.chestTop + 68} Q97,${lm.chestTop + 66} 99,${lm.chestTop + 54}`
              : `M70,${lm.chestTop + 38} Q71,${lm.chestTop + 62} 86,${lm.chestTop + 63} Q96,${lm.chestTop + 62} 99,${lm.chestTop + 52}`,
            "breast",
          )}
          {both(`M86,${lm.chestTop + 52} m-1.2,0 a1.2,1.2 0 1,0 2.4,0 a1.2,1.2 0 1,0 -2.4,0`, "nip")}
        </>
      ) : null}

      {type === "pregnant" ? (
        <>
          {/* the bump: a full round belly with a prominent navel and linea nigra */}
          <path d={`M62,${lm.upperAbdTop + 18} Q54,${lm.pelvisTop + 4} 100,${lm.pelvisTop + 8} Q146,${lm.pelvisTop + 4} 138,${lm.upperAbdTop + 18} Q122,${lm.upperAbdTop - 4} 100,${lm.upperAbdTop - 4} Q78,${lm.upperAbdTop - 4} 62,${lm.upperAbdTop + 18}`} />
          {both(`M66,${lm.lowerAbdTop - 8} q4,10 2,22`, "bumpshade")}
          <path d={`M100,${lm.lowerAbdTop + 6} L100,${lm.pelvisTop + 4}`} strokeDasharray="1.5 2.5" />
          <circle cx="100" cy={lm.lowerAbdTop} r="2.4" />
        </>
      ) : (
        <circle cx="100" cy={lm.lowerAbdTop - 4} r="1.6" />
      )}

      {/* groin creases */}
      {both(`M${lm.armpit[0] + (type === "female" || type === "pregnant" ? 0 : 4)},${lm.pelvisTop + 4} Q86,${lm.legLine} 96,${c - 6}`, "groin")}

      {/* external genitals, drawn as simple clinical outlines (adults only) */}
      {type === "male" ? (
        <g>
          <path d={`M96,${c - 22} Q96,${c - 26} 100,${c - 26} Q104,${c - 26} 104,${c - 22} L104,${c - 9} Q104,${c - 5} 100,${c - 5} Q96,${c - 5} 96,${c - 9} Z`} />
          <path d={`M95,${c - 13} Q89,${c - 1} 100,${c + 1} Q111,${c - 1} 105,${c - 13}`} />
        </g>
      ) : null}
      {type === "female" || type === "pregnant" ? (
        <g>
          <path d={`M100,${c - 16} Q95,${c - 9} 100,${c - 1} Q105,${c - 9} 100,${c - 16}`} />
          <path d={`M100,${c - 13} L100,${c - 3}`} />
        </g>
      ) : null}

      {/* knees */}
      {both(`M78,${lm.ankle - 84} q6,4 12,0`, "knee")}
    </g>
  );
}

function HeadZoom({ active, labels, onSelect }: Omit<Props, "view" | "type">) {
  const shapes: { region: string; el: React.ReactNode }[] = [
    { region: "neck", el: <path d="M74,180 L126,180 L134,224 L66,224 Z" /> },
    { region: "head", el: <ellipse cx={100} cy={100} rx={66} ry={84} /> },
    { region: "ears", el: <ellipse cx={34} cy={112} rx={12} ry={22} /> },
    { region: "ears", el: <ellipse cx={166} cy={112} rx={12} ry={22} /> },
    { region: "face", el: <path d="M48,96 Q50,170 100,182 Q150,170 152,96 Q126,84 100,84 Q74,84 48,96 Z" /> },
    { region: "eyes", el: <ellipse cx={78} cy={110} rx={14} ry={8} /> },
    { region: "eyes", el: <ellipse cx={122} cy={110} rx={14} ry={8} /> },
    { region: "mouth_throat", el: <ellipse cx={100} cy={156} rx={20} ry={10} /> },
  ];
  return (
    <svg viewBox="0 0 200 226" className="mx-auto block h-[min(52vh,420px)] w-full max-w-[320px] touch-manipulation" role="group" aria-label="Head">
      {shapes.map((s, i) => (
        <Tappable key={i} region={s.region} label={labels[s.region] ?? s.region} active={active === s.region} onTap={() => onSelect(s.region)}>
          {s.el}
        </Tappable>
      ))}
      <g pointerEvents="none" stroke="var(--primary)" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.8">
        <path d="M44,90 Q60,20 100,18 Q140,20 156,90" />
        <circle cx="78" cy="110" r="3.5" fill="var(--primary)" />
        <circle cx="122" cy="110" r="3.5" fill="var(--primary)" />
        <path d="M100,116 l-4,18 h8" />
        <path d="M66,96 q10,-6 22,-2 M134,96 q-10,-6 -22,-2" />
      </g>
    </svg>
  );
}

function Tappable({ region, label, active, onTap, children, soft }: {
  region: string; label: string; active: boolean; onTap: () => void; children: React.ReactNode; soft?: boolean;
}) {
  return (
    <g
      className={soft ? "body-region body-region-soft" : "body-region"}
      data-region={region}
      data-active={active}
      role="button"
      tabIndex={0}
      aria-label={label}
      onClick={onTap}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onTap();
        }
      }}
    >
      {children}
    </g>
  );
}

type Props = {
  view: BodyView;
  type: BodyType;
  active: string | null;
  labels: Record<string, string>;
  onSelect: (region: string) => void;
};

export function BodyMap({ view, type, active, labels, onSelect }: Props) {
  const clipId = useId().replace(/:/g, "");
  if (view === "head") return <HeadZoom active={active} labels={labels} onSelect={onSelect} />;
  const b = body(type);
  return (
    <svg
      viewBox="20 2 160 450"
      className="mx-auto block h-[min(58vh,470px)] w-full max-w-[260px] touch-manipulation"
      role="group"
      aria-label={`Body, ${view}`}
    >
      <defs>
        <clipPath id={clipId}>
          <path d={b.outline} />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clipId})`}>
        {regions(b.lm, view).map((r) => (
          <Tappable key={r.region} soft region={r.region} label={labels[r.region] ?? r.region} active={active === r.region}
            onTap={() => onSelect(r.region)}>
            <path d={r.d} fillRule="nonzero" />
          </Tappable>
        ))}
      </g>
      <path d={b.outline} fill="none" stroke="var(--primary)" strokeWidth="1.8" strokeLinejoin="round" pointerEvents="none" />
      <g pointerEvents="none" fill="none" stroke="var(--primary)" strokeWidth="1.1" strokeLinecap="round" opacity="0.7">
        <Anatomy type={type} view={view} lm={b.lm} />
      </g>
    </svg>
  );
}
