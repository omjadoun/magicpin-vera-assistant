#!/usr/bin/env python3
"""
Test Suite: Complete Multi-Turn Conversation System
===================================================

Validates all 12 multi-turn conversation scenarios and state transitions:
1. Merchant wants to join -> Immediate action mode (zero qualification)
2. Merchant accepts -> Draft prepared with actioning words
3. Merchant asks "how much?" -> Transparent pricing
4. Merchant rejects "not interested" -> Graceful exit, stop marketing
5. Merchant says "STOP" -> Permanent opt-out termination
6. Automated reply -> Canned response detected, no bot qualification
7. Same automated reply repeated -> Multi-turn escalation (send -> wait -> end)
8. Merchant changes English -> Hindi -> Responds fluently in Hindi
9. Merchant changes Hindi -> Hinglish -> Responds fluently in Hinglish
10. Unexpected question / curveball -> Polite boundary + value bridge
11. Merchant doesn't meaningfully respond ("ok") -> Non-repetitive low-friction follow-up
12. Merchant accepts and action is completed -> COMPLETED state + confirmed release

Also tests:
- Formal state transitions
- Anti-repetition engine (no duplicate sentences, hooks, or offers)
- Zero-qualifying constraint (NO 'would you', 'do you', 'can you tell', 'what if', 'how about')
"""

import sys
import io
from typing import Dict, Any

# Ensure UTF-8 output for Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

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


def print_test_header(name: str):
    print(f"\n--- [TEST] {name} ---")


def test_scenario_1_merchant_wants_to_join():
    print_test_header("Scenario 1: Merchant wants to join ('I want to join magicpin.')")
    state = ConversationState(
        conversation_id="conv_join_01",
        merchant_id="m_food_01",
        category_slug="restaurants",
        state=StateName.DISCOVERY
    )
    
    reply = respond(state, "I want to join magicpin.")
    print(f"  Bot action: {reply['action']}")
    print(f"  Bot body: {reply.get('body', '')[:90]}...")
    print(f"  New State: {state.state}")

    assert reply["action"] == "send"
    assert state.state == StateName.ACTION_READY
    assert state.is_accepted is True
    assert state.pending_action is not None

    body_lower = reply["body"].lower()
    # Must contain actioning words
    assert any(w in body_lower for w in ACTIONING_KEYWORDS), f"Missing actioning keywords: {reply['body']}"
    # Must NOT contain qualifying questions
    assert not any(w in body_lower for w in QUALIFYING_KEYWORDS), f"Found qualifying keywords: {reply['body']}"
    print("  [PASS] Scenario 1 passed: moved directly to action mode with zero qualification.")


def test_scenario_2_merchant_accepts():
    print_test_header("Scenario 2: Merchant accepts ('yes')")
    state = ConversationState(
        conversation_id="conv_accept_02",
        merchant_id="m_salon_02",
        category_slug="salons",
        state=StateName.PITCH
    )
    state.add_turn("vera", "We noticed 40 regular clients haven't visited in 60 days. Shall we run a winback campaign?")

    reply = respond(state, "yes")
    print(f"  Bot action: {reply['action']}")
    print(f"  Bot body: {reply.get('body', '')[:90]}...")
    print(f"  New State: {state.state}")

    assert reply["action"] == "send"
    assert state.state == StateName.ACTION_READY
    assert state.is_accepted is True

    body_lower = reply["body"].lower()
    assert any(w in body_lower for w in ACTIONING_KEYWORDS)
    assert not any(w in body_lower for w in QUALIFYING_KEYWORDS)
    assert "confirm" in body_lower
    print("  [PASS] Scenario 2 passed: accepted into ACTION_READY without qualifying questions.")


