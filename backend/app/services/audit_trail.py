import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.audit_trail import ActivityLog


GENESIS_HASH = "0" * 64


def canonical_json(data: Any) -> str:
    """Produces deterministic, sorted, whitespace-minimized JSON."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def format_canonical_timestamp(dt: datetime) -> str:
    """Returns a deterministic ISO-8601 UTC timestamp string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def compute_entry_hash(
    prev_hash: str,
    sequence_id: int,
    timestamp_iso: str,
    actor_id: Optional[str],
    action: str,
    entity_type: str,
    entity_id: str,
    payload_json: str,
) -> str:
    """
    Computes SHA-256 hash across the immutable fields of the audit log entry.
    """
    actor_str = str(actor_id or "system")
    raw_content = f"{prev_hash}|{sequence_id}|{timestamp_iso}|{actor_str}|{action}|{entity_type}|{entity_id}|{payload_json}"
    return hashlib.sha256(raw_content.encode("utf-8")).hexdigest()


def log_activity(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_id: Optional[str] = None,
    actor_name: str = "System",
    case_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> ActivityLog:
    """
    Appends an immutable, hash-chained log entry to activity_logs.
    """
    payload_str = canonical_json(payload or {})
    now = datetime.now(timezone.utc)
    now_iso = format_canonical_timestamp(now)

    # Get the latest entry in the chain
    latest = (
        db.query(ActivityLog)
        .order_by(ActivityLog.sequence_id.desc())
        .first()
    )

    if latest:
        next_sequence = latest.sequence_id + 1
        prev_hash = latest.current_hash
    else:
        next_sequence = 1
        prev_hash = GENESIS_HASH

    current_hash = compute_entry_hash(
        prev_hash=prev_hash,
        sequence_id=next_sequence,
        timestamp_iso=now_iso,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=payload_str,
    )

    entry = ActivityLog(
        sequence_id=next_sequence,
        timestamp=now,
        actor_id=actor_id,
        actor_name=actor_name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        case_id=case_id,
        payload_json=payload_str,
        prev_hash=prev_hash,
        current_hash=current_hash,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def verify_hash_chain(db: Session) -> Dict[str, Any]:
    """
    Traverses the entire activity_logs table from genesis to verify cryptographic integrity.
    Reports the exact sequence_id where tampering or breakage occurred, if any.
    """
    records = db.query(ActivityLog).order_by(ActivityLog.sequence_id.asc()).all()

    if not records:
        return {
            "verified": True,
            "total_records": 0,
            "broken_at_sequence": None,
            "last_verified_at": datetime.now(timezone.utc).isoformat(),
            "message": "Audit chain is empty and valid.",
        }

    prev_hash_expected = GENESIS_HASH

    for idx, entry in enumerate(records):
        # 1. Verify sequence continuity
        expected_seq = idx + 1
        if entry.sequence_id != expected_seq:
            return {
                "verified": False,
                "total_records": len(records),
                "broken_at_sequence": entry.sequence_id,
                "error": f"Sequence discontinuity: expected {expected_seq}, found {entry.sequence_id}",
                "expected_hash": None,
                "actual_hash": entry.current_hash,
            }

        # 2. Verify prev_hash link
        if entry.prev_hash != prev_hash_expected:
            return {
                "verified": False,
                "total_records": len(records),
                "broken_at_sequence": entry.sequence_id,
                "error": "Chain linkage broken: prev_hash does not match previous record's current_hash",
                "expected_hash": prev_hash_expected,
                "actual_hash": entry.prev_hash,
            }

        # 3. Recompute content hash
        # Use deterministic ISO string format consistent with creation
        now_iso = format_canonical_timestamp(entry.timestamp)
        expected_hash = compute_entry_hash(
            prev_hash=entry.prev_hash,
            sequence_id=entry.sequence_id,
            timestamp_iso=now_iso,
            actor_id=entry.actor_id,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            payload_json=entry.payload_json,
        )

        if entry.current_hash != expected_hash:
            return {
                "verified": False,
                "total_records": len(records),
                "broken_at_sequence": entry.sequence_id,
                "error": "Hash mismatch: contents have been modified or tampered with",
                "expected_hash": expected_hash,
                "actual_hash": entry.current_hash,
            }

        prev_hash_expected = entry.current_hash

    return {
        "verified": True,
        "total_records": len(records),
        "broken_at_sequence": None,
        "last_verified_at": datetime.now(timezone.utc).isoformat(),
        "message": "Cryptographic audit trail is intact and verified.",
    }
