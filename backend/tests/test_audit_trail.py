import pytest
from app.models.audit_trail import ActivityLog
from app.services.audit_trail import log_activity, verify_hash_chain


def test_hash_chain_integrity(client, db_session, auth_tokens):
    # Verify starting state (seeded genesis)
    verify_res = verify_hash_chain(db_session)
    assert verify_res["verified"] is True
    initial_count = verify_res["total_records"]

    # Append sequential actions
    log_activity(
        db=db_session,
        action="test:action_1",
        entity_type="test_entity",
        entity_id="101",
        actor_name="Auditor Anand",
        payload={"step": 1},
    )
    log_activity(
        db=db_session,
        action="test:action_2",
        entity_type="test_entity",
        entity_id="102",
        actor_name="Auditor Anand",
        payload={"step": 2},
    )

    verify_after = verify_hash_chain(db_session)
    assert verify_after["verified"] is True
    assert verify_after["total_records"] == initial_count + 2

    # Verify via API endpoint
    hdr = {"Authorization": f"Bearer {auth_tokens['auditor']}"}
    api_res = client.get("/api/audit-trail/verify", headers=hdr)
    assert api_res.status_code == 200
    assert api_res.json()["verified"] is True


def test_tamper_detection(db_session):
    # Create entries to establish a chain
    entry1 = log_activity(
        db=db_session,
        action="fund:transfer",
        entity_type="voucher",
        entity_id="VOUCH-001",
        actor_name="System",
        payload={"amount": 500000},
    )
    entry2 = log_activity(
        db=db_session,
        action="fund:disburse",
        entity_type="voucher",
        entity_id="VOUCH-002",
        actor_name="System",
        payload={"amount": 250000},
    )

    # Tamper with entry1 directly via raw SQL to bypass SQLAlchemy application event guard
    db_session.execute(
        ActivityLog.__table__.update()
        .where(ActivityLog.id == entry1.id)
        .values(payload_json='{"amount":999999999}')
    )
    db_session.commit()

    # Verify that the verification function catches the tampering!
    tamper_result = verify_hash_chain(db_session)
    assert tamper_result["verified"] is False
    assert tamper_result["broken_at_sequence"] == entry1.sequence_id
    assert "Hash mismatch" in tamper_result["error"]


def test_immutability_guard(db_session):
    # 1. Test update guard
    entry1 = log_activity(
        db=db_session,
        action="security:event_1",
        entity_type="event",
        entity_id="SEC-01",
        payload={},
    )

    entry1.action = "tampered:action"
    with pytest.raises(ValueError, match="ActivityLog is strictly append-only: updates are prohibited."):
        db_session.flush()

    db_session.rollback()

    # 2. Test delete guard with fresh entry
    entry2 = log_activity(
        db=db_session,
        action="security:event_2",
        entity_type="event",
        entity_id="SEC-02",
        payload={},
    )

    db_session.delete(entry2)
    with pytest.raises(ValueError, match="ActivityLog is strictly append-only: deletions are prohibited."):
        db_session.flush()

    db_session.rollback()