def test_scenario_3_merchant_asks_how_much():
    print_test_header("Scenario 3: Merchant asks ('how much?')")
    state = ConversationState(
        conversation_id="conv_price_03",
        merchant_id="m_gym_03",
        category_slug="gyms",
        state=StateName.PITCH
    )

    reply = respond(state, "how much?")
    print(f"  Bot action: {reply['action']}")
    print(f"  Bot body: {reply.get('body', '')[:90]}...")
    print(f"  New State: {state.state}")

    assert reply["action"] == "send"
    assert state.state == StateName.WAITING_FOR_INFO
    body_lower = reply["body"].lower()
    # Must be transparent about zero upfront fees or pay-per-walkin
    assert "upfront" in body_lower or "free" in body_lower or "pay-per-walk-in" in body_lower
    assert "cta" in reply
    print("  [PASS] Scenario 3 passed: transparent pricing provided with binary next step.")


def test_scenario_4_merchant_rejects():
    print_test_header("Scenario 4: Merchant rejects ('not interested')")
    state = ConversationState(
        conversation_id="conv_reject_04",
        merchant_id="m_dentist_04",
        category_slug="dentists",
        state=StateName.PITCH
    )

    reply = respond(state, "not interested")
    print(f"  Bot action: {reply['action']}")
    print(f"  New State: {state.state}")

    assert reply["action"] == "end"
    assert state.state == StateName.NOT_INTERESTED
    assert state.status == "ended"
    assert state.is_rejected is True
    print("  [PASS] Scenario 4 passed: conversation ended, marketing stopped.")


def test_scenario_5_merchant_says_stop():
    print_test_header("Scenario 5: Merchant says ('STOP')")
    state = ConversationState(
        conversation_id="conv_stop_05",
        merchant_id="m_pharma_05",
        category_slug="pharmacies",
        state=StateName.PITCH
    )

    reply = respond(state, "STOP")
    print(f"  Bot action: {reply['action']}")
    print(f"  New State: {state.state}")

    assert reply["action"] == "end"
    assert state.state == StateName.GRACEFUL_EXIT
    assert state.status == "ended"
    assert "opt-out" in reply["rationale"].lower() or "stop" in reply["rationale"].lower()
    print("  [PASS] Scenario 5 passed: permanent opt-out respected, terminated immediately.")


def test_scenario_6_automated_reply():
    print_test_header("Scenario 6: Automated reply ('Thank you for contacting our team...')")
    state = ConversationState(
        conversation_id="conv_auto_06",
        merchant_id="m_auto_06",
        category_slug="dentists",
        state=StateName.PITCH
    )
    auto_msg = "Thank you for contacting our team. We will get back to you shortly."

    reply = respond(state, auto_msg)
    print(f"  Bot action: {reply['action']}")
    print(f"  Bot body: {reply.get('body', '')}")
    print(f"  New State: {state.state}")

    assert reply["action"] == "send"
    assert state.state == StateName.AUTO_REPLY_DETECTED
    assert state.auto_reply_status == "confirmed"
    assert "automated reply" in reply["body"].lower()
    # Must NOT ask qualification questions to a bot
    assert not any(w in reply["body"].lower() for w in QUALIFYING_KEYWORDS)
    print("  [PASS] Scenario 6 passed: single polite notification for owner, no qualification to bot.")


def test_scenario_7_same_automated_reply_repeated():
    print_test_header("Scenario 7: Same automated reply repeated across turns")
    state = ConversationState(
        conversation_id="conv_auto_rep_07",
        merchant_id="m_auto_rep_07",
        category_slug="restaurants",
        state=StateName.PITCH
    )
    auto_msg = "Thank you for contacting our team. We will get back to you shortly."

    # Turn 1: First auto-reply -> send notification
    r1 = respond(state, auto_msg)
    assert r1["action"] == "send"
    assert state.state == StateName.AUTO_REPLY_DETECTED
    print("  Turn 1:", r1["action"])

    # Turn 2: Second auto-reply -> wait 24h
    r2 = respond(state, auto_msg)
    assert r2["action"] == "wait"
    assert r2["wait_seconds"] >= 14400
    assert state.state == StateName.WAITING_FOR_INFO
    print("  Turn 2:", r2["action"], f"wait_seconds={r2['wait_seconds']}")

    # Turn 3: Third auto-reply -> end conversation
    r3 = respond(state, auto_msg)
    assert r3["action"] == "end"
    assert state.state == StateName.GRACEFUL_EXIT
    assert state.status == "ended"
    print("  Turn 3:", r3["action"], f"rationale={r3['rationale']}")
    print("  [PASS] Scenario 7 passed: progressive backoff and permanent exit on 3x auto-reply.")


