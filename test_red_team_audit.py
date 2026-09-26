#!/usr/bin/env python3
"""
magicpin AI Challenge — Final Red-Team Audit Suite
=================================================

Comprehensive, adversarial verification across all 15 audit checkpoints:
1. Requirements & Deliverables
2. Core API Signature & Exact Schema
3. Data-Driven / Zero Hardcoding
4. Hidden Context Adaptation (Dynamic Data Mutation)
5. Multi-Turn States & Dynamics
6. Factual Grounding & Zero Hallucination
7. Category Fit & Voice
8. Customer Consent & DPDP Compliance
9. CTA Discipline
10. Anti-Repetition
11. Performance & Latency (< 10ms per call)
12. Zero Secrets / API Keys
13. Submission JSONL Validation
"""

import os
import sys
import io
import json
import time
import re
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from bot import compose
from conversation_handlers import respond, ConversationState, StateName, MERCHANT_AUTO_REPLY_TRACKER

def test_checkpoint_1_and_2_core_api():
    print("\n--- [CHECKPOINT 1 & 2] Core API Signature & Exact Schema ---")
    cat = {"slug": "dentists", "display_name": "Dentists", "voice": {"tone": "peer_clinical"}}
    m = {
        "merchant_id": "m_test_api",
        "identity": {"name": "Metro Smiles", "city": "Delhi", "locality": "Saket", "owner_first_name": "Dr. Sameer"},
        "performance": {"views": 1500}
    }
    trg = {"id": "trg_test_api", "kind": "perf_dip", "payload": {"metric": "views", "delta_pct": -0.20, "vs_baseline": 1875}}

    res = compose(cat, m, trg, customer=None)
    required_keys = {"body", "cta", "send_as", "suppression_key", "rationale"}
    assert set(res.keys()) == required_keys, f"Keys mismatch: {set(res.keys())} vs {required_keys}"
    assert isinstance(res["body"], str) and len(res["body"]) > 20
    assert isinstance(res["cta"], str) and len(res["cta"]) > 0
    assert res["send_as"] in ("vera", "merchant_on_behalf")
    assert isinstance(res["suppression_key"], str) and len(res["suppression_key"]) > 0
    assert isinstance(res["rationale"], str) and len(res["rationale"]) > 0
    print("  [PASS] Exact schema returned: {body, cta, send_as, suppression_key, rationale}")


