"""Facility matching. Pure functions over facility snapshots so it is easy to test.

score (0-100) = 40 service match + 25 availability now + 20 distance + 15 data freshness
Hard filter: a facility missing an essential service (not offered, or marked unavailable) is excluded.
`unknown` availability stays in, labelled, and scores lower.
"""

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.engines.triage.data import care_types
from app.models.enums import Availability

NEARBY_KM = 30.0
CONFIRMED_H = 6
STALE_H = 48
AVAIL_SCORE = {Availability.available: 1.0, Availability.limited: 0.5, Availability.unknown: 0.25}


@dataclass
class ServiceSnap:
    code: str
    status: str
    last_confirmed_at: datetime | None


@dataclass
class FacilitySnap:
    id: uuid.UUID
    name: str
    lga: str
    type: str
    lat: float
    lng: float
    phone: str | None
    services: dict[str, ServiceSnap]
    ready_alert: bool = False  # tapped "Ready" on a heads-up for this report


@dataclass
class Match:
    facility_id: uuid.UUID
    name: str
    lga: str
    type: str
    lat: float
    lng: float
    phone: str | None
    distance_km: float
    eta_minutes: int
    score: float
    freshness: str  # confirmed | stale | unknown
    last_confirmed_at: datetime | None
    ready_now: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Excluded:
    facility_id: uuid.UUID
    name: str
    distance_km: float
    reasons: list[str]


@dataclass
class MatchResult:
    care_type: str | None
    nearby: int
    can_handle: int
    ready_now: int
    matches: list[Match]
    excluded: list[Excluded]


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def freshness_of(ts: datetime | None, now: datetime) -> str:
    if ts is None:
        return "unknown"
    age = now - ts
    if age < timedelta(hours=CONFIRMED_H):
        return "confirmed"
    if age < timedelta(hours=STALE_H):
        return "stale"
    return "unknown"


FRESH_SCORE = {"confirmed": 1.0, "stale": 0.5, "unknown": 0.0}
FRESH_RANK = {"confirmed": 2, "stale": 1, "unknown": 0}


def _service_name(code: str) -> str:
    for s in care_types()["services"]:
        if s["code"] == code:
            return s["name"]
    return code


def match(
    facilities: list[FacilitySnap],
    care_type: str | None,
    lat: float,
    lng: float,
    now: datetime,
    speed_kmh: float = 25.0,
    limit: int = 5,
) -> MatchResult:
    cfg = care_types()["care_types"].get(care_type or "", {})
    essential: list[str] = cfg.get("essential", [])
    preferred: list[str] = cfg.get("preferred", [])

    nearby = 0
    matches: list[Match] = []
    excluded: list[Excluded] = []

    for f in facilities:
        dist = haversine_km(lat, lng, f.lat, f.lng)
        if dist > NEARBY_KM:
            continue
        nearby += 1

        missing = []
        for code in essential:
            svc = f.services.get(code)
            if svc is None:
                missing.append(f"No {_service_name(code).lower()}")
            elif svc.status == Availability.unavailable:
                missing.append(f"{_service_name(code)}: not available right now")
        if missing:
            excluded.append(Excluded(f.id, f.name, round(dist, 1), missing))
            continue

        reasons: list[str] = []
        warnings: list[str] = []
        ess = [f.services[c] for c in essential]

        # Service match: essentials present (unknown counts half) + preferred extras.
        if essential:
            ess_score = sum(0.5 if s.status == Availability.unknown else 1.0 for s in ess) / len(ess)
        else:
            ess_score = 1.0
        pref_have = [c for c in preferred if c in f.services and f.services[c].status != Availability.unavailable]
        pref_score = len(pref_have) / len(preferred) if preferred else 1.0
        service_match = 0.8 * ess_score + 0.2 * pref_score

        # Availability now.
        if f.ready_alert:
            avail = 1.0
        elif ess:
            avail = sum(AVAIL_SCORE.get(s.status, 0.25) for s in ess) / len(ess)
        else:
            known = [s for s in f.services.values()]
            avail = (
                sum(AVAIL_SCORE.get(s.status, 0.25) for s in known) / len(known) if known else 0.25
            )

        distance_score = max(0.0, 1 - dist / NEARBY_KM)

        stamps = [s.last_confirmed_at for s in (ess or list(f.services.values()))]
        labels = [freshness_of(t, now) for t in stamps] or ["unknown"]
        fresh_score = sum(FRESH_SCORE[x] for x in labels) / len(labels)
        worst = min(labels, key=lambda x: FRESH_RANK[x])
        known_stamps = [t for t in stamps if t is not None]
        oldest = min(known_stamps) if known_stamps else None

        score = round(100 * (0.40 * service_match + 0.25 * avail + 0.20 * distance_score + 0.15 * fresh_score), 1)

        if essential:
            reasons.append(f"Has {', '.join(_service_name(c).lower() for c in essential)}")
        if f.ready_alert:
            reasons.append("Said they are ready for this patient")
        elif ess and all(s.status == Availability.available for s in ess):
            reasons.append("All needed services marked available")
        for s in ess:
            if s.status == Availability.unknown:
                warnings.append(f"{_service_name(s.code)}: availability unknown")
            elif s.status == Availability.limited:
                warnings.append(f"{_service_name(s.code)}: limited")
        if worst == "stale":
            warnings.append("Availability not confirmed in the last 6 hours")
        elif worst == "unknown":
            warnings.append("Availability not confirmed recently")
        if pref_have:
            reasons.append(f"Also has {', '.join(_service_name(c).lower() for c in pref_have[:3])}")

        ready = f.ready_alert or (
            bool(ess)
            and all(s.status == Availability.available for s in ess)
            and worst == "confirmed"
        )
        matches.append(
            Match(
                facility_id=f.id,
                name=f.name,
                lga=f.lga,
                type=f.type,
                lat=f.lat,
                lng=f.lng,
                phone=f.phone,
                distance_km=round(dist, 1),
                eta_minutes=max(3, round(dist / speed_kmh * 60)),
                score=score,
                freshness=worst,
                last_confirmed_at=oldest,
                ready_now=ready,
                reasons=reasons,
                warnings=warnings,
            )
        )

    matches.sort(key=lambda m: (-m.score, m.distance_km))
    excluded.sort(key=lambda e: e.distance_km)
    return MatchResult(
        care_type=care_type,
        nearby=nearby,
        can_handle=len(matches),
        ready_now=sum(1 for m in matches if m.ready_now),
        matches=matches[:limit],
        excluded=excluded,
    )