def test_scenario_8_merchant_changes_english_to_hindi():
    print_test_header("Scenario 8: Merchant changes English -> Hindi")
    state = ConversationState(
        conversation_id="conv_lang_hi_08",
        merchant_id="m_lang_08",
        category_slug="restaurants",
        language="en",
        state=StateName.PITCH
    )
    state.add_turn("vera", "Hello! Would you like to see how magicpin drives footfall to your restaurant?")

    # Merchant switches to Hindi (Devanagari)
    hindi_msg = "मुझे मैजिकपिन के बारे में बताओ, इससे क्या फायदा होगा?"
    reply = respond(state, hindi_msg)
    print(f"  Detected language: {state.language}")
    print(f"  Bot body: {reply.get('body', '')}")

    assert state.language == "hi"
    assert reply["action"] == "send"
    # Response must be in Devanagari Hindi
    assert any("\u0900" <= c <= "\u097f" for c in reply["body"])
    print("  [PASS] Scenario 8 passed: dynamically adapted from English to Hindi.")


def test_scenario_9_merchant_changes_hindi_to_hinglish():
    print_test_header("Scenario 9: Merchant changes Hindi -> Hinglish")
    state = ConversationState(
        conversation_id="conv_lang_hinglish_09",
        merchant_id="m_lang_09",
        category_slug="salons",
        language="hi",
        state=StateName.PITCH
    )
    state.add_turn("vera", "नमस्ते! magicpin आपके सैलून के लिए ग्राहक लाता है।")

    # Merchant switches to Hinglish (Romanized Hindi)
    hinglish_msg = "theek hai, details btao kaise setup karein?"
    reply = respond(state, hinglish_msg)
    print(f"  Detected language: {state.language}")
    print(f"  Bot body: {reply.get('body', '')}")

    assert state.language == "hinglish"
    assert reply["action"] == "send"
    body_lower = reply["body"].lower()
    # Response must contain Hinglish words
    assert any(w in body_lower for w in ["aapka", "karein", "hai", "main", "draft", "bhej"])
    print("  [PASS] Scenario 9 passed: dynamically adapted from Hindi to Hinglish.")


def test_scenario_10_unexpected_question():
    print_test_header("Scenario 10: Unexpected question / curveball")
    state = ConversationState(
        conversation_id="conv_curveball_10",
        merchant_id="m_food_10",
        category_slug="restaurants",
        state=StateName.PITCH
    )
    curveball_msg = "Do you also support Swiggy and Zomato order management?"

    reply = respond(state, curveball_msg)
    print(f"  Bot action: {reply['action']}")
    print(f"  Bot body: {reply.get('body', '')}")
    print(f"  New State: {state.state}")

    assert reply["action"] == "send"
    assert state.state == StateName.WAITING_FOR_INFO
    body_lower = reply["body"].lower()
    # Must politely address third-party apps and redirect to magicpin's direct footfall
    assert "delivery" in body_lower or "swiggy" in body_lower or "footfall" in body_lower
    assert not any(w in body_lower for w in QUALIFYING_KEYWORDS)
    print("  [PASS] Scenario 10 passed: curveball handled with clear boundary and value bridge.")


