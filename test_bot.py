#!/usr/bin/env python3
"""
Comprehensive Unit & Integration Test Suite for bot.py
"""

import sys
import io
import json
from pathlib import Path

# Configure utf-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from bot import compose, STORE, CONVERSATIONS, ConversationState, MultiTurnHandler

def test_compose_seed_data():
    print("Testing compose() across seed dataset triggers...")
    
    # Check that contexts are loaded in STORE
    counts = STORE.counts()
    print(f"STORE context counts: {counts}")
    assert counts["category"] >= 5, "Missing category contexts in store"
    assert counts["merchant"] >= 10, "Missing merchant contexts in store"
    assert counts["trigger"] >= 25, "Missing trigger contexts in store"

    categories = {}
    for cat_slug in ["dentists", "salons", "restaurants", "gyms", "pharmacies"]:
        cat = STORE.get("category", cat_slug)
        assert cat is not None, f"Category {cat_slug} not found in store"
        categories[cat_slug] = cat

    # Test each seed trigger
    for trg_id in [
        "trg_001_research_digest_dentists",
        "trg_002_compliance_dci_radiograph",
        "trg_003_recall_due_priya",
        "trg_004_perf_dip_bharat",
        "trg_005_renewal_due_bharat",
        "trg_006_festival_diwali",
        "trg_007_bridal_followup_kavya",
        "trg_008_curious_ask_studio11",
        "trg_009_winback_glamour",
        "trg_010_ipl_match_delhi",
        "trg_011_review_theme_late_delivery",
        "trg_012_milestone_mylari",
        "trg_013_corporate_thali_planning",
        "trg_014_seasonal_acquisition_dip_powerhouse",
        "trg_015_winback_rashmi",
        "trg_016_kids_yoga_program_drafting",
        "trg_017_kids_yoga_trial_followup_karthik",
        "trg_018_supply_atorvastatin_recall",
        "trg_019_chronic_refill_grandfather",
        "trg_020_summer_demand_shift",
        "trg_021_unverified_gbp_sunrise",
        "trg_022_cde_webinar_dentists",
        "trg_023_competitor_opened_dentist",
        "trg_024_perf_spike_zen",
        "trg_025_dormancy_glamour"
    ]:
        trigger = STORE.get("trigger", trg_id)
        assert trigger is not None, f"Trigger {trg_id} not found"
        
        merchant_id = trigger["merchant_id"]
        merchant = STORE.get("merchant", merchant_id)
        assert merchant is not None, f"Merchant {merchant_id} not found"
        
        cat_slug = merchant["category_slug"]
        category = categories[cat_slug]
        
        customer_id = trigger.get("customer_id")
        customer = STORE.get("customer", customer_id) if customer_id else None
        
        # Call compose()
        res = compose(category, merchant, trigger, customer)
        
        # Verify schema
        required_keys = {"body", "cta", "send_as", "suppression_key", "rationale"}
        assert required_keys.issubset(res.keys()), f"Missing keys in {trg_id}: {res.keys()}"
        assert isinstance(res["body"], str) and len(res["body"]) > 20, f"Body too short in {trg_id}"
        assert res["send_as"] in ("vera", "merchant_on_behalf"), f"Invalid send_as in {trg_id}: {res['send_as']}"
        assert "http://" not in res["body"] and "https://" not in res["body"], f"URL detected in body for {trg_id}"
        
        # Check taboos
        taboos = category.get("voice", {}).get("vocab_taboo", [])
        for taboo in taboos:
            clean_taboo = taboo.split("(")[0].strip().lower()
            if clean_taboo:
                assert clean_taboo not in res["body"].lower(), f"Taboo '{clean_taboo}' found in {trg_id}"
                
        print(f"  [PASS] {trg_id} (send_as={res['send_as']}, cta={res['cta']})")

def test_multi_turn_auto_reply():
    print("Testing auto-reply detection in MultiTurnHandler...")
    state = ConversationState(conversation_id="conv_test_auto", merchant_id="m_001")
    auto_msg = "Thank you for contacting Dr. Meera's Dental Clinic! Our team will respond shortly."
    
    # Turn 1: Bot should prompt owner
    r1 = MultiTurnHandler.respond(state, auto_msg)
    print("  Turn 1:", r1)
    assert r1["action"] == "send"
    assert "automated reply" in r1["body"].lower()
    
    # Turn 2: Bot should back off (wait)
    r2 = MultiTurnHandler.respond(state, auto_msg)
    print("  Turn 2:", r2)
    assert r2["action"] == "wait"
    assert r2["wait_seconds"] > 0
    
    # Turn 3: Bot should gracefully end
    r3 = MultiTurnHandler.respond(state, auto_msg)
    print("  Turn 3:", r3)
    assert r3["action"] == "end"
    print("  [PASS] Auto-reply lifecycle verified")

def test_multi_turn_intent_transition():
    print("Testing intent transition to Action Mode...")
    state = ConversationState(conversation_id="conv_test_intent", merchant_id="m_001")
    
    commitment_phrases = [
        "Ok lets do it. Whats next?",
        "I want to join",
        "Yes send the abstract please",
        "haan kar do",
        "please update it"
    ]
    
    actioning_keywords = ["done", "sending", "draft", "here", "confirm", "proceed", "next"]
    qualifying_keywords = ["would you", "do you", "can you tell", "what if", "how about"]
    
    for phrase in commitment_phrases:
        st = ConversationState(conversation_id=f"conv_test_{phrase[:5]}", merchant_id="m_001")
        res = MultiTurnHandler.respond(st, phrase)
        assert res["action"] == "send"
        body_lower = res["body"].lower()
        
        has_actioning = any(w in body_lower for w in actioning_keywords)
        has_qualifying = any(w in body_lower for w in qualifying_keywords)
        
        assert has_actioning, f"Expected actioning words for '{phrase}', got: {res['body']}"
        assert not has_qualifying, f"Found qualifying words for '{phrase}': {res['body']}"
        print(f"  [PASS] Action mode verified for: '{phrase}'")

def test_multi_turn_hostility():
    print("Testing hostility and stop detection...")
    state = ConversationState(conversation_id="conv_test_hostile", merchant_id="m_001")
    
    hostile_phrases = [
        "Stop messaging me. This is useless spam.",
        "Not interested.",
        "Please unsubscribe my number."
    ]
    
    for phrase in hostile_phrases:
        st = ConversationState(conversation_id=f"conv_{phrase[:5]}", merchant_id="m_001")
        res = MultiTurnHandler.respond(st, phrase)
        assert res["action"] == "end", f"Expected 'end' action for '{phrase}', got {res['action']}"
        print(f"  [PASS] Graceful exit on hostile phrase: '{phrase}'")

if __name__ == "__main__":
    test_compose_seed_data()
    test_multi_turn_auto_reply()
    test_multi_turn_intent_transition()
    test_multi_turn_hostility()
    print("\nALL UNIT & INTEGRATION TESTS PASSED SUCCESSFULLY!")