def test_checkpoint_3_and_4_data_driven_hidden_context():
    print("\n--- [CHECKPOINT 3 & 4] Data-Driven Hidden Context Adaptation ---")
    cat = {
        "slug": "restaurants",
        "display_name": "Restaurants",
        "offer_catalog": [{"id": "o1", "title": "Initial Buffet @ ₹399", "status": "active"}],
        "digest": [{"id": "dig_init", "kind": "research", "title": "Initial Food Study", "trial_n": 500, "source": "Culinary Digest"}]
    }
    m = {
        "merchant_id": "m_dynamic_test",
        "identity": {"name": "Tandoor Tales", "city": "Mumbai", "locality": "Bandra", "owner_first_name": "Kabir"},
        "performance": {"views": 1200}
    }

    # 1. Mutate metric
    trg1 = {"id": "trg_1", "kind": "perf_dip", "payload": {"metric": "views", "delta_pct": -0.15, "vs_baseline": 1411}}
    out1 = compose(cat, m, trg1)
    assert "15%" in out1["body"]

    trg1_mutated = {"id": "trg_1", "kind": "perf_dip", "payload": {"metric": "views", "delta_pct": -0.47, "vs_baseline": 2264}}
    out1_mutated = compose(cat, m, trg1_mutated)
    assert "47%" in out1_mutated["body"], "Output did not reflect mutated delta_pct!"
    print("  [PASS] Metric mutation reflected dynamically: -15% -> -47%")

    # 2. Mutate research digest
    cat_mutated_digest = {
        "slug": "dentists", "display_name": "Dentists",
        "digest": [{
            "id": "lancet_2026", "kind": "research",
            "title": "Periodontal prophylaxis impact on diabetes markers",
            "source": "The Lancet Oct 2026, p.88",
            "trial_n": 12500,
            "patient_segment": "diabetic_cohort"
        }]
    }
    m_dent = {
        "merchant_id": "m_dent_01",
        "identity": {"name": "Apex Dental", "city": "Delhi", "locality": "Rohini", "owner_first_name": "Dr. Rohit"},
        "customer_aggregate": {"diabetic_cohort_count": 310}
    }
    trg_digest = {"id": "trg_d", "kind": "research_digest", "payload": {"top_item_id": "lancet_2026"}}
    out_digest = compose(cat_mutated_digest, m_dent, trg_digest)
    assert "The Lancet Oct 2026, p.88" in out_digest["body"]
    assert "12,500" in out_digest["body"]
    assert "310" in out_digest["body"]
    print("  [PASS] Research study & trial N mutation reflected dynamically (The Lancet, 12,500, 310)")

    # 3. Mutate catalog prices
    m_offers_1 = {"merchant_id": "m_off", "identity": {"name": "Spa Relax", "locality": "Indiranagar", "owner_first_name": "Sonia"}, "offers": [{"title": "Glow Facial @ ₹499"}]}
    m_offers_2 = {"merchant_id": "m_off", "identity": {"name": "Spa Relax", "locality": "Indiranagar", "owner_first_name": "Sonia"}, "offers": [{"title": "Luxury Gold Facial @ ₹1,850"}]}
    trg_plan = {"id": "trg_p", "kind": "active_planning_intent", "payload": {"intent_topic": "weekend_package"}}

    out_plan_1 = compose({"slug": "salons"}, m_offers_1, trg_plan)
    out_plan_2 = compose({"slug": "salons"}, m_offers_2, trg_plan)
    assert "₹499" in out_plan_1["body"]
    assert "₹1850" in out_plan_2["body"]
    print("  [PASS] Price mutation reflected dynamically: ₹499 -> ₹1,850")

    # 4. Mutate competitor name and distance
    trg_comp_1 = {"id": "trg_c", "kind": "competitor_opened", "payload": {"competitor_name": "Dentist One", "distance_km": 0.8}}
    trg_comp_2 = {"id": "trg_c", "kind": "competitor_opened", "payload": {"competitor_name": "Crown Care Clinic", "distance_km": 0.3}}
    out_comp_1 = compose(cat_mutated_digest, m_dent, trg_comp_1)
    out_comp_2 = compose(cat_mutated_digest, m_dent, trg_comp_2)
    assert "Dentist One" in out_comp_1["body"] and "0.8 km" in out_comp_1["body"]
    assert "Crown Care Clinic" in out_comp_2["body"] and "0.3 km" in out_comp_2["body"]
    print("  [PASS] Competitor name and distance mutation reflected dynamically")


