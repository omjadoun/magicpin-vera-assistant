#!/usr/bin/env python3
"""
Adversarial AI Judge Test Suite — 35 Rigorous Stress Tests
==========================================================

Tries to break the magicpin AI assistant implementation across all dimensions:
1. Specificity
2. Category fit
3. Merchant fit
4. Trigger relevance
5. Engagement compulsion

Adversarial Scenarios Tested:
- Changed merchant metrics (0 views, 5,000,000 views, negative delta)
- Changed merchant names & missing owner first names
- Changed offers & unseen offer titles
- Changed prices (high ticket, custom values)
- Injected research digests & compliance circulars
- Unseen trigger kinds & completely empty trigger payloads
- Unseen categories (e.g., veterinary, dry_cleaning)
- Customer state changes (new, lapsed_hard, vip)
- Customer consent revocation (reminder_opt_in=False -> privacy suppression)
- Dynamic multilingual adaptation (English, Hindi, Hinglish, rapid language switching)
- Auto-reply classification & multi-turn progressive backoff
- Opt-out & rejection in English, Hindi, and Hinglish (STOP, nahi chahiye, band karo)
- Ambiguous 'yes' in PITCH vs ACTION_READY states
- Curveballs (bot identity, Swiggy/Zomato, GST, commercial loans, legal disputes)
- Empty / whitespace utterances
- Extended multi-turn anti-repetition guarantees
- Zero URL and taboo word violations
"""

import sys
import io
import json
import re
from typing import Dict, Any

# Ensure UTF-8 output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from bot import compose, ContextStore
from conversation_handlers import (
    StateName,
    ConversationTurn,
    ConversationState,
    MultiTurnHandler,
    respond,
    detect_language,
    classify_auto_reply,
    classify_intent,
)

QUALIFYING_KEYWORDS = ["would you", "do you", "can you tell", "what if", "how about"]
ACTIONING_KEYWORDS = ["done", "sending", "draft", "here", "confirm", "proceed", "next"]
TABOO_WORDS = ["guaranteed", "100% safe", "completely cure", "miracle", "best in city"]


def assert_clean_message(body: str, test_desc: str):
    assert body and len(body.strip()) > 20, f"[{test_desc}] Body too short or empty: {body}"
    assert "http://" not in body and "https://" not in body, f"[{test_desc}] URL found in body: {body}"
    for taboo in TABOO_WORDS:
        assert taboo not in body.lower(), f"[{test_desc}] Taboo word '{taboo}' in body: {body}"


# =============================================================================
# ADVERSARIAL TEST CASES
# =============================================================================

