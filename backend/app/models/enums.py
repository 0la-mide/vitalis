from enum import StrEnum


class Role(StrEnum):
    network_admin = "network_admin"
    facility_admin = "facility_admin"
    receptionist = "receptionist"
    nurse = "nurse"
    doctor = "doctor"
    lab = "lab"
    radiology = "radiology"
    worker = "worker"  # frontline: chemist/PPMV, pharmacist, CHEW, midwife


HOSPITAL_ROLES = {Role.facility_admin, Role.receptionist, Role.nurse, Role.doctor, Role.lab, Role.radiology}


class VerificationStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    suspended = "suspended"


class WorkerType(StrEnum):
    chemist = "chemist"  # PPMV
    pharmacist = "pharmacist"
    chew = "chew"
    midwife = "midwife"


class Availability(StrEnum):
    available = "available"
    limited = "limited"
    unavailable = "unavailable"
    unknown = "unknown"


class ActionLevel(StrEnum):
    go_now = "go_now"
    go_today = "go_today"
    see_chemist = "see_chemist"
    self_care = "self_care"


class TriageStatus(StrEnum):
    open = "open"
    emergency = "emergency"
    completed = "completed"
    referred = "referred"


class ReferralStatus(StrEnum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    more_info = "more_info"
    cancelled = "cancelled"
    arrived = "arrived"
    overdue = "overdue"
    completed = "completed"


REFERRAL_TRANSITIONS: dict[ReferralStatus, set[ReferralStatus]] = {
    ReferralStatus.pending: {
        ReferralStatus.accepted,
        ReferralStatus.declined,
        ReferralStatus.more_info,
        ReferralStatus.cancelled,
    },
    ReferralStatus.more_info: {
        ReferralStatus.accepted,
        ReferralStatus.declined,
        ReferralStatus.cancelled,
    },
    ReferralStatus.accepted: {ReferralStatus.arrived, ReferralStatus.overdue, ReferralStatus.cancelled},
    ReferralStatus.overdue: {ReferralStatus.arrived, ReferralStatus.cancelled},
    ReferralStatus.arrived: {ReferralStatus.completed},
    ReferralStatus.declined: set(),
    ReferralStatus.cancelled: set(),
    ReferralStatus.completed: set(),
}


class AlertStatus(StrEnum):
    sent = "sent"
    ready = "ready"
    dismissed = "dismissed"


class EncounterState(StrEnum):
    registered = "registered"
    awaiting_nursing = "awaiting_nursing"
    awaiting_doctor = "awaiting_doctor"
    awaiting_investigation = "awaiting_investigation"
    results_ready = "results_ready"
    awaiting_disposition = "awaiting_disposition"
    completed = "completed"
    cancelled = "cancelled"


ES = EncounterState
# Allowed manual transitions and the roles that may perform them. Order/result-driven moves
# (awaiting_doctor -> awaiting_investigation -> results_ready) happen automatically.
ENCOUNTER_TRANSITIONS: dict[tuple[str, str], set[str]] = {
    (ES.registered, ES.awaiting_nursing): {"receptionist", "nurse", "facility_admin"},
    (ES.registered, ES.awaiting_doctor): {"receptionist", "nurse", "doctor", "facility_admin"},
    (ES.awaiting_nursing, ES.awaiting_doctor): {"nurse", "facility_admin"},
    (ES.awaiting_doctor, ES.awaiting_disposition): {"doctor"},
    (ES.results_ready, ES.awaiting_disposition): {"doctor"},
    (ES.results_ready, ES.awaiting_doctor): {"doctor", "nurse"},
    (ES.awaiting_disposition, ES.completed): {"receptionist", "nurse", "doctor", "facility_admin"},
}
CANCELLABLE = {ES.registered, ES.awaiting_nursing, ES.awaiting_doctor, ES.awaiting_investigation, ES.results_ready,
               ES.awaiting_disposition}
CANCEL_ROLES = {"receptionist", "doctor", "facility_admin"}
