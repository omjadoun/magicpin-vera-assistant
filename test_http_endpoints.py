#!/usr/bin/env python3
"""
Test HTTP API Endpoints using Starlette/FastAPI TestClient
"""

import sys
import io
import json
from starlette.testclient import TestClient

# Configure utf-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from bot import app, STORE

client = TestClient(app)

def test_endpoints():
    print("Testing /v1/healthz...")
    resp = client.get("/v1/healthz")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert data["status"] == "ok"
    assert data["contexts_loaded"]["category"] >= 5
    print("  [PASS] /v1/healthz:", data)

    print("Testing /v1/metadata...")
    resp = client.get("/v1/metadata")
    assert resp.status_code == 200
    meta = resp.json()
    assert "team_name" in meta
    print("  [PASS] /v1/metadata:", meta["team_name"])

    print("Testing /v1/context push & idempotency...")
    push_body = {
        "scope": "category",
        "context_id": "dentists",
        "version": 1,
        "payload": STORE.get("category", "dentists"),
        "delivered_at": "2026-04-26T10:00:00Z"
    }
    # Version 1 is already in store from preload -> should return 409
    resp = client.post("/v1/context", json=push_body)
    assert resp.status_code == 409, f"Expected 409 for duplicate version, got {resp.status_code}"
    print("  [PASS] Idempotency check (409 stale_version)")

    # Bump version to 2 -> should return 200
    push_body["version"] = 2
    resp = client.post("/v1/context", json=push_body)
    assert resp.status_code == 200, f"Expected 200 for version bump, got {resp.status_code}"
    assert resp.json()["accepted"] is True
    print("  [PASS] Context version bump accepted (200)")

    print("Testing /v1/tick...")
    tick_body = {
        "now": "2026-04-26T10:30:00Z",
        "available_triggers": [
            "trg_001_research_digest_dentists",
            "trg_003_recall_due_priya",
            "trg_010_ipl_match_delhi"
        ]
    }
    resp = client.post("/v1/tick", json=tick_body)
    assert resp.status_code == 200
    tick_res = resp.json()
    assert len(tick_res["actions"]) == 3, f"Expected 3 actions, got {len(tick_res['actions'])}"
    for act in tick_res["actions"]:
        assert "conversation_id" in act
        assert "send_as" in act
        assert "body" in act
        assert "cta" in act
        assert "rationale" in act
        print(f"  [PASS] Tick action: trigger={act['trigger_id']}, send_as={act['send_as']}")

    print("Testing /v1/reply (auto-reply, intent transition, hostile)...")
    # Auto-reply test
    auto_body = {
        "conversation_id": "conv_replay_auto",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "from_role": "merchant",
        "message": "Thank you for contacting Dr. Meera's Dental Clinic! Our team will respond shortly.",
        "turn_number": 2
    }
    # Turn 1
    r1 = client.post("/v1/reply", json=auto_body).json()
    assert r1["action"] == "send"
    # Turn 2
    auto_body["turn_number"] = 3
    r2 = client.post("/v1/reply", json=auto_body).json()
    assert r2["action"] == "wait"
    # Turn 3
    auto_body["turn_number"] = 4
    r3 = client.post("/v1/reply", json=auto_body).json()
    assert r3["action"] == "end"
    print("  [PASS] Auto-reply multi-turn replay passed")

    # Intent transition test
    intent_body = {
        "conversation_id": "conv_replay_intent",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "from_role": "merchant",
        "message": "Ok lets do it. Whats next?",
        "turn_number": 2
    }
    r_intent = client.post("/v1/reply", json=intent_body).json()
    assert r_intent["action"] == "send"
    assert any(w in r_intent["body"].lower() for w in ["done", "sending", "draft", "here", "confirm", "proceed", "next"])
    assert not any(w in r_intent["body"].lower() for w in ["would you", "do you", "can you tell", "what if", "how about"])
    print("  [PASS] Intent transition to action mode passed")

    # Specific Live Test Case: Dr. Meera Dental Clinic -> "I want to join magicpin"
    join_body = {
        "conversation_id": "conv_drmeera_join",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "from_role": "merchant",
        "message": "I want to join magicpin",
        "turn_number": 2,
        "initial_message": "Dr. Meera, compliance update: Dental Council of India circular 2026-11-04 issued guidance regarding radiograph dose limits."
    }
    r_join = client.post("/v1/reply", json=join_body).json()
    assert r_join["action"] == "send"
    assert r_join["state"] == "ACTION_READY"
    assert r_join["intent"] == "join_onboarding"
    assert r_join["cta"] == "single_choice_confirm"
    
    join_text_lower = r_join["body"].lower()
    # Grounded onboarding assertions
    assert "₹0 upfront" in join_text_lower or "free" in join_text_lower
    assert "confirm" in join_text_lower
    # Strictly prohibited hallucinations
    assert "tomorrow 10:00 am" not in join_text_lower
    assert "10:00 am" not in join_text_lower
    assert "patients due for preventive checkup" not in join_text_lower
    assert "done! drafting your message and pre-filling" not in join_text_lower
    print("  [PASS] Dr. Meera 'I want to join magicpin' onboarding test passed")
    # Hostile test
    hostile_body = {
        "conversation_id": "conv_replay_hostile",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "from_role": "merchant",
        "message": "Stop messaging me. This is useless spam.",
        "turn_number": 2
    }
    r_hostile = client.post("/v1/reply", json=hostile_body).json()
    assert r_hostile["action"] == "end"
    print("  [PASS] Hostile stop passed")

    print("\nALL HTTP ENDPOINTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_endpoints()
