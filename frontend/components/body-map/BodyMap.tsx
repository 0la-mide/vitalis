"use client";

/**
 * Original, simple body silhouettes drawn for VITALIS (front, back, zoomed head).
 * Each shape is a tappable region whose code matches backend/data/symptoms.json.
 */

type RegionShape = { region: string; d?: string; ellipse?: [number, number, number, number]; mirror?: boolean };

const ARM = "M62,86 Q47,90 44,112 L35,198 Q34,208 41,210 L49,210 L57,142 L64,118 Z";
const HAND: [number, number, number, number] = [42, 225, 10, 14];
const LEG = "M68,238 Q84,250 98,244 L97,330 L93,398 L75,398 L71,330 Z";
const FOOT = "M74,398 L94,398 L97,413 Q86,421 68,418 Z";

const FRONT: RegionShape[] = [
  { region: "head", ellipse: [100, 38, 24, 28] },
  { region: "neck", d: "M90,63 L110,63 L113,82 L87,82 Z" },
  { region: "chest", d: "M62,86 Q100,74 138,86 L137,140 L63,140 Z" },
  { region: "upper_abdomen", d: "M63,140 L137,140 L135,180 L65,180 Z" },
  { region: "lower_abdomen", d: "M65,180 L135,180 L135,214 L65,214 Z" },
  { region: "pelvis", d: "M65,214 L135,214 Q132,240 112,248 L100,240 L88,248 Q68,240 65,214 Z" },
  { region: "arms", d: ARM },
  { region: "arms", d: ARM, mirror: true },
  { region: "hands", ellipse: HAND },
  { region: "hands", ellipse: HAND, mirror: true },
  { region: "legs", d: LEG },
  { region: "legs", d: LEG, mirror: true },
  { region: "feet", d: FOOT },
  { region: "feet", d: FOOT, mirror: true },
];

const BACK: RegionShape[] = [
  { region: "head", ellipse: [100, 38, 24, 28] },
  { region: "neck", d: "M90,63 L110,63 L113,82 L87,82 Z" },
  { region: "back_upper", d: "M62,86 Q100,74 138,86 L136,168 L64,168 Z" },
  { region: "back_lower", d: "M64,168 L136,168 L135,214 Q100,224 65,214 Z" },
  { region: "pelvis", d: "M65,214 Q100,224 135,214 Q132,240 112,248 L100,240 L88,248 Q68,240 65,214 Z" },
  { region: "arms", d: ARM },
  { region: "arms", d: ARM, mirror: true },
  { region: "hands", ellipse: HAND },
  { region: "hands", ellipse: HAND, mirror: true },
  { region: "legs", d: LEG },
  { region: "legs", d: LEG, mirror: true },
  { region: "feet", d: FOOT },
  { region: "feet", d: FOOT, mirror: true },
];

const HEAD_ZOOM: RegionShape[] = [
  { region: "head", ellipse: [100, 98, 70, 86] },
  { region: "ears", ellipse: [30, 112, 13, 24] },
  { region: "ears", ellipse: [170, 112, 13, 24] },
  { region: "face", ellipse: [100, 124, 52, 56] },
  { region: "eyes", ellipse: [78, 110, 14, 9] },
  { region: "eyes", ellipse: [122, 110, 14, 9] },
  { region: "mouth_throat", ellipse: [100, 154, 20, 10] },
  { region: "neck", d: "M72,182 L128,182 L132,220 L68,220 Z" },
];

export type BodyView = "front" | "back" | "head";

function Shape({
  s,
  label,
  active,
  onTap,
}: {
  s: RegionShape;
  label: string;
  active: boolean;
  onTap: () => void;
}) {
  const common = {
    className: "body-region",
    "data-active": active,
    role: "button",
    tabIndex: 0,
    "aria-label": label,
    onClick: onTap,
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onTap();
      }
    },
  } as const;
  const shape = s.ellipse ? (
    <ellipse cx={s.ellipse[0]} cy={s.ellipse[1]} rx={s.ellipse[2]} ry={s.ellipse[3]} {...common} />
  ) : (
    <path d={s.d} {...common} />
  );
  return s.mirror ? <g transform="translate(200,0) scale(-1,1)">{shape}</g> : shape;
}

export function BodyMap({
  view,
  active,
  labels,
  onSelect,
}: {
  view: BodyView;
  active: string | null;
  labels: Record<string, string>;
  onSelect: (region: string) => void;
}) {
  const shapes = view === "front" ? FRONT : view === "back" ? BACK : HEAD_ZOOM;
  const viewBox = view === "head" ? "0 0 200 225" : "20 0 160 425";
  return (
    <svg
      viewBox={viewBox}
      className="mx-auto h-[min(58vh,460px)] w-auto touch-manipulation"
      role="group"
      aria-label={view === "head" ? "Head" : `Body, ${view}`}
    >
      {shapes.map((s, i) => (
        <Shape
          key={`${s.region}-${i}`}
          s={s}
          label={labels[s.region] ?? s.region}
          active={active === s.region}
          onTap={() => onSelect(s.region)}
        />
      ))}
      {view === "head" && (
        <g pointerEvents="none" stroke="var(--primary)" strokeWidth="2" fill="none" strokeLinecap="round">
          <circle cx="78" cy="110" r="3.5" fill="var(--primary)" />
          <circle cx="122" cy="110" r="3.5" fill="var(--primary)" />
          <path d="M96,128 Q100,138 104,128" />
        </g>
      )}
    </svg>
  );
}
