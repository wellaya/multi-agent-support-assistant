from app.safety.store import SafetyStore


def _store() -> SafetyStore:
    return SafetyStore(":memory:")


def test_log_and_list_audit():
    store = _store()
    store.log_audit(
        message="I forgot my password",
        category="password_reset",
        sentiment="neutral",
        action="respond",
        input_flagged=False,
        output_flagged=False,
        flag_reasons=[],
    )

    entries = store.list_audit()

    assert len(entries) == 1
    assert entries[0]["message"] == "I forgot my password"
    assert entries[0]["action"] == "respond"
    assert entries[0]["input_flagged"] == 0


def test_list_audit_respects_limit_and_order():
    store = _store()
    for i in range(3):
        store.log_audit(
            message=f"message {i}",
            category="other",
            sentiment="neutral",
            action="ticket",
            input_flagged=False,
            output_flagged=False,
            flag_reasons=[],
        )

    entries = store.list_audit(limit=2)

    assert len(entries) == 2
    assert entries[0]["message"] == "message 2"


def test_enqueue_and_list_pending_approvals():
    store = _store()
    approval_id = store.enqueue_approval(
        message="This is outrageous!",
        draft_response="Draft reply",
        category="billing",
        action="escalate",
    )

    pending = store.list_pending_approvals()

    assert len(pending) == 1
    assert pending[0]["id"] == approval_id
    assert pending[0]["status"] == "pending"


def test_decide_approval_removes_it_from_pending():
    store = _store()
    approval_id = store.enqueue_approval(
        message="msg", draft_response="draft", category="other", action="ticket"
    )

    decided = store.decide_approval(approval_id, approved=True, note="looks fine")

    assert decided["status"] == "approved"
    assert decided["reviewer_note"] == "looks fine"
    assert store.list_pending_approvals() == []


def test_decide_unknown_approval_returns_none():
    store = _store()
    assert store.decide_approval(999, approved=False) is None