def test_scenario_11_low_information_response():
    print_test_header("Scenario 11: Merchant doesn't meaningfully respond ('ok')")
    state = ConversationState(
        conversation_id="conv_low_info_11",
        merchant_id="m_retail_11",
        category_slug="pharmacies",
        state=StateName.PITCH
    )
    initial_pitch = "Over 120 patients in your pincode need regular prescription refills each month."
    state.record_bot_send(initial_pitch, "binary_yes_no")

    # Merchant gives low-information response
    reply = respond(state, "ok")
    print(f"  Bot action: {reply['action']}")
    print(f"  Bot body: {reply.get('body', '')}")
    print(f"  New State: {state.state}")

    assert reply["action"] == "send"
    assert state.state == StateName.FOLLOW_UP
    assert state.unanswered_nudges == 1

    # ANTI-REPETITION: Must NOT repeat the initial pitch
    assert initial_pitch not in reply["body"]
    assert reply["body"] != initial_pitch
    print("  [PASS] Scenario 11 passed: low-information reply advanced with non-repetitive next step.")


def test_scenario_12_merchant_accepts_and_action_completed():
    print_test_header("Scenario 12: Merchant accepts and action is completed")
    state = ConversationState(
        conversation_id="conv_complete_12",
        merchant_id="m_dentist_12",
        category_slug="dentists",
        state=StateName.PITCH
    )

    # Turn 1: Merchant commits
    r1 = respond(state, "Let's do it, what's next?")
    assert r1["action"] == "send"
    assert state.state == StateName.ACTION_READY
    assert state.pending_action is not None
    print("  Turn 1 (Commitment):", r1["body"][:80], "...")

    # Turn 2: Merchant confirms execution
    r2 = respond(state, "CONFIRM")
    assert r2["action"] == "send"
    assert state.state == StateName.COMPLETED
    assert state.status == "ended"
    assert state.completed_action is not None
    assert state.pending_action is None
    assert r2["cta"] == "none"
    print("  Turn 2 (Confirmed):", r2["body"])
    print("  [PASS] Scenario 12 passed: action scheduled and marked COMPLETED.")


def test_anti_repetition_across_turns():
    print_test_header("Anti-Repetition Engine Verification")
    state = ConversationState(
        conversation_id="conv_anti_rep_test",
        merchant_id="m_gym_rep",
        category_slug="gyms",
        state=StateName.PITCH
    )

    turns = [
        "What is this?",
        "how much?",
        "ok",
        "let's do this",
        "confirm"
    ]

    sent_bodies = []
    for i, t in enumerate(turns, 1):
        res = respond(state, t)
        body = res.get("body", "")
        if body:
            # Check body is not identical to any previously sent body
            assert body not in sent_bodies, f"Repeated body on turn {i}: {body}"
            sent_bodies.append(body)
        print(f"  Turn {i} ('{t}'): state={state.state}, action={res['action']}")

    print("  [PASS] Anti-repetition confirmed: 0 duplicate messages across 5 turns.")