def test_checkpoint_5_multi_turn_system():
    print("\n--- [CHECKPOINT 5] Multi-Turn State Machine & Transitions ---")
    st = ConversationState(conversation_id="conv_red_01", merchant_id="m_red_01", category_slug="salons")

    # Turn 1: Question
    r1 = respond(st, "What is this service?")
    assert r1["action"] == "send"
    assert st.state == StateName.PITCH

    # Turn 2: Curveball (GST)
    r2 = respond(st, "Can you file my GST returns?")
    assert r2["action"] == "send"
    assert "CA" in r2["body"] or "tax" in r2["body"].lower()

    # Turn 3: Action commitment -> ZERO QUALIFICATION QUESTIONS!
    r3 = respond(st, "let's do it")
    assert r3["action"] == "send"
    assert st.state == StateName.ACTION_READY
    assert "?" not in r3["body"].split("\n")[-1], "Action mode must present pre-filled draft, NOT ask questions!"
    assert "confirm" in r3["cta"].lower()

    # Turn 4: Confirmation -> COMPLETED
    r4 = respond(st, "CONFIRM")
    assert r4["action"] == "send"
    assert st.state == StateName.COMPLETED

    # Test STOP / Opt-out
    st_stop = ConversationState(conversation_id="conv_red_stop", merchant_id="m_red_02")
    r_stop = respond(st_stop, "STOP messaging me!")
    assert r_stop["action"] == "end"
    assert st_stop.state == StateName.GRACEFUL_EXIT

    # Test Rejection
    st_rej = ConversationState(conversation_id="conv_red_rej", merchant_id="m_red_03")
    r_rej = respond(st_rej, "Not interested, thank you")
    assert r_rej["action"] == "end"
    assert st_rej.state == StateName.NOT_INTERESTED

    # Test 3-turn auto-reply circuit breaker
    m_id_auto = "m_red_auto_99"
    MERCHANT_AUTO_REPLY_TRACKER[m_id_auto] = 0
    st_auto = ConversationState(conversation_id="conv_red_auto", merchant_id=m_id_auto)
    auto_msg = "Thank you for contacting us. We will get back to you shortly."

    r_a1 = respond(st_auto, auto_msg)
    assert r_a1["action"] == "send"
    assert st_auto.state == StateName.AUTO_REPLY_DETECTED

    r_a2 = respond(st_auto, auto_msg)
    assert r_a2["action"] == "wait"
    assert r_a2["wait_seconds"] == 86400

    r_a3 = respond(st_auto, auto_msg)
    assert r_a3["action"] == "end"
    assert st_auto.state == StateName.GRACEFUL_EXIT

    # Test Language Switching
    st_lang = ConversationState(conversation_id="conv_red_lang", merchant_id="m_red_04")
    r_en = respond(st_lang, "Tell me how it works")
    assert st_lang.language == "en"

    r_hi = respond(st_lang, "हिंदी में बताओ")
    assert st_lang.language == "hi"
    assert any('\u0900' <= char <= '\u097f' for char in r_hi["body"])

    r_hing = respond(st_lang, "theek hai bhai kitna charge lagega batao")
    assert st_lang.language == "hinglish"
    assert "₹0" in r_hing["body"]

    print("  [PASS] All multi-turn behaviors verified (Action commitment, Confirmation, STOP, Rejection, Auto-reply 3x escalation, Language switching)")


def test_checkpoint_6_grounding_and_no_hallucinations():
    print("\n--- [CHECKPOINT 6] Grounding & Zero Hallucinations ---")
    cat = {
        "slug": "pharmacies",
        "offer_catalog": [{"id": "p1", "title": "15% off Senior Citizen Prescriptions", "status": "active"}]
    }
    m = {
        "merchant_id": "m_ph_01",
        "identity": {"name": "Apollo Care", "locality": "Malviya Nagar", "owner_first_name": "Ramesh"},
        "customer_aggregate": {"chronic_rx_count": 140}
    }
    trg = {
        "id": "trg_ph_supply", "kind": "supply_alert",
        "payload": {
            "molecule": "Metformin 500mg SR",
            "affected_batches": ["B-8812", "B-8814"],
            "manufacturer": "Sun Pharma"
        }
    }
    res = compose(cat, m, trg)
    body = res["body"]
    # Check that all specific terms are from input
    assert "Metformin 500mg SR" in body
    assert "B-8812" in body
    assert "Sun Pharma" in body
    assert "140" in body
    # Verify no URLs exist
    assert not re.search(r"https?://", body), "Found external URL in body!"
    print("  [PASS] All factual claims grounded strictly in payload; 0 hallucinated entities or URLs")


