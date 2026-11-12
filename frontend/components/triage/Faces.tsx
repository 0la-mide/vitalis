"use client";

/** Original 5-step "how bad" faces for VITALIS: calm to crying. Not based on any published pain scale. */

const TONES = ["#2f9e6f", "#7bb662", "#e0b23a", "#e07b39", "#c8442f"];

function mouth(level: number) {
  // smile -> flat -> frown, deeper with level
  const curves = ["M38,64 Q50,76 62,64", "M38,66 Q50,72 62,66", "M38,68 L62,68", "M38,72 Q50,62 62,72", "M36,74 Q50,58 64,74"];
  return curves[level - 1];
}

export function Face({ level, size = 72 }: { level: number; size?: number }) {
  const tone = TONES[level - 1];
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden>
      <circle cx="50" cy="50" r="44" fill={tone} opacity="0.18" />
      <circle cx="50" cy="50" r="44" fill="none" stroke={tone} strokeWidth="5" />
      {level >= 4 ? (
        <g stroke={tone} strokeWidth="5" strokeLinecap="round">
          <path d="M30,38 L42,44" />
          <path d="M70,38 L58,44" />
        </g>
      ) : (
        <g fill={tone}>
          <circle cx="36" cy="42" r="5" />
          <circle cx="64" cy="42" r="5" />
        </g>
      )}
      <path d={mouth(level)} fill="none" stroke={tone} strokeWidth="5" strokeLinecap="round" />
      {level === 5 && (
        <g fill="#4aa3df">
          <path d="M30,52 q-4,8 0,12 q4,-4 0,-12z" />
          <path d="M70,52 q-4,8 0,12 q4,-4 0,-12z" />
        </g>
      )}
    </svg>
  );
}
