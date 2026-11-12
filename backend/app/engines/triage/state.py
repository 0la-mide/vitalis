"""Triage state: patient context + accumulated symptoms + vitals. Pure data, no I/O."""

from dataclasses import dataclass, field


@dataclass
class SymptomState:
    code: str
    region: str | None = None
    severity: int | None = None  # 1..5
    onset: str | None = None  # now | today | days | week


@dataclass
class TriageState:
    age_group: str = "adult"  # under5 | child | teen | adult | elderly
    sex: str = "unknown"
    pregnant: bool = False
    symptoms: list[SymptomState] = field(default_factory=list)
    vitals: dict[str, float] = field(default_factory=dict)
    regions: list[str] = field(default_factory=list)
    severity: int | None = None  # overall "how bad"
    onset: str | None = None  # overall "since when"

    @property
    def is_child(self) -> bool:
        return self.age_group in {"under5", "child"}

    def codes(self) -> set[str]:
        return {s.code for s in self.symptoms}

    def severity_of(self, code: str) -> int | None:
        for s in self.symptoms:
            if s.code == code:
                return s.severity or self.severity
        return None

    @classmethod
    def from_report(cls, context: dict, answers: dict, vitals: dict | None = None) -> "TriageState":
        syms = [
            SymptomState(
                code=s["code"],
                region=s.get("region"),
                severity=s.get("severity") or answers.get("severity"),
                onset=s.get("onset") or answers.get("onset"),
            )
            for s in answers.get("symptoms", [])
        ]
        return cls(
            age_group=context.get("age_group") or "adult",
            sex=context.get("sex") or "unknown",
            pregnant=bool(context.get("pregnant")),
            symptoms=syms,
            vitals=dict(vitals or {}),
            regions=list(answers.get("regions", [])),
            severity=answers.get("severity"),
            onset=answers.get("onset"),
        )