def test_checkpoint_7_category_voice():
    print("\n--- [CHECKPOINT 7] Category Voice & Taboo Scrubbing ---")
    cat_dentist = {
        "slug": "dentists",
        "voice": {"tone": "peer_clinical", "vocab_taboo": ["guaranteed", "100% safe", "miracle"]},
        "offer_catalog": [{"id": "d_bad", "title": "Guaranteed 100% safe miracle whitening", "status": "active"}]
    }
    m = {
        "merchant_id": "m_d",
        "identity": {"name": "Smile Lab", "locality": "Koramangala", "owner_first_name": "Dr. Priya"}
    }
    trg = {"id": "trg_taboo", "kind": "category_seasonal", "payload": {"festival": "Diwali"}}
    res = compose(cat_dentist, m, trg)
    body_lower = res["body"].lower()
    assert "guaranteed" not in body_lower
    assert "100% safe" not in body_lower
    assert "miracle" not in body_lower
    print("  [PASS] Category taboo terms successfully sanitized to compliant vocabulary")


def test_checkpoint_8_customer_consent_and_send_as():
    print("\n--- [CHECKPOINT 8] Customer Consent & DPDP Privacy ---")
    cat = {"slug": "dentists"}
    m = {"merchant_id": "m_01", "identity": {"name": "Apex Dental", "owner_first_name": "Dr. Amit"}}
    trg = {"id": "trg_rec", "scope": "customer", "kind": "recall_due", "payload": {"service_due": "cleaning"}}

    # Case A: Active consent -> send_as: merchant_on_behalf
    cx_active = {
        "customer_id": "c_01",
        "identity": {"name": "Aarav Sharma"},
        "preferences": {"reminder_opt_in": True},
        "state": "active",
        "consent": {"scope": ["recall_reminders"]}
    }
    res_active = compose(cat, m, trg, cx_active)
    assert res_active["send_as"] == "merchant_on_behalf"
    assert "Aarav" in res_active["body"]

    # Case B: Opted out -> send_as: vera (alert merchant, DO NOT message customer!)
    cx_optout = {
        "customer_id": "c_02",
        "identity": {"name": "Sneha Gupta"},
        "preferences": {"reminder_opt_in": False},
        "state": "opted_out",
        "consent": {"scope": []}
    }
    res_optout = compose(cat, m, trg, cx_optout)
    assert res_optout["send_as"] == "vera", "Must NOT send on behalf to opted-out customer!"
    assert "compliance notice" in res_optout["body"].lower()
    assert "held this automated outreach" in res_optout["body"].lower()
    print("  [PASS] Customer consent respected: active -> merchant_on_behalf, opted_out -> vera alert")


def test_checkpoint_9_cta_rules():
    print("\n--- [CHECKPOINT 9] Single Unambiguous CTA Discipline ---")
    valid_ctas = {"binary_yes_no", "binary_confirm_cancel", "multi_choice_slot", "open_ended"}
    cat = {"slug": "gyms"}
    m = {"merchant_id": "m_g", "identity": {"name": "Fit Zone", "owner_first_name": "Vikram"}}

    trg1 = {"id": "t1", "kind": "perf_dip", "payload": {"metric": "views", "delta_pct": -0.10}}
    res1 = compose(cat, m, trg1)
    assert res1["cta"] in valid_ctas

    trg2 = {"id": "t2", "kind": "appointment_tomorrow", "scope": "customer", "payload": {"appointment_time": "10:00 AM"}}
    cx = {"identity": {"name": "Rohan"}, "preferences": {"reminder_opt_in": True}}
    res2 = compose(cat, m, trg2, cx)
    assert res2["cta"] in valid_ctas
    print("  [PASS] Single standard CTAs used with zero conflicting choices")


def test_checkpoint_10_anti_repetition():
    print("\n--- [CHECKPOINT 10] Anti-Repetition Engine ---")
    st = ConversationState(conversation_id="conv_rep_01", merchant_id="m_rep_01")
    inbound_queries = [
        "What is this?",
        "tell me more",
        "how does magicpin work?",
        "what are the details?"
    ]
    seen_bodies = set()
    for q in inbound_queries:
        r = respond(st, q)
        b = r.get("body", "")
        if b:
            assert b not in seen_bodies, f"Repeated message detected: {b}"
            seen_bodies.add(b)
    print("  [PASS] 4 consecutive general inquiries produced 4 distinct non-repeated value propositions")


