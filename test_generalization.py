#!/usr/bin/env python3
"""
Anti-Hardcoding & Hidden Context Generalization Test Suite
Tests 22 diverse, schema-valid mutated scenarios across all 5 verticals.
Verifies that compose() and MultiTurnHandler dynamically adapt to:
- Name changes
- Metric & CTR changes
- Offer & price changes
- Research digest mutations
- Customer identity, language, & state changes
- Category cross-generalization
- Competitor, review theme, & event variations
"""

import sys
import io
import json
from copy import deepcopy

# Configure utf-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from bot import compose, STORE, ConversationState, MultiTurnHandler

def run_generalization_tests():
    print("=" * 70)
    print("RUNNING ANTI-HARDCODING & HIDDEN CONTEXT GENERALIZATION TESTS")
    print("=" * 70)

    # Base contexts from STORE
    base_dentist = STORE.get("category", "dentists")
    base_salon = STORE.get("category", "salons")
    base_restaurant = STORE.get("category", "restaurants")
    base_gym = STORE.get("category", "gyms")
    base_pharmacy = STORE.get("category", "pharmacies")

    base_m_dentist = STORE.get("merchant", "m_001_drmeera_dentist_delhi")
    base_m_salon = STORE.get("merchant", "m_003_studio11_salon_hyderabad")
    base_m_restaurant = STORE.get("merchant", "m_005_pizzajunction_restaurant_delhi")
    base_m_gym = STORE.get("merchant", "m_007_powerhouse_gym_bangalore")
    base_m_pharmacy = STORE.get("merchant", "m_009_apollo_pharmacy_jaipur")

    base_customer = STORE.get("customer", "c_001_priya_for_m001")

    passed_count = 0
    total_tests = 22

    # -------------------------------------------------------------------------
    # Scenario 1: Merchant Name Changed
    # -------------------------------------------------------------------------
    m1 = deepcopy(base_m_dentist)
    m1["identity"]["name"] = "Apex Smile Studio"
    m1["identity"]["owner_first_name"] = "Aaradhya"
    trg1 = STORE.get("trigger", "trg_008_curious_ask_studio11") # curious ask
    res1 = compose(base_dentist, m1, trg1)
    assert "Aaradhya" in res1["body"], f"Expected Aaradhya, got: {res1['body']}"
    assert "Apex Smile Studio" in res1["body"], f"Expected Apex Smile Studio, got: {res1['body']}"
    assert "Meera" not in res1["body"]
    print("  [PASS] Scenario 1: Merchant name & owner dynamically adapted")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 2: Merchant Performance Metrics Changed
    # -------------------------------------------------------------------------
    m2 = deepcopy(base_m_dentist)
    m2["performance"]["views"] = 18450
    m2["identity"]["locality"] = "Koramangala"
    trg2 = {"id": "trg_gen_02", "kind": "generic", "scope": "merchant", "payload": {}}
    res2 = compose(base_dentist, m2, trg2)
    assert "18,450" in res2["body"], f"Expected 18,450 views, got: {res2['body']}"
    assert "Koramangala" in res2["body"]
    print("  [PASS] Scenario 2: Dynamic views and locality reflected")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 3: Milestone Value & Target Changed
    # -------------------------------------------------------------------------
    trg3 = {
        "id": "trg_gen_03", "kind": "milestone_reached", "scope": "merchant",
        "payload": {"metric": "review_count", "value_now": 342, "milestone_value": 350}
    }
    res3 = compose(base_dentist, base_m_dentist, trg3)
    assert "342" in res3["body"], f"Expected 342, got: {res3['body']}"
    assert "350" in res3["body"], f"Expected 350, got: {res3['body']}"
    assert "8 away" in res3["body"], f"Expected 8 away, got: {res3['body']}"
    assert "145" not in res3["body"] and "150" not in res3["body"]
    print("  [PASS] Scenario 3: Dynamic milestone calculations adapted")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 4: Merchant Custom Offer Changed
    # -------------------------------------------------------------------------
    m4 = deepcopy(base_m_salon)
    m4["offers"] = [{"id": "o_custom_1", "title": "Keratin Silk Infusion @ ₹3,499", "status": "active"}]
    trg4 = {"id": "trg_gen_04", "kind": "perf_dip", "scope": "merchant", "payload": {"metric": "calls", "delta_pct": -0.35, "vs_baseline": 40}}
    res4 = compose(base_salon, m4, trg4)
    assert "Keratin Silk Infusion @ ₹3,499" in res4["body"], f"Expected custom offer, got: {res4['body']}"
    assert "35%" in res4["body"]
    assert "baseline of 40" in res4["body"]
    print("  [PASS] Scenario 4: Custom merchant offer and price dynamically utilized")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 5: Offer Price Mutated
    # -------------------------------------------------------------------------
    m5 = deepcopy(base_m_salon)
    m5["offers"] = [{"id": "o_custom_2", "title": "Bridal Radiance Glow @ ₹8,999", "status": "active"}]
    res5 = compose(base_salon, m5, trg4)
    assert "₹8,999" in res5["body"], f"Expected ₹8,999 in body, got: {res5['body']}"
    print("  [PASS] Scenario 5: Mutated offer price reflected")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 6: Hidden Research Digest Injected
    # -------------------------------------------------------------------------
    cat6 = deepcopy(base_dentist)
    cat6["digest"] = [{
        "id": "d_hidden_2027",
        "kind": "research",
        "title": "Nanohydroxyapatite paste remineralization study",
        "source": "British Dental Journal 2027",
        "trial_n": 4500,
        "summary": "Nanohydroxyapatite paste reduced enamel erosion in 92% of evaluated subjects."
    }]
    trg6 = {"id": "trg_gen_06", "kind": "research_digest", "scope": "merchant", "payload": {"top_item_id": "d_hidden_2027"}}
    res6 = compose(cat6, base_m_dentist, trg6)
    assert "British Dental Journal 2027" in res6["body"], f"Expected BDJ 2027, got: {res6['body']}"
    assert "4,500-patient" in res6["body"], f"Expected 4,500, got: {res6['body']}"
    assert "Nanohydroxyapatite" in res6["body"]
    assert "JIDA" not in res6["body"] and "2,100" not in res6["body"]
    print("  [PASS] Scenario 6: Injected hidden research study dynamically extracted")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 7: Regulation Change with New Body & Deadline
    # -------------------------------------------------------------------------
    cat7 = deepcopy(base_pharmacy)
    cat7["digest"] = [{
        "id": "d_reg_new",
        "kind": "compliance",
        "title": "Mandatory QR Traceability for Schedule X Drugs",
        "source": "Central Drugs Standard Control Organisation",
        "summary": "All Schedule X shipments must scan GS1 2D barcodes at point of sale."
    }]
    trg7 = {"id": "trg_gen_07", "kind": "regulation_change", "scope": "merchant", "payload": {"top_item_id": "d_reg_new", "deadline_iso": "2027-03-31"}}
    res7 = compose(cat7, base_m_pharmacy, trg7)
    assert "Central Drugs Standard Control Organisation" in res7["body"]
    assert "2027-03-31" in res7["body"]
    assert "Mandatory QR Traceability" in res7["body"]
    assert "IOPA" not in res7["body"] and "radiograph" not in res7["body"]
    print("  [PASS] Scenario 7: Dynamic compliance regulation adaptation")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 8: Mutated Performance Metric in Payload
    # -------------------------------------------------------------------------
    trg8 = {"id": "trg_gen_08", "kind": "perf_dip", "scope": "merchant", "payload": {"metric": "directions", "delta_pct": -0.62, "vs_baseline": 85}}
    res8 = compose(base_dentist, base_m_dentist, trg8)
    assert "directions" in res8["body"]
    assert "62%" in res8["body"]
    assert "85" in res8["body"]
    print("  [PASS] Scenario 8: Mutated performance dip metric extracted")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 9: Customer Identity Changed
    # -------------------------------------------------------------------------
    cx9 = deepcopy(base_customer)
    cx9["identity"]["name"] = "Zoya Akhtar"
    trg9 = {"id": "trg_gen_09", "kind": "appointment_tomorrow", "scope": "customer", "payload": {}}
    res9 = compose(base_dentist, base_m_dentist, trg9, cx9)
    assert "Zoya" in res9["body"]
    assert "Priya" not in res9["body"]
    print("  [PASS] Scenario 9: Customer first name addressed dynamically")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 10: Customer Language Preference Changed (English)
    # -------------------------------------------------------------------------
    cx10 = deepcopy(base_customer)
    cx10["identity"]["language_pref"] = "english"
    trg10 = STORE.get("trigger", "trg_003_recall_due_priya")
    res10 = compose(base_dentist, base_m_dentist, trg10, cx10)
    assert "We have reserved slots" in res10["body"]
    assert "Apke liye ready" not in res10["body"]
    print("  [PASS] Scenario 10: Language preference honored (Pure English)")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 11: Customer State & Elapsed Duration Mutated
    # -------------------------------------------------------------------------
    cx11 = deepcopy(base_customer)
    trg11 = {"id": "trg_gen_11", "kind": "customer_lapsed_hard", "scope": "customer", "payload": {"days_since_last_visit": 150, "previous_focus": "orthodontic aligners"}}
    res11 = compose(base_dentist, base_m_dentist, trg11, cx11)
    assert "5 months" in res11["body"] or "150 days" in res11["body"]
    assert "orthodontic aligners" in res11["body"]
    print("  [PASS] Scenario 11: Dynamic lapse window and service history reflected")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 12: Positive Performance Spike Dynamic Calculation
    # -------------------------------------------------------------------------
    trg12 = {"id": "trg_gen_12", "kind": "perf_spike", "scope": "merchant", "payload": {"metric": "views", "delta_pct": 0.40, "vs_baseline": 2000, "likely_driver": "instagram_reels"}}
    res12 = compose(base_salon, base_m_salon, trg12)
    assert "views" in res12["body"]
    assert "+40%" in res12["body"]
    assert "2,800" in res12["body"]
    assert "instagram reels" in res12["body"]
    print("  [PASS] Scenario 12: Performance spike metric compounded dynamically")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 13: Category Cross-Generalization (Gym Recall Due)
    # -------------------------------------------------------------------------
    trg13 = {"id": "trg_gen_13", "kind": "recall_due", "scope": "customer", "payload": {"service_due": "training_assessment", "days_since_last_visit": 60}}
    res13 = compose(base_gym, base_m_gym, trg13, base_customer)
    assert "🦷" not in res13["body"], "Found tooth emoji in gym message!"
    assert "dental" not in res13["body"].lower()
    assert "cleaning" not in res13["body"].lower()
    assert "fitness" in res13["body"].lower() or "training" in res13["body"].lower()
    print("  [PASS] Scenario 13: Gym recall due correctly generalizes without dental terms")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 14: Category Cross-Generalization (Salon Recall Due)
    # -------------------------------------------------------------------------
    trg14 = {"id": "trg_gen_14", "kind": "recall_due", "scope": "customer", "payload": {"service_due": "hair_spa_refresh", "days_since_last_visit": 45}}
    res14 = compose(base_salon, base_m_salon, trg14, base_customer)
    assert "🦷" not in res14["body"]
    assert "hair" in res14["body"].lower() or "beauty" in res14["body"].lower()
    print("  [PASS] Scenario 14: Salon recall due correctly utilizes salon vocabulary")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 15: Competitor Radar in New Locality & Custom Distance
    # -------------------------------------------------------------------------
    trg15 = {"id": "trg_gen_15", "kind": "competitor_opened", "scope": "merchant", "payload": {
        "competitor_name": "Zenith Fitness Hub", "distance_km": 3.2, "their_offer": "Annual Membership @ ₹9,999"
    }}
    m15 = deepcopy(base_m_gym)
    m15["identity"]["locality"] = "Whitefield"
    res15 = compose(base_gym, m15, trg15)
    assert "Zenith Fitness Hub" in res15["body"]
    assert "3.2 km" in res15["body"]
    assert "Annual Membership @ ₹9,999" in res15["body"]
    assert "Whitefield" in res15["body"]
    print("  [PASS] Scenario 15: Competitor radar grounded on custom competitor & distance")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 16: Supply Alert with New Molecule & Batches
    # -------------------------------------------------------------------------
    trg16 = {"id": "trg_gen_16", "kind": "supply_alert", "scope": "merchant", "payload": {
        "molecule": "amoxicillin clavulanate", "affected_batches": ["AC-901", "AC-902"], "manufacturer": "Sun Pharma"
    }}
    res16 = compose(base_pharmacy, base_m_pharmacy, trg16)
    assert "amoxicillin clavulanate" in res16["body"]
    assert "AC-901, AC-902" in res16["body"]
    assert "Sun Pharma" in res16["body"]
    assert "atorvastatin" not in res16["body"]
    print("  [PASS] Scenario 16: Supply recall grounded on payload molecule and batches")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 17: IPL Match Day with Custom Teams & Weeknight Logic
    # -------------------------------------------------------------------------
    trg17 = {"id": "trg_gen_17", "kind": "ipl_match_today", "scope": "merchant", "payload": {
        "match": "CSK vs RCB", "venue": "M. A. Chidambaram Stadium", "match_time_iso": "2026-05-04T19:30:00+05:30", "is_weeknight": True
    }}
    res17 = compose(base_restaurant, base_m_restaurant, trg17)
    assert "CSK vs RCB" in res17["body"]
    assert "M. A. Chidambaram Stadium" in res17["body"]
    assert "Weeknight matches drive higher" in res17["body"]
    print("  [PASS] Scenario 17: Custom match teams and weeknight rationale adapted")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 18: Custom Review Theme Signal
    # -------------------------------------------------------------------------
    trg18 = {"id": "trg_gen_18", "kind": "review_theme_emerged", "scope": "merchant", "payload": {
        "theme": "air_conditioning", "occurrences_30d": 6, "common_quote": "dining area felt hot during lunch"
    }}
    res18 = compose(base_restaurant, base_m_restaurant, trg18)
    assert "air conditioning" in res18["body"]
    assert "6 customer reviews" in res18["body"]
    assert "dining area felt hot during lunch" in res18["body"]
    print("  [PASS] Scenario 18: Custom review theme dynamically extracted")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 19: Regional Festival Variation
    # -------------------------------------------------------------------------
    trg19 = {"id": "trg_gen_19", "kind": "festival_upcoming", "scope": "merchant", "payload": {"festival": "Pongal"}}
    res19 = compose(base_restaurant, base_m_restaurant, trg19)
    assert "Pongal" in res19["body"]
    print("  [PASS] Scenario 19: Regional festival dynamic injection")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 20: Renewal Due with Custom Plan & Days Remaining
    # -------------------------------------------------------------------------
    m20 = deepcopy(base_m_pharmacy)
    m20["subscription"]["days_remaining"] = 3
    m20["subscription"]["plan"] = "Enterprise"
    trg20 = {"id": "trg_gen_20", "kind": "renewal_due", "scope": "merchant", "payload": {"days_remaining": 3, "plan": "Enterprise"}}
    res20 = compose(base_pharmacy, m20, trg20)
    assert "Enterprise" in res20["body"]
    assert "3 days remaining" in res20["body"]
    print("  [PASS] Scenario 20: Dynamic subscription plan and expiry countdown")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 21: Multi-Turn Action Intent on a Restaurant
    # -------------------------------------------------------------------------
    st21 = ConversationState(conversation_id="conv_res_action", merchant_id="m_005", category_slug="restaurants")
    r21 = MultiTurnHandler.respond(st21, "Ok lets do it. Whats next?")
    assert r21["action"] == "send"
    assert "cavity" not in r21["body"].lower(), "Dental copy found in restaurant multi-turn!"
    assert "kitchen" in r21["body"].lower() or "delivery" in r21["body"].lower()
    print("  [PASS] Scenario 21: Multi-turn action transition customized to restaurant vertical")
    passed_count += 1

    # -------------------------------------------------------------------------
    # Scenario 22: Multi-Turn Action Intent on a Gym
    # -------------------------------------------------------------------------
    st22 = ConversationState(conversation_id="conv_gym_action", merchant_id="m_007", category_slug="gyms")
    r22 = MultiTurnHandler.respond(st22, "Yes please proceed")
    assert r22["action"] == "send"
    assert "fitness" in r22["body"].lower() or "training" in r22["body"].lower()
    assert "cavity" not in r22["body"].lower()
    print("  [PASS] Scenario 22: Multi-turn action transition customized to gym vertical")
    passed_count += 1

    print("=" * 70)
    print(f"RESULTS: {passed_count}/{total_tests} GENERALIZATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_generalization_tests()