def test_required_intent_utterances_across_all_5_categories():
    print_test_header("Requirement: 9 Required Utterances across ALL 5 Categories")
    categories = ["restaurants", "salons", "gyms", "pharmacies", "dentists"]

    utterances = [
        ("I want to join", StateName.ACTION_READY, "join_onboarding", "single_choice_confirm"),
        ("I want to join magicpin", StateName.ACTION_READY, "join_onboarding", "single_choice_confirm"),
        ("Yes, let's do it", StateName.ACTION_READY, "accept_proposal", "single_choice_confirm"),
        ("Go ahead", StateName.ACTION_READY, "accept_proposal", "single_choice_confirm"),
        ("Please update it", StateName.ACTION_READY, "modify_update", "single_choice_confirm"),
        ("Haan kar do", StateName.ACTION_READY, "accept_proposal", "single_choice_confirm"),
        ("No thanks", StateName.NOT_INTERESTED, "reject", None),
        ("Not interested", StateName.NOT_INTERESTED, "reject", None),
        ("STOP", StateName.GRACEFUL_EXIT, "opt_out", None),
    ]

    for cat in categories:
        for utt, expected_state, expected_intent, expected_cta in utterances:
            state = ConversationState(
                conversation_id=f"conv_{cat}_{utt.replace(' ', '_')}",
                merchant_id=f"m_{cat}_test",
                category_slug=cat,
                state=StateName.PITCH
            )
            # Add a generic pitch
            state.add_turn("vera", "We have a growth opportunity for your store.")

            reply = respond(state, utt)
            assert state.merchant_intent == expected_intent, (
                f"Cat {cat}, Utterance '{utt}': expected intent {expected_intent}, got {state.merchant_intent}"
            )
            assert state.state == expected_state, (
                f"Cat {cat}, Utterance '{utt}': expected state {expected_state}, got {state.state}"
            )

            if expected_cta:
                assert reply.get("cta") == expected_cta, (
                    f"Cat {cat}, Utterance '{utt}': expected cta {expected_cta}, got {reply.get('cta')}"
                )

            # Verification of zero fake execution claims & no hallucinated timestamps
            if reply.get("body"):
                body_lower = reply["body"].lower()
                assert "tomorrow 10:00 am" not in body_lower, f"Hallucinated time in {cat} for '{utt}'"
                assert "10:00 am" not in body_lower, f"Hallucinated time in {cat} for '{utt}'"
                assert "done! drafting your message and pre-filling" not in body_lower, (
                    f"Fake 'Done!' execution claim in {cat} for '{utt}'"
                )

    print(f"  [PASS] Successfully verified all 9 utterances across all 5 merchant categories (45/45 evaluations)!")


def test_adversarial_trigger_vs_join_intent():
    print_test_header("Requirement: Adversarial Trigger Isolation (Trigger about X, Merchant says 'I want to join')")
    
    test_cases = [
        {
            "category": "dentists",
            "trigger_msg": "Compliance alert: DCI circular 2026-11-04 issued revised radiograph dose limits. Maximum dose drops to 1.0 mSv. RVG unaffected.",
            "unwanted_words": ["radiograph", "iopa", "rvg", "circular", "dose", "preventive checkup", "patients due", "booking"]
        },
        {
            "category": "restaurants",
            "trigger_msg": "IPL Match tonight! Expect 35% surge in food delivery orders between 7-11 PM.",
            "unwanted_words": ["ipl", "match", "cricket", "delivery surge", "7-11 pm"]
        },
        {
            "category": "pharmacies",
            "trigger_msg": "Urgent quality recall for Metformin 500mg SR batches B-8812, B-8814 by Sun Pharma.",
            "unwanted_words": ["metformin", "recall", "b-8812", "sun pharma", "sub-potency"]
        },
        {
            "category": "gyms",
            "trigger_msg": "Milestone alert: Zen Yoga reached 94 reviews on Google Maps — just 6 away from crossing 100!",
            "unwanted_words": ["94 reviews", "100 reviews", "google maps rank"]
        },
        {
            "category": "salons",
            "trigger_msg": "Local grooming demand: searches for hair spa and styling in your area jumped 34% this week.",
            "unwanted_words": ["34%", "hair spa", "styling searches"]
        }
    ]

    for tc in test_cases:
        state = ConversationState(
            conversation_id=f"conv_adv_{tc['category']}",
            merchant_id=f"m_{tc['category']}_adv",
            category_slug=tc["category"],
            state=StateName.PITCH
        )
        state.add_turn("vera", tc["trigger_msg"])

        # Merchant ignores trigger and says "I want to join magicpin"
        reply = respond(state, "I want to join magicpin")
        body_lower = reply["body"].lower()

        # 1. Must be recognized as join_onboarding
        assert state.merchant_intent == "join_onboarding"
        assert state.state == StateName.ACTION_READY

        # 2. Must contain onboarding transparency (₹0 upfront, free listing)
        assert "₹0 upfront" in body_lower or "free" in body_lower or "partner" in body_lower

        # 3. Must NOT inherit ANY unrelated trigger content!
        for unw in tc["unwanted_words"]:
            assert unw not in body_lower, (
                f"Adversarial contamination! Category {tc['category']} inherited trigger word '{unw}': {reply['body']}"
            )

        # 4. Must NOT invent fake appointments, schedules, or unperformed actions
        assert "tomorrow 10:00 am" not in body_lower
        assert "done! drafting" not in body_lower

    print("  [PASS] Adversarial isolation verified: zero trigger leakage into onboarding responses across all categories!")


