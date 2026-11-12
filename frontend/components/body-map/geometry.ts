/**
 * Body geometry for the VITALIS body map. Original artwork, drawn as clinical line art.
 *
 * Each body is ONE smooth outline (left half, mirrored), so head, arms, hands, legs and feet are joined. Tappable
 * regions are simple bands/polygons clipped to that outline, so they always follow the body's real shape.
 * viewBox: 0 0 200 460, body centred on x = 100.
 */

// "adult" = sex not recorded: the male outline without sex-specific anatomy.
export type BodyType = "male" | "female" | "pregnant" | "child" | "adult";
type P = [number, number] | [number, number, 1]; // third value = sharp corner

/** Closed Catmull-Rom spline through the points, as an SVG path. Corner points are kept sharp. */
function smooth(points: P[]): string {
  const pts: [number, number][] = [];
  for (const p of points) {
    pts.push([p[0], p[1]]);
    if (p[2]) pts.push([p[0], p[1]]); // duplicate => zero tangent => sharp corner
  }
  const n = pts.length;
  const at = (i: number) => pts[(i + n) % n];
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < n; i++) {
    const [p0, p1, p2, p3] = [at(i - 1), at(i), at(i + 1), at(i + 2)];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0].toFixed(1)},${c1[1].toFixed(1)} ${c2[0].toFixed(1)},${c2[1].toFixed(1)} ${p2[0]},${p2[1]}`;
  }
  return d + " Z";
}

/** Left half from the top of the head (on the axis) down to the crotch (on the axis); mirrored for the right. */
function mirrored(left: P[]): string {
  const right = left
    .slice(1, -1)
    .reverse()
    .map((p) => [200 - p[0], p[1], ...(p[2] ? [1] : [])] as P);
  return smooth([...left, ...right]);
}

export type Landmarks = {
  neckTop: number; // bottom of the chin
  chestTop: number; // base of the neck / shoulders
  armpit: [number, number];
  innerWrist: [number, number];
  handBottom: number;
  upperAbdTop: number; // under the chest
  lowerAbdTop: number; // navel line
  pelvisTop: number;
  legLine: number; // outer hip where the leg begins
  crotch: number;
  ankle: number;
  backSplit: number; // upper back / lower back boundary
};

export type Body = { outline: string; lm: Landmarks };

// ---------------- adult male ----------------
const MALE: P[] = [
  [100, 10], [89, 12], [81, 19], [77, 29], [74, 33], [73, 39], [75, 45], [78, 47], [80, 53], [85, 60], [91, 65],
  [92, 70], [91, 77], [84, 81], [72, 85], [62, 88],
  [55, 93], [51, 103], [50, 116], [48, 136], [45, 156], [43, 170], [40, 192], [37, 213], [35, 228],
  [32, 236], [29, 248], [29, 258], [32, 266], [36, 270], [40, 268], [43, 260], [44, 250], [45, 240],
  [47, 231], [50, 210], [53, 190], [55, 173], [58, 153], [61, 133], [64, 118, 1],
  [66, 131], [68, 152], [71, 174], [71, 192], [69, 210], [66, 226],
  [65, 246], [66, 272], [69, 300], [72, 326], [71, 347], [72, 372], [75, 396], [77, 412],
  [76, 422], [71, 432], [70, 440], [76, 445], [88, 445], [95, 441], [96, 431], [94, 420],
  [93, 400], [92, 376], [91, 352], [92, 331], [94, 306], [96, 285], [98, 270], [100, 263, 1],
];

// ---------------- adult female ----------------
const FEMALE: P[] = [
  [100, 12], [90, 14], [82, 21], [78, 31], [75, 35], [74.5, 40], [76, 45], [79, 47], [81, 53], [86, 60], [92, 65],
  [93, 70], [92, 77], [85, 81], [75, 85], [66, 89],
  [59, 94], [56, 104], [55, 116], [53, 136], [50, 156], [48, 170], [45, 192], [42, 212], [40, 227],
  [37, 235], [34, 247], [34, 257], [37, 265], [41, 269], [45, 267], [48, 259], [49, 249], [50, 239],
  [52, 230], [55, 209], [58, 189], [60, 172], [63, 152], [65, 133], [68, 119, 1],
  [68, 128], [68, 142], [71, 158], [75, 172], [74, 188], [69, 204], [63, 220], [61, 236],
  [61, 252], [63, 277], [67, 304], [71, 328], [71, 348], [72, 372], [75, 396], [77, 412],
  [76, 422], [72, 431], [71, 439], [77, 444], [88, 444], [94, 440], [95, 431], [94, 420],
  [93, 400], [92, 376], [91, 352], [92, 332], [94, 307], [96, 285], [98, 268], [100, 260, 1],
];

// Pregnant (~third trimester): fuller bust, belly bump wider than the waist in front view.
const PREGNANT: P[] = FEMALE.map((p) => [...p] as P);
PREGNANT.splice(
  PREGNANT.findIndex((p) => p[0] === 68 && p[1] === 128),
  8,
  [67, 128], [66, 140], [63, 152], [59, 166], [56, 182], [55, 198], [57, 213], [61, 226], [61, 238],
);

// ---------------- child (about 5 years): big head, short limbs ----------------
const CHILD: P[] = [
  [100, 18], [87, 20], [77, 28], [72, 41], [70, 46], [69.5, 52], [71, 58], [73, 60], [76, 68], [83, 76], [92, 81],
  [93, 86], [92, 92], [85, 96], [76, 99], [68, 102],
  [62, 107], [59, 117], [58, 128], [56, 146], [54, 162], [53, 172], [51, 190], [49, 208], [48, 220],
  [45, 227], [43, 237], [43, 246], [46, 252], [50, 254], [54, 251], [56, 244], [57, 236], [57, 228],
  [58, 220], [60, 202], [62, 186], [63, 175], [65, 158], [67, 142], [69, 131, 1],
  [70, 145], [70, 165], [70, 188], [70, 208], [69, 226],
  [68, 246], [69, 272], [72, 300], [73, 322], [74, 350], [76, 380], [78, 400],
  [77, 408], [73, 416], [72, 423], [78, 427], [89, 427], [95, 423], [96, 414], [94, 404],
  [93, 384], [92, 356], [92, 328], [93, 303], [95, 283], [98, 268], [100, 263, 1],
];

const LANDMARKS: Record<BodyType, Landmarks> = {
  male: {
    neckTop: 64, chestTop: 80, armpit: [64, 118], innerWrist: [47, 231], handBottom: 271, upperAbdTop: 148,
    lowerAbdTop: 186, pelvisTop: 222, legLine: 248, crotch: 263, ankle: 414, backSplit: 172,
  },
  female: {
    neckTop: 64, chestTop: 80, armpit: [68, 119], innerWrist: [52, 230], handBottom: 270, upperAbdTop: 150,
    lowerAbdTop: 186, pelvisTop: 218, legLine: 246, crotch: 260, ankle: 414, backSplit: 172,
  },
  pregnant: {
    neckTop: 64, chestTop: 80, armpit: [67, 119], innerWrist: [52, 230], handBottom: 270, upperAbdTop: 150,
    lowerAbdTop: 190, pelvisTop: 224, legLine: 246, crotch: 260, ankle: 414, backSplit: 172,
  },
  adult: {
    neckTop: 64, chestTop: 80, armpit: [64, 118], innerWrist: [47, 231], handBottom: 271, upperAbdTop: 148,
    lowerAbdTop: 186, pelvisTop: 222, legLine: 248, crotch: 263, ankle: 414, backSplit: 172,
  },
  child: {
    neckTop: 80, chestTop: 94, armpit: [69, 131], innerWrist: [58, 220], handBottom: 255, upperAbdTop: 158,
    lowerAbdTop: 192, pelvisTop: 224, legLine: 246, crotch: 263, ankle: 402, backSplit: 180,
  },
};

const OUTLINES: Record<BodyType, P[]> = { male: MALE, female: FEMALE, pregnant: PREGNANT, child: CHILD, adult: MALE };

const cache = new Map<BodyType, Body>();
export function body(type: BodyType): Body {
  let b = cache.get(type);
  if (!b) {
    b = { outline: mirrored(OUTLINES[type]), lm: LANDMARKS[type] };
    cache.set(type, b);
  }
  return b;
}

/** Which figure to show for the patient context gathered so far. */
export function bodyFor(ctx: { age_group?: string; sex?: string; pregnant?: boolean }): BodyType {
  if (ctx.pregnant) return "pregnant";
  if (ctx.age_group === "under5" || ctx.age_group === "child") return "child";
  if (ctx.sex === "female") return "female";
  return ctx.sex === "male" ? "male" : "adult";
}