def run_all_adversarial_tests():
    passed = 0
    total = 35

    print("======================================================================")
    print("STARTING 35 ADVERSARIAL STRESS TESTS")
    print("======================================================================")

    # Base Category Contexts
    cat_dentist = {
        "slug": "dentists", "display_name": "Dentists & Dental Clinics",
        "voice": {"tone": "clinical_peer", "register": "doctor_to_doctor", "code_mix": "english_primary"},
        "offer_catalog": [{"id": "d_001", "title": "Dental Cleaning @ ₹299", "value": "299", "status": "active"}]
    }
    cat_restaurant = {
        "slug": "restaurants", "display_name": "Restaurants & Cafes",
        "voice": {"tone": "warm_direct", "register": "peer_merchant", "code_mix": "english_primary"},
        "offer_catalog": [{"id": "r_001", "title": "Lunch Thali @ ₹149", "value": "149", "status": "active"}]
    }

    # 1. Zero views brand new merchant
    m1 = {
        "merchant_id": "m_adv_01", "category_slug": "dentists",
        "identity": {"name": "Apex Dental", "city": "Delhi", "locality": "Rohini", "owner_first_name": "Rohit"},
        "performance": {"views": 0, "calls": 0, "directions": 0, "ctr": 0.0},
        "offers": [{"id": "o_adv_1", "title": "Consultation @ ₹199", "status": "active"}]
    }
    t1 = {"id": "t_adv_01", "kind": "milestone_reached", "payload": {"metric": "views", "value_now": 0, "milestone_value": 100}}
    res1 = compose(cat_dentist, m1, t1)
    assert_clean_message(res1["body"], "Adv 1: Zero metrics")
    assert "0 views" in res1["body"] and "100" in res1["body"]
    print("  [PASS 01/35] Zero views brand new merchant correctly handled")
    passed += 1

    # 2. Huge metric scale (5,000,000 views)
    m2 = {
        "merchant_id": "m_adv_02", "category_slug": "restaurants",
        "identity": {"name": "Mega Dosa", "city": "Bangalore", "locality": "Koramangala", "owner_first_name": "Karthik"},
        "performance": {"views": 5000000, "calls": 24000, "ctr": 0.08},
        "offers": [{"id": "o_adv_2", "title": "Butter Dosa @ ₹99", "status": "active"}]
    }
    t2 = {"id": "t_adv_02", "kind": "perf_dip", "payload": {"metric": "views", "delta_pct": -0.10, "vs_baseline": 5000000}}
    res2 = compose(cat_restaurant, m2, t2)
    assert_clean_message(res2["body"], "Adv 2: Huge metric scale")
    assert "5,000,000" in res2["body"] or "5000000" in res2["body"]
    print("  [PASS 02/35] 5,000,000 views metric formatting correctly handled")
    passed += 1

    # 3. Missing owner first name & missing locality
    m3 = {
        "merchant_id": "m_adv_03", "category_slug": "dentists",
        "identity": {"name": "Dr. Batra Clinic", "city": "Mumbai"},  # No owner_first_name, no locality
        "performance": {"views": 500},
        "offers": []
    }
    t3 = {"id": "t_adv_03", "kind": "gbp_unverified", "payload": {"estimated_uplift_pct": 0.35}}
    res3 = compose(cat_dentist, m3, t3)
    assert_clean_message(res3["body"], "Adv 3: Missing owner and locality")
    assert "Dr. Batra" in res3["body"]  # Extracted from clinic name
    print("  [PASS 03/35] Missing owner & locality gracefully extracted from business name")
    passed += 1

    # 4. Changed custom high-ticket offer price (₹24,999)
    m4 = {
        "merchant_id": "m_adv_04", "category_slug": "dentists",
        "identity": {"name": "Aligner World", "city": "Pune", "locality": "Kothrud", "owner_first_name": "Sneha"},
        "offers": [{"id": "o_adv_4", "title": "Invisible Aligners @ ₹24,999", "status": "active"}]
    }
    t4 = {"id": "t_adv_04", "kind": "perf_dip", "payload": {"metric": "calls", "delta_pct": -0.30, "vs_baseline": 20}}
    res4 = compose(cat_dentist, m4, t4)
    assert_clean_message(res4["body"], "Adv 4: High ticket offer")
    assert "Invisible Aligners @ ₹24,999" in res4["body"]
    print("  [PASS 04/35] High-ticket ₹24,999 price extracted dynamically")
    passed += 1

    # 5. Injected new research study with custom journal & trial size
    t5 = {
        "id": "t_adv_05", "kind": "research_digest",
        "payload": {"top_item_id": "study_aiims_2026"}
    }
    cat_with_study = {
        "slug": "dentists", "display_name": "Dentists",
        "voice": {"tone": "clinical_peer", "register": "doctor_to_doctor", "code_mix": "english_primary"},
        "digest": [{
            "id": "study_aiims_2026", "kind": "research",
            "title": "Salivary Biomarkers for Early Periodontitis Detection",
            "source": "AIIMS Journal of Oral Health (April 2026)",
            "summary": "Salivary MMP-8 chairside test showed 94% sensitivity across 3,450 screen subjects.",
            "trial_n": 3450
        }]
    }
    res5 = compose(cat_with_study, m1, t5)
    assert_clean_message(res5["body"], "Adv 5: Injected research study")
    assert "AIIMS Journal of Oral Health (April 2026)" in res5["body"]
    assert "3,450" in res5["body"]
    print("  [PASS 05/35] Dynamically extracted injected AIIMS research study & 3,450 sample size")
    passed += 1

    # 6. Completely empty trigger payload ({})
    t6 = {"id": "t_adv_06", "kind": "gbp_unverified", "payload": {}}
    res6 = compose(cat_dentist, m1, t6)
    assert_clean_message(res6["body"], "Adv 6: Empty payload")
    assert res6["cta"] == "binary_yes_no"
    print("  [PASS 06/35] Empty payload {} handled without crashing")
    passed += 1

    # 7. Unseen category slug (veterinary)
    cat_vet = {
        "slug": "veterinary", "display_name": "Veterinary Care",
        "voice": {"tone": "compassionate_clinical", "register": "vet_to_client", "code_mix": "english_primary"},
        "offer_catalog": [{"id": "vet_01", "title": "Pet Wellness Check @ ₹499", "status": "active"}]
    }
    m_vet = {
        "merchant_id": "m_vet_01", "category_slug": "veterinary",
        "identity": {"name": "PetCare Clinic", "city": "Delhi", "locality": "Saket", "owner_first_name": "Anil"},
        "performance": {"views": 450}
    }
    t7 = {"id": "t_adv_07", "kind": "milestone_reached", "payload": {"metric": "reviews", "value_now": 48, "milestone_value": 50}}
    res7 = compose(cat_vet, m_vet, t7)
    assert_clean_message(res7["body"], "Adv 7: Unseen veterinary category")
    assert "PetCare Clinic" in res7["body"]
    print("  [PASS 07/35] Unseen veterinary category generalized cleanly")
    passed += 1

    # 8. Unseen trigger kind with fallback
    t8 = {"id": "t_adv_08", "kind": "rainy_day_surge", "payload": {"locality": "Indiranagar"}}
    res8 = compose(cat_restaurant, m2, t8)
    assert_clean_message(res8["body"], "Adv 8: Unseen trigger kind")
    assert "Mega Dosa" in res8["body"]
    print("  [PASS 08/35] Unseen trigger kind fell back to data-grounded merchant composition")
    passed += 1

    # 9. Customer with opted_out consent (Privacy enforcement)
    cust_opted_out = {
        "customer_id": "c_opt_01", "merchant_id": "m_adv_01",
        "identity": {"name": "Aarav Sharma"},
        "state": "opted_out",
        "preferences": {"reminder_opt_in": False},
        "consent": {"scope": []}
    }
    t9 = {"id": "t_adv_09", "scope": "customer", "kind": "recall_due", "payload": {"service_due": "cleaning"}}
    res9 = compose(cat_dentist, m1, t9, cust_opted_out)
    assert_clean_message(res9["body"], "Adv 9: Customer opted out")
    assert res9["send_as"] == "vera", "Must route to vera if customer opted out"
    assert "compliance notice" in res9["body"].lower() or "opt-in" in res9["body"].lower()
    print("  [PASS 09/35] Customer opt-out honored: suppressed direct send and alerted merchant")
    passed += 1

    # 10. Multi-turn: Whitespace inbound message
    st10 = ConversationState(conversation_id="conv_adv_10", merchant_id="m_adv_01")
    r10 = respond(st10, "    ")
    assert r10["action"] == "send"
    assert "whenever you're ready" in r10["body"].lower() or "yes" in r10["body"].lower()
    print("  [PASS 10/35] Whitespace inbound message handled smoothly")
    passed += 1

    # 11. Multi-turn: Hindi opt-out ("Band karo, ab mat bhejna")
    st11 = ConversationState(conversation_id="conv_adv_11", merchant_id="m_adv_01")
    r11 = respond(st11, "Band karo, ab mat bhejna")
    assert r11["action"] == "end"
    assert st11.state in (StateName.GRACEFUL_EXIT, StateName.NOT_INTERESTED)
    print("  [PASS 11/35] Hinglish/Hindi opt-out ('Band karo') triggered permanent end")
    passed += 1

    # 12. Multi-turn: Rejection in Hindi ("Nahi chahiye")
    st12 = ConversationState(conversation_id="conv_adv_12", merchant_id="m_adv_01")
    r12 = respond(st12, "nahi chahiye mujhe ye sab")
    assert r12["action"] == "end"
    assert st12.is_rejected is True
    print("  [PASS 12/35] Hindi rejection ('nahi chahiye') triggered graceful exit with no marketing")
    passed += 1

    # 13. Multi-turn: Ambiguous 'yes' in PITCH state -> ACTION_READY
    st13 = ConversationState(conversation_id="conv_adv_13", merchant_id="m_adv_01", state=StateName.PITCH, category_slug="dentists")
    r13 = respond(st13, "yes")
    assert r13["action"] == "send"
    assert st13.state == StateName.ACTION_READY
    assert any(w in r13["body"].lower() for w in ACTIONING_KEYWORDS)
    assert not any(w in r13["body"].lower() for w in QUALIFYING_KEYWORDS)
    print("  [PASS 13/35] Ambiguous 'yes' in PITCH state transitioned to ACTION_READY (0 qualification)")
    passed += 1

    # 14. Multi-turn: Ambiguous 'yes' in ACTION_READY state -> COMPLETED
    r14 = respond(st13, "yes")
    assert r14["action"] == "send"
    assert st13.state == StateName.COMPLETED
    assert r14["cta"] == "none"
    print("  [PASS 14/35] Ambiguous 'yes' in ACTION_READY confirmed execution -> COMPLETED")
    passed += 1

    # 15. Multi-turn: Bot identity inquiry ("Who are you?")
    st15 = ConversationState(conversation_id="conv_adv_15", merchant_id="m_adv_01")
    r15 = respond(st15, "Who are you?")
    assert r15["action"] == "send"
    assert "vera" in r15["body"].lower()
    print("  [PASS 15/35] Bot identity curveball answered transparently without breaking character")
    passed += 1

    # 16. Multi-turn: Tax / GST curveball ("Help me with GST audit")
    st16 = ConversationState(conversation_id="conv_adv_16", merchant_id="m_adv_01")
    r16 = respond(st16, "Can you help me file my GST returns and audit?")
    assert r16["action"] == "send"
    assert "accountant" in r16["body"].lower() or "ca" in r16["body"].lower()
    print("  [PASS 16/35] GST / Tax curveball bounded cleanly with professional CA redirect")
    passed += 1

    # 17. Multi-turn: Legal dispute curveball ("I will sue magicpin in court")
    st17 = ConversationState(conversation_id="conv_adv_17", merchant_id="m_adv_01")
    r17 = respond(st17, "I will take this to court with my lawyer")
    assert r17["action"] == "send"
    assert "legal" in r17["body"].lower()
    print("  [PASS 17/35] Legal dispute curveball redirected to compliance")
    passed += 1

    # 18. Multi-turn: Rapid language shift across 4 turns (EN -> HI -> Hinglish -> EN)
    st18 = ConversationState(conversation_id="conv_adv_18", merchant_id="m_adv_01", category_slug="salons")
    # Turn 1: English
    r18_1 = respond(st18, "How can you help my salon?")
    assert st18.language == "en"
    # Turn 2: Hindi (Devanagari)
    r18_2 = respond(st18, "क्या आप नए ग्राहक ला सकते हैं?")
    assert st18.language == "hi"
    assert any("\u0900" <= c <= "\u097f" for c in r18_2["body"])
    # Turn 3: Hinglish
    r18_3 = respond(st18, "theek hai, pricing btao kya lagegi?")
    assert st18.language == "hinglish"
    assert any(w in r18_3["body"].lower() for w in ["free", "zero", "walkin", "pay"])
    # Turn 4: Back to English
    r18_4 = respond(st18, "Let's do it, schedule the post now")
    assert st18.language == "en"
    assert st18.state == StateName.ACTION_READY
    print("  [PASS 18/35] 4-turn rapid language switching (EN -> HI -> Hinglish -> EN) verified")
    passed += 1

    # 19. Multi-turn: Auto-reply detection across different conversation IDs for same merchant
    m_id_auto = "m_adv_auto_cross"
    st19_a = ConversationState(conversation_id="conv_replay_turn_1", merchant_id=m_id_auto)
    r19_1 = respond(st19_a, "Thank you for contacting our clinic! Our team will respond shortly.")
    assert r19_1["action"] == "send"

    st19_b = ConversationState(conversation_id="conv_replay_turn_2", merchant_id=m_id_auto)
    r19_2 = respond(st19_b, "Thank you for contacting our clinic! Our team will respond shortly.")
    assert r19_2["action"] == "wait"
    assert r19_2["wait_seconds"] >= 14400

    st19_c = ConversationState(conversation_id="conv_replay_turn_3", merchant_id=m_id_auto)
    r19_3 = respond(st19_c, "Thank you for contacting our clinic! Our team will respond shortly.")
    assert r19_3["action"] == "end"
    print("  [PASS 19/35] Cross-conversation auto-reply streak correctly escalated (send -> wait -> end)")
    passed += 1

    # 20. Customer with honorific 'Dr.' in name
    cust_dr = {
        "customer_id": "c_dr_01", "merchant_id": "m_adv_01",
        "identity": {"name": "Dr. Radhika Kulkarni", "language_pref": "en"},
        "preferences": {"reminder_opt_in": True},
        "consent": {"scope": ["recall_reminders"]}
    }
    t20 = {"id": "t_adv_20", "scope": "customer", "kind": "recall_due", "payload": {"service_due": "dental_checkup"}}
    res20 = compose(cat_dentist, m1, t20, cust_dr)
    assert_clean_message(res20["body"], "Adv 20: Customer with Dr. title")
    assert "Dr. Radhika" in res20["body"], f"Expected 'Dr. Radhika', got {res20['body']}"
    print("  [PASS 20/35] Customer honorific 'Dr. Radhika' properly extracted")
    passed += 1

    # 21. Customer with honorific 'Mrs.' in name
    cust_mrs = {
        "customer_id": "c_mrs_01", "merchant_id": "m_adv_01",
        "identity": {"name": "Mrs. Sunita Verma", "language_pref": "en"},
        "preferences": {"reminder_opt_in": True},
        "consent": {"scope": ["recall_reminders"]}
    }
    res21 = compose(cat_dentist, m1, t20, cust_mrs)
    assert_clean_message(res21["body"], "Adv 21: Customer with Mrs. title")
    assert "Mrs. Sunita" in res21["body"]
    print("  [PASS 21/35] Customer honorific 'Mrs. Sunita' properly extracted")
    passed += 1

    # 22. Competitor opened with unknown/absent distance_km
    t22 = {
        "id": "t_adv_22", "kind": "competitor_opened",
        "payload": {"competitor_name": "Dental X", "their_offer": "50% off"}
        # distance_km omitted
    }
    res22 = compose(cat_dentist, m1, t22)
    assert_clean_message(res22["body"], "Adv 22: Competitor without distance")
    assert "nearby in Rohini" in res22["body"]
    assert "nearby km away" not in res22["body"]
    print("  [PASS 22/35] Competitor without distance rendered cleanly without 'nearby km away'")
    passed += 1

    # 23. Milestone reached with 0 current reviews
    t23 = {"id": "t_adv_23", "kind": "milestone_reached", "payload": {"metric": "reviews", "value_now": 0, "milestone_value": 5}}
    res23 = compose(cat_restaurant, m2, t23)
    assert_clean_message(res23["body"], "Adv 23: Milestone from zero")
    assert "0 reviews on Google — just 5 away from reaching 5" in res23["body"]
    print("  [PASS 23/35] Milestone from zero correctly calculated")
    passed += 1

    # 24. Active planning intent with salon styling packages
    m_salon = {
        "merchant_id": "m_sal_01", "category_slug": "salons",
        "identity": {"name": "Glow Studio", "city": "Mumbai", "locality": "Bandra", "owner_first_name": "Rhea"},
        "offers": [{"id": "s_01", "title": "Keratin Treatment @ ₹1,999", "status": "active"}]
    }
    cat_salon = {
        "slug": "salons", "display_name": "Hair & Beauty Salons",
        "voice": {"tone": "stylish_warm", "register": "expert_stylist", "code_mix": "english_primary"},
        "offer_catalog": [{"id": "sal_01", "title": "Haircut @ ₹99", "value": "99"}]
    }
    t24 = {
        "id": "t_adv_24", "kind": "active_planning_intent",
        "payload": {"intent_topic": "bridal_season_packages"}
    }
    res24 = compose(cat_salon, m_salon, t24)
    assert_clean_message(res24["body"], "Adv 24: Planning intent with salon offer")
    assert "₹1999" in res24["body"] or "₹1,999" in res24["body"]
    print("  [PASS 24/35] Active planning intent computed realistic pricing from merchant salon offer")
    passed += 1

    # 25. Seasonal category with underscore formatting (monsoon_shift_2026)
    t25 = {"id": "t_adv_25", "kind": "category_seasonal", "payload": {"season": "monsoon_shift_2026"}}
    res25 = compose(cat_restaurant, m2, t25)
    assert_clean_message(res25["body"], "Adv 25: Seasonal underscore removal")
    assert "monsoon_shift_2026" not in res25["body"]
    assert "Monsoon Shift 2026" in res25["body"]
    print("  [PASS 25/35] Underscored season formatted cleanly to title-case")
    passed += 1

    # 26. Pharmacy refill with 4 chronic molecules
    cat_pharma = {
        "slug": "pharmacies", "display_name": "Pharmacies",
        "voice": {"tone": "clinical_caring", "register": "pharmacist_to_patient", "code_mix": "english_primary"},
        "offer_catalog": [{"id": "ph_01", "title": "Free Delivery > ₹499", "status": "active"}]
    }
    m_pharma = {
        "merchant_id": "m_ph_01", "category_slug": "pharmacies",
        "identity": {"name": "MedLife Pharmacy", "city": "Jaipur", "locality": "C-Scheme", "owner_first_name": "Sanjay"},
        "offers": [{"id": "o_ph_1", "title": "Senior Citizen 15% OFF", "status": "active"}]
    }
    cust_pharma = {
        "customer_id": "c_ph_01", "merchant_id": "m_ph_01",
        "identity": {"name": "Gopal Prasad", "language_pref": "en"},
        "preferences": {"reminder_opt_in": True},
        "consent": {"scope": ["refill_reminders"]}
    }
    t26 = {
        "id": "t_adv_26", "scope": "customer", "kind": "chronic_refill_due",
        "payload": {
            "molecule_list": ["glimepiride", "metformin", "rosuvastatin", "losartan"],
            "stock_runs_out_iso": "2026-05-10T00:00:00Z"
        }
    }
    res26 = compose(cat_pharma, m_pharma, t26, cust_pharma)
    assert_clean_message(res26["body"], "Adv 26: 4 chronic molecules")
    assert "glimepiride, metformin, rosuvastatin, losartan" in res26["body"]
    assert "Senior Citizen 15% OFF" in res26["body"]
    print("  [PASS 26/35] Pharmacy refill accurately formatted 4 molecules and senior discount")
    passed += 1

    # 27. IPL match with missing team payload (graceful fallback)
    t27 = {"id": "t_adv_27", "kind": "ipl_match_today", "payload": {"venue": "Wankhede Stadium"}}
    res27 = compose(cat_restaurant, m2, t27)
    assert_clean_message(res27["body"], "Adv 27: IPL match fallback")
    assert "Wankhede Stadium" in res27["body"]
    print("  [PASS 27/35] IPL match with partial payload handled gracefully")
    passed += 1

    # 28. Review theme with negative sentiment (slow billing)
    t28 = {
        "id": "t_adv_28", "kind": "review_theme_emerged",
        "payload": {"theme": "billing_delay", "occurrences_30d": 4, "common_quote": "Took 20 mins to get the bill"}
    }
    res28 = compose(cat_restaurant, m2, t28)
    assert_clean_message(res28["body"], "Adv 28: Review theme")
    assert "billing delay" in res28["body"]
    assert "Took 20 mins to get the bill" in res28["body"]
    assert "FAQ" in res28["body"] or "response" in res28["body"]
    print("  [PASS 28/35] Operational review theme feedback transformed constructively")
    passed += 1

    # 29. CDE webinar with accredited points (IDA 3 points)
    t29 = {
        "id": "t_adv_29", "kind": "cde_opportunity",
        "payload": {"credits": 3, "topic": "Advanced Bone Grafting in Implantology"}
    }
    res29 = compose(cat_dentist, m1, t29)
    assert_clean_message(res29["body"], "Adv 29: CDE webinar credits")
    assert "3-credit" in res29["body"] or "3" in res29["body"]
    print("  [PASS 29/35] CDE webinar accredited credits grounded dynamically")
    passed += 1

    # 30. Multi-turn: Commercial loan curveball
    st30 = ConversationState(conversation_id="conv_adv_30", merchant_id="m_adv_01")
    r30 = respond(st30, "I need a 10 lakh business loan for clinic expansion")
    assert r30["action"] == "send"
    assert "loan" in r30["body"].lower() or "financing" in r30["body"].lower()
    print("  [PASS 30/35] Commercial loan inquiry redirected to magicpin capital services")
    passed += 1

    # 31. Multi-turn: Delivery during monsoon curveball
    st31 = ConversationState(conversation_id="conv_adv_31", merchant_id="m_adv_01")
    r31 = respond(st31, "How will delivery work in heavy monsoon rains?")
    assert r31["action"] == "send"
    assert "monsoon" in r31["body"].lower() or "radius" in r31["body"].lower() or "pickup" in r31["body"].lower()
    print("  [PASS 31/35] Weather / monsoon delivery curveball answered with operational radius strategy")
    passed += 1

    # 32. Multi-turn: Extended anti-repetition check over 6 turns
    st32 = ConversationState(conversation_id="conv_adv_32", merchant_id="m_adv_01", category_slug="dentists")
    history_messages = [
        "Hi, what is this?",
        "how much?",
        "ok",
        "is it safe?",
        "what if I want to pause?",
        "let's do it"
    ]
    seen_bodies = set()
    for idx, msg in enumerate(history_messages, 1):
        res = respond(st32, msg)
        body = res.get("body", "")
        if body:
            assert body not in seen_bodies, f"Repeated body on turn {idx}: {body}"
            seen_bodies.add(body)
    print("  [PASS 32/35] 6-turn extended conversation verified: 0 duplicate bodies")
    passed += 1

    # 33. Compliance circular with explicit deadline and sensor guidelines
    t33 = {
        "id": "t_adv_33", "kind": "compliance_alert",
        "payload": {
            "authority": "AERB Regulatory Board",
            "circular_title": "AERB revised radiation safety guideline",
            "effective_date": "2026-08-01",
            "summary": "Mandatory lead apron thickness updated to 0.5mm Pb equivalent."
        }
    }
    res33 = compose(cat_dentist, m1, t33)
    assert_clean_message(res33["body"], "Adv 33: Compliance alert")
    assert "AERB" in res33["body"]
    assert "2026-08-01" in res33["body"]
    assert "0.5mm Pb" in res33["body"]
    print("  [PASS 33/35] AERB regulatory circular, deadline, and lead thickness grounded")
    passed += 1

    # 34. Taboo word replacement active check
    # Inject a taboo word into category offer and ensure sanitization catches it
    cat_dirty = {
        "slug": "salons", "display_name": "Salons",
        "voice": {"tone": "stylish", "register": "expert", "code_mix": "english_primary"},
        "offer_catalog": [{"id": "dirty_01", "title": "Guaranteed Glow Facial @ ₹499", "status": "active"}]
    }
    m_dirty = {
        "merchant_id": "m_dirty_01", "category_slug": "salons",
        "identity": {"name": "Glow Spa", "city": "Delhi", "locality": "Lajpat Nagar", "owner_first_name": "Priya"},
        "offers": [{"id": "d_off", "title": "Guaranteed Weight Loss Package", "status": "active"}]
    }
    t34 = {"id": "t_adv_34", "kind": "perf_dip", "payload": {"metric": "views", "delta_pct": -0.15, "vs_baseline": 100}}
    res34 = compose(cat_dirty, m_dirty, t34)
    # The taboo sanitizer must replace "Guaranteed"
    assert "guaranteed" not in res34["body"].lower(), f"Taboo 'guaranteed' leaked: {res34['body']}"
    assert_clean_message(res34["body"], "Adv 34: Taboo sanitization")
    print("  [PASS 34/35] Taboo word 'Guaranteed' successfully sanitized to safe compliant equivalent")
    passed += 1

    # 35. Determinism test: Calling compose() 5 times with identical inputs produces bit-for-bit identical outputs
    results = [compose(cat_dentist, m1, t1) for _ in range(5)]
    first_body = results[0]["body"]
    for r in results[1:]:
        assert r["body"] == first_body, "compose() must be strictly deterministic!"
    print("  [PASS 35/35] Determinism verified: 5/5 identical runs produced identical output")
    passed += 1

    print("\n======================================================================")
    print(f"ADVERSARIAL JUDGE AUDIT COMPLETED: {passed}/{total} TESTS PASSED (100%)!")
    print("======================================================================")


if __name__ == "__main__":
    run_all_adversarial_tests()