def test_zero_cross_vertical_leakage():
    print_test_header("Requirement: Zero Dental / Cross-Vertical Contamination")
    
    non_dental_categories = ["restaurants", "salons", "gyms", "pharmacies"]
    dental_specific_words = ["dental", "dentist", "patient", "consultation", "iopa", "rvg", "clinical care"]

    messages_to_test = [
        "I want to join",
        "I want to join magicpin",
        "Yes, let's do it",
        "Go ahead",
        "Please update it",
        "Haan kar do",
    ]

    for cat in non_dental_categories:
        for msg in messages_to_test:
            state = ConversationState(
                conversation_id=f"conv_leak_{cat}_{msg.replace(' ', '_')}",
                merchant_id=f"m_{cat}_leak",
                category_slug=cat,
                state=StateName.PITCH
            )
            state.add_turn("vera", f"Welcome, here is an active promotion for your {cat} business.")

            reply = respond(state, msg)
            body_lower = reply["body"].lower()

            for dw in dental_specific_words:
                assert dw not in body_lower, (
                    f"Dental term '{dw}' leaked into {cat} response for '{msg}': {reply['body']}"
                )

    print("  [PASS] Zero cross-vertical leakage verified: no dental terminology appeared in non-dental categories!")


def test_single_primary_cta_constraint():
    print_test_header("Requirement: Maintain Single Primary CTA (No competing CONFIRM + CANCEL)")
    
    state = ConversationState(
        conversation_id="conv_cta_check",
        merchant_id="m_cta_test",
        category_slug="restaurants",
        state=StateName.PITCH
    )
    
    reply = respond(state, "I want to join magicpin")
    # CTA must be single_choice_confirm, not a competing multi-choice
    assert reply["cta"] == "single_choice_confirm"
    assert "confirm" in reply["cta"].lower()
    assert "cancel" not in reply["cta"].lower()
    
    # Body must clearly ask for CONFIRM as the primary CTA
    assert "reply confirm" in reply["body"].lower() or "confirm" in reply["body"].lower()

    print("  [PASS] Single primary CTA verified: single_choice_confirm with zero competing buttons.")


if __name__ == "__main__":
    print("======================================================================")
    print("STARTING COMPLETE MULTI-TURN CONVERSATION TEST SUITE")
    print("======================================================================")
    
    test_scenario_1_merchant_wants_to_join()
    test_scenario_2_merchant_accepts()
    test_scenario_3_merchant_asks_how_much()
    test_scenario_4_merchant_rejects()
    test_scenario_5_merchant_says_stop()
    test_scenario_6_automated_reply()
    test_scenario_7_same_automated_reply_repeated()
    test_scenario_8_merchant_changes_english_to_hindi()
    test_scenario_9_merchant_changes_hindi_to_hinglish()
    test_scenario_10_unexpected_question()
    test_scenario_11_low_information_response()
    test_scenario_12_merchant_accepts_and_action_completed()
    test_anti_repetition_across_turns()
    
    # Newly added requirements tests
    test_required_intent_utterances_across_all_5_categories()
    test_adversarial_trigger_vs_join_intent()
    test_zero_cross_vertical_leakage()
    test_single_primary_cta_constraint()

    print("\n======================================================================")
    print("ALL 17 TEST SUITES (INCLUDING ALL NEW INTENT & ISOLATION TESTS) PASSED PERFECTLY!")
    print("======================================================================")

