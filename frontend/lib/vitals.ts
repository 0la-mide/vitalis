export const VITAL_FIELDS = [
  { kind: "systolic_bp", label: "BP systolic", short: "SBP", unit: "mmHg", step: "1" },
  { kind: "diastolic_bp", label: "BP diastolic", short: "DBP", unit: "mmHg", step: "1" },
  { kind: "pulse", label: "Pulse", short: "Pulse", unit: "bpm", step: "1" },
  { kind: "temp_c", label: "Temperature", short: "Temp", unit: "°C", step: "0.1" },
  { kind: "spo2", label: "SpO₂", short: "SpO₂", unit: "%", step: "1" },
  { kind: "resp_rate", label: "Resp. rate", short: "RR", unit: "/min", step: "1" },
  { kind: "weight_kg", label: "Weight", short: "Wt", unit: "kg", step: "0.1" },
  { kind: "height_cm", label: "Height", short: "Ht", unit: "cm", step: "1" },
  { kind: "blood_glucose", label: "Blood glucose", short: "Glu", unit: "mg/dL", step: "1" },
] as const;

export type VitalKind = (typeof VITAL_FIELDS)[number]["kind"];

export const vitalLabel = (kind: string) => VITAL_FIELDS.find((f) => f.kind === kind)?.label ?? kind;