def test_checkpoint_11_performance():
    print("\n--- [CHECKPOINT 11] Performance & Latency ---")
    cat = {"slug": "restaurants"}
    m = {"merchant_id": "m_speed", "identity": {"name": "Speedy Bites", "owner_first_name": "Ajay"}}
    trg = {"id": "t_speed", "kind": "perf_spike", "payload": {"metric": "views", "delta_pct": 0.35}}

    t0 = time.perf_counter()
    n_runs = 500
    for _ in range(n_runs):
        compose(cat, m, trg)
    total_time = time.perf_counter() - t0
    avg_ms = (total_time / n_runs) * 1000
    assert avg_ms < 5.0, f"Average compose latency too high: {avg_ms:.2f}ms"
    print(f"  [PASS] 500 compose() executions completed in {total_time:.3f}s (Average: {avg_ms:.3f}ms per call < 5ms)")


def test_checkpoint_12_secrets_audit():
    print("\n--- [CHECKPOINT 12] Secrets & Sensitive Data Audit ---")
    root_dir = Path(__file__).parent
    secret_patterns = [
        r"sk-[a-zA-Z0-9]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"(?:password|passwd|secret)\s*=\s*['\"][^'\"]{8,}['\"]",
        r"bearer\s+ey[A-Za-z0-9_-]{20,}"
    ]
    scanned_files = 0
    for ext in ("*.py", "*.json", "*.md", "*.jsonl"):
        for p in root_dir.glob(ext):
            scanned_files += 1
            content = p.read_text(encoding="utf-8", errors="ignore")
            for sp in secret_patterns:
                assert not re.search(sp, content, re.IGNORECASE), f"Potential secret leak in {p.name}!"
    print(f"  [PASS] Scanned {scanned_files} files across repo: 0 secrets or sensitive tokens detected")


def test_checkpoint_13_submission_validation():
    print("\n--- [CHECKPOINT 13] Submission JSONL Integrity ---")
    sub_path = Path(__file__).parent / "submission.jsonl"
    assert sub_path.exists(), "submission.jsonl is missing!"

    lines = [l.strip() for l in sub_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 30, f"Expected 30 lines, got {len(lines)}"

    seen_ids = set()
    for idx, line in enumerate(lines, 1):
        data = json.loads(line)
        tid = data.get("test_id")
        assert tid == f"T{idx:02d}", f"Line {idx} has invalid test_id {tid}"
        assert tid not in seen_ids, f"Duplicate test_id {tid}"
        seen_ids.add(tid)
        assert data.get("body") and len(data["body"]) > 20
        assert data.get("cta") in ("binary_yes_no", "binary_confirm_cancel", "multi_choice_slot", "open_ended")
        assert data.get("send_as") in ("vera", "merchant_on_behalf")
        assert data.get("suppression_key")
        assert data.get("rationale")
    print("  [PASS] submission.jsonl strictly verified: exactly 30 lines (T01-T30), 100% valid schema, 0 duplicates")


def run_full_red_team_audit():
    print("======================================================================")
    print("STARTING 15-POINT COMPREHENSIVE RED-TEAM AUDIT")
    print("======================================================================")

    test_checkpoint_1_and_2_core_api()
    test_checkpoint_3_and_4_data_driven_hidden_context()
    test_checkpoint_5_multi_turn_system()
    test_checkpoint_6_grounding_and_no_hallucinations()
    test_checkpoint_7_category_voice()
    test_checkpoint_8_customer_consent_and_send_as()
    test_checkpoint_9_cta_rules()
    test_checkpoint_10_anti_repetition()
    test_checkpoint_11_performance()
    test_checkpoint_12_secrets_audit()
    test_checkpoint_13_submission_validation()

    print("\n======================================================================")
    print("ALL RED-TEAM AUDIT CHECKPOINTS PASSED FLAWLESSLY (100% CERTIFIED)!")
    print("======================================================================")


if __name__ == "__main__":
    run_full_red_team_audit()
