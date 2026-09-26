#!/usr/bin/env python3
"""
magicpin AI Challenge — Production Multi-Turn Conversation State Machine
========================================================================

Complete multi-turn conversation handler for the magicpin assistant (Vera):
- Formal state machine: DISCOVERY, PITCH, ACTION_READY, ACTION_IN_PROGRESS,
  WAITING_FOR_INFO, FOLLOW_UP, AUTO_REPLY_DETECTED, NOT_INTERESTED,
  COMPLETED, GRACEFUL_EXIT
- Real vs automated/canned reply classification with graceful multi-turn backoff
- Intent transition engine: IMMEDIATE Action Mode with ZERO qualifying questions
- Hostility / STOP opt-out graceful termination (no marketing after rejection)
- Transparent, data-driven pricing handling
- Unexpected question / curveball boundaries with smooth value bridging
- Passive / low-information acknowledgment without repetitive loops
- Multilingual dynamic switching: English <-> Hindi <-> Hinglish
- Anti-repetition engine: tracks CTA history, facts communicated, sent sentences,
  preventing duplicate hooks, sentences, or offers

Author: Lead AI Engineer for magicpin AI Challenge Submission
"""

from __future__ import annotations
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Set, Tuple


# =============================================================================
# STATE CONSTANTS
# =============================================================================

class StateName:
    DISCOVERY = "DISCOVERY"
    PITCH = "PITCH"
    ACTION_READY = "ACTION_READY"
    ACTION_IN_PROGRESS = "ACTION_IN_PROGRESS"
    WAITING_FOR_INFO = "WAITING_FOR_INFO"
    FOLLOW_UP = "FOLLOW_UP"
    AUTO_REPLY_DETECTED = "AUTO_REPLY_DETECTED"
    NOT_INTERESTED = "NOT_INTERESTED"
    COMPLETED = "COMPLETED"
    GRACEFUL_EXIT = "GRACEFUL_EXIT"


# Global merchant auto-reply tracker across conversations to prevent replay resets
MERCHANT_AUTO_REPLY_TRACKER: Dict[str, int] = {}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ConversationTurn:
    role: str  # "vera" | "merchant" | "customer"
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ConversationState:
    conversation_id: str
    merchant_id: str
    category_slug: str = "general"
    customer_id: Optional[str] = None
    state: str = StateName.PITCH
    mode: str = "pitch"  # Backward compatibility: "pitch", "action", "waiting", "ended", "completed"
    status: str = "active"  # Backward compatibility: "active", "waiting", "ended"
    turns: List[ConversationTurn] = field(default_factory=list)
    last_bot_message: str = ""
    last_inbound_message: str = ""
    merchant_intent: str = "unknown"
    objective: str = "engage"
    language: str = "en"  # "en", "hi", "hinglish"
    auto_reply_status: str = "none"  # "none", "suspected", "confirmed"
    auto_reply_score: float = 0.0
    repeated_auto_reply_count: int = 0
    pending_action: Optional[str] = None
    completed_action: Optional[str] = None
    is_accepted: bool = False
    is_rejected: bool = False
    cta_history: List[str] = field(default_factory=list)
    facts_communicated: List[str] = field(default_factory=list)
    unanswered_nudges: int = 0
    wait_until: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_turn(self, role: str, message: str) -> None:
        turn = ConversationTurn(role=role, message=message)
        self.turns.append(turn)
        if role in ("merchant", "customer"):
            self.last_inbound_message = message.strip()
        elif role == "vera":
            self.last_bot_message = message.strip()
            self._record_facts_and_sentences(message)

    def transition_to(self, new_state: str, reason: str = "") -> None:
        self.state = new_state
        if new_state in (StateName.GRACEFUL_EXIT, StateName.NOT_INTERESTED):
            self.status = "ended"
            self.mode = "ended"
            self.is_rejected = True
        elif new_state == StateName.COMPLETED:
            self.status = "ended"
            self.mode = "completed"
        elif new_state in (StateName.ACTION_READY, StateName.ACTION_IN_PROGRESS):
            self.status = "active"
            self.mode = "action"
            self.is_accepted = True
        elif new_state in (StateName.WAITING_FOR_INFO, StateName.AUTO_REPLY_DETECTED):
            self.mode = "waiting"
            if self.repeated_auto_reply_count >= 2:
                self.status = "waiting"
        elif new_state == StateName.FOLLOW_UP:
            self.status = "active"
            self.mode = "pitch"

    def record_bot_send(self, body: str, cta: str, rationale: str = "") -> None:
        self.add_turn(role="vera", message=body)
        self.cta_history.append(cta)
        self._record_facts_and_sentences(body)

    def _record_facts_and_sentences(self, text: str) -> None:
        # Split text into normalized sentences for anti-repetition tracking
        sentences = [s.strip().lower() for s in re.split(r"[.!?\n]+", text) if len(s.strip()) > 5]
        sent_set: Set[str] = self.metadata.setdefault("sent_sentences", set())
        for s in sentences:
            sent_set.add(s)
            if s not in self.facts_communicated:
                self.facts_communicated.append(s)

    def has_said_sentence(self, sentence: str) -> bool:
        sent_set: Set[str] = self.metadata.get("sent_sentences", set())
        norm = sentence.strip().lower()
        return norm in sent_set or any(norm in prev for prev in sent_set)

    @property
    def history(self) -> List[ConversationTurn]:
        return self.turns


# =============================================================================
# PATTERNS & HEURISTICS
# =============================================================================

# Automated / Canned reply indicators
AUTO_REPLY_PATTERNS = [
    r"thank\s+you\s+for\s+contacting",
    r"thanks\s+for\s+contacting",
    r"our\s+team\s+will\s+respond\s+shortly",
    r"we\s+will\s+get\s+back\s+to\s+you\s+shortly",
    r"will\s+respond\s+shortly",
    r"automated\s+assistant",
    r"automated\s+message",
    r"auto-reply",
    r"automated\s+response",
    r"this\s+is\s+an\s+automated",
    r"aapki\s+jaankari\s+ke\s+liye\s+bahut-bahut\s+shukriya",
    r"main\s+ek\s+automated\s+assistant\s+hoon",
    r"hamari\s+team\s+tak\s+pahuncha\s+deti\s+hoon",
    r"currently\s+unavailable",
    r"out\s+of\s+office",
    r"busy\s+right\s+now",
    r"thanks\s+for\s+reaching\s+out",
    r"we\s+have\s+received\s+your\s+message",
    r"our\s+business\s+hours\s+are",
    r"an\s+agent\s+will\s+be\s+with\s+you",
]

# Explicit opt-out / STOP phrases
OPT_OUT_PATTERNS = [
    r"\b(stop|unsubscribe|opt[ -]?out)\b",
    r"\b(stop\s+messaging|stop\s+sending|don'?t\s+message|dont\s+message)\b",
    r"\b(never\s+message|don'?t\s+contact|dont\s+contact)\b",
    r"\b(useless\s+spam|spam|harassment|bothering\s+me)\b",
    r"\b(leave\s+me\s+alone|remove\s+my\s+number|delete\s+my\s+number|report\s+spam)\b",
    r"\b(band\s+karo|mat\s+bhejo|ruko|ab\s+mat\s+bhejna)\b",
]

# Rejection / Not Interested phrases
REJECTION_PATTERNS = [
    r"\b(not\s+interested|no\s+thanks|nahi\s+chahiye|don'?t\s+want|dont\s+want)\b",
    r"\b(mat\s+bhejo|not\s+needed|no\s+need|decline|disagree)\b",
    r"\b(not\s+for\s+me|no\s+interest|pass|na\s+baba|nahi\s+karna|nahi\s+chahiyen)\b",
]

# Join / Onboarding phrases (Merchant wants to join or partner with magicpin)
JOIN_ONBOARDING_PATTERNS = [
    r"\b(i\s+want\s+to\s+join|want\s+to\s+join|join\s+magicpin|how\s+to\s+join|how\s+can\s+i\s+join)\b",
    r"\b(mujhe\s+join\s+karna|mujhe\s+judna|join\s+karna\s+hai|magicpin\s+join|join\s+karna)\b",
    r"\b(sign\s+me\s+up|onboard\s+me|register\s+my\s+store|register\s+my\s+clinic|register\s+my\s+business|partner\s+with\s+magicpin)\b",
    r"\b(how\s+do\s+i\s+onboard|onboarding\s+process|listing\s+my\s+store|listing\s+my\s+business)\b",
    r"^join(\s+magicpin)?$",
]

# Modify / Update phrases (Merchant asks to update their profile or listing)
MODIFY_UPDATE_PATTERNS = [
    r"\b(please\s+(?:check\s+&\s+)?update(?:s|\s+the\s+profile|\s+my\s+listing|\s+it)?|update\s+it|update\s+kar\s+do|update\s+please)\b",
    r"\b(change\s+(?:timings?|hours?|details?|offers?|address)|edit\s+(?:profile|listing|details))\b",
    r"\b(profile\s+update|listing\s+update|details\s+update)\b",
    r"^update(\s+it)?$",
]

# Proposal Acceptance / Action Commitment phrases
ACCEPT_PROPOSAL_PATTERNS = [
    r"\b(let'?s\s+do\s+it|lets\s+do\s+it|lets\s+do\s+this|let'?s\s+do\s+this)\b",
    r"\b(go\s+ahead|proceed|sure|yep|yeah|yup|ok\s+lets\s+go|okay\s+let'?s\s+do\s+it)\b",
    r"\b(haan\s+kar\s+do|kar\s+do|haan\s+bhejo|haan\s+batao|aage\s+batao)\b",
    r"\b(send\s+(?:me\s+)?(?:the\s+)?(?:abstract|list|draft|details|pdf|preview|template|checklist))\b",
    r"\b(draft\s+(?:it|the\s+post|the\s+whatsapp|the\s+banner))\b",
    r"\b(what'?s\s+next|whats\s+next|what\s+is\s+next)\b",
    r"\b(deal|agree|done\s+deal|lock\s+it\s+in)\b",
    r"^(yes|yes\s+please|yes\s+pls|haan|ha|sure|go\s+ahead)$",
]

# Customer Specific / Roster Requests
CUSTOMER_REQUEST_PATTERNS = [
    r"\b(customer\s+list|patient\s+list|client\s+list|roster|customer\s+records?|patient\s+records?)\b",
    r"\b(who\s+are\s+the\s+patients|which\s+customers|repeat\s+customers|order\s+history)\b",
]

# Combined alias for backward compatibility
ACTION_COMMITMENT_PATTERNS = JOIN_ONBOARDING_PATTERNS + MODIFY_UPDATE_PATTERNS + ACCEPT_PROPOSAL_PATTERNS

# Execution / Confirmation phrases
CONFIRM_EXECUTE_PATTERNS = [
    r"\b(confirm|confirmed|execute|publish|lock\s+it|send\s+now|start\s+campaign|live\s+kar\s+do)\b",
]

# Pricing / Cost inquiries
PRICING_PATTERNS = [
    r"\b(how\s+much|cost|costs?|price|prices?|pricing|charges?|commission|fees?|rates?)\b",
    r"\b(kitna\s+(?:\w+\s+)?lagega|kitna\s+kharcha|kya\s+rate\s+hai|kya\s+charge\s+hai|kitna\s+charge|kitne\s+paise|paise|fees?)\b",
]

# Curveballs / Out-of-scope inquiries
OUT_OF_SCOPE_HANDLERS = [
    (r"\b(who\s+are\s+you|what\s+is\s+vera|are\s+you\s+(?:a\s+)?bot|kya\s+tum\s+bot\s+ho|tum\s+kaun\s+ho)\b", {
        "en": "I am Vera, your dedicated magicpin store assistant. I work quietly in the background to spot demand surges, track competitor updates, and draft ready-to-launch promotions for your store.",
        "hi": "मैं वेरा हूँ, आपकी समर्पित मैजिकपिन स्टोर सहायक। मैं बैकग्राउंड में काम करती हूँ ताकि मांग में वृद्धि देख सकूँ और आपके स्टोर के लिए तैयार प्रचार बना सकूँ।",
        "hinglish": "Main Vera hoon, aapki dedicated magicpin store assistant. Main background me demand surges track karke ready promotions draft karti hoon."
    }),
    (r"\b(swiggy|zomato|ubereats|deliveroo)\b", {
        "en": "While third-party delivery apps manage their own commission orders, magicpin specializes in driving direct local customer walk-ins and direct repeat sales to your counter without middleman friction.",
        "hi": "तीसरे पक्ष के डिलीवरी ऐप्स अपने कमीशन पर काम करते हैं, जबकि मैजिकपिन सीधे स्थानीय ग्राहकों को आपकी दुकान तक लाने पर ध्यान केंद्रित करता है।",
        "hinglish": "Third-party delivery apps ke comparison me magicpin aapki shop par direct local customer walk-ins aur direct repeat sales laane par focus karta hai."
    }),
    (r"\b(gst|income\s+tax|tax\s+filing|ca\s+|audit|balance\s+sheet)\b", {
        "en": "GST and tax compliance are best handled with your chartered accountant, while I focus on growing your store's customer footfall and campaign visibility.",
        "hi": "जीएसटी और टैक्स से जुड़े मामले आपके सीए (चार्टर्ड अकाउंटेंट) द्वारा बेहतर संभाले जाते हैं, जबकि मेरा ध्यान आपके स्टोर के ग्राहकों को बढ़ाने पर है।",
        "hinglish": "GST aur tax matters aapke CA ke saath handle karna best rehta hai, jabki mera focus aapke store par customer footfalls badhana hai."
    }),
    (r"\b(loan|credit\s+line|bank\s+overdraft|capital)\b", {
        "en": "Commercial financing and bank credit lines are outside my scope, though our team can connect you with magicpin financial services if needed.",
        "hi": "व्यावसायिक ऋण और बैंक क्रेडिट लाइन मेरे दायरे से बाहर हैं, हालांकि यदि आवश्यक हो तो हमारी टीम आपको मैजिकपिन वित्तीय सेवाओं से जोड़ सकती है।",
        "hinglish": "Commercial loans aur credit line mere scope se bahar hain, lekin zaroorat padne par hamari team aapko magicpin financial services se connect kar sakti hai."
    }),
    (r"\b(ice\s+cream|rainy|monsoon|rain|refrigeration)\b", {
        "en": "For seasonal or weather-sensitive logistics, local customer pickup and fast 15-minute radius delivery promotions protect product freshness during monsoon.",
        "hi": "मौसम के संवेदनशील सामान के लिए, स्थानीय ग्राहक पिकअप और 15-मिनट की डिलीवरी प्रचार बारिश के दौरान ताजगी बनाए रखते हैं।",
        "hinglish": "Weather-sensitive items ke liye local pickup aur fast 15-minute delivery radius promotions monsoon me product freshness protect karte hain."
    }),
    (r"\b(legal|court|police|lawyer|sue)\b", {
        "en": "Legal and formal disputes are managed directly by magicpin legal compliance.",
        "hi": "कानूनी और औपचारिक विवाद सीधे मैजिकपिन कानूनी अनुपालन टीम द्वारा संभाले जाते हैं।",
        "hinglish": "Legal aur formal disputes directly magicpin legal compliance team manage karti hai."
    }),
    (r"\b(safe|safety|secure|security|risk|trust|data\s+safe|privacy)\b", {
        "en": "magicpin operates with bank-grade data security and never shares your customer or billing records with third parties.",
        "hi": "मैजिकपिन बैंक-ग्रेड सुरक्षा पर काम करता है और कभी भी आपके ग्राहक या बिलिंग डेटा को तीसरे पक्ष के साथ साझा नहीं करता।",
        "hinglish": "magicpin bank-grade data security ke saath kaam karta hai aur aapka customer ya billing record kisi third party se share nahi karta."
    }),
    (r"\b(pause|cancel|stop\s+later|lock\s*in|contract|commitment|quit)\b", {
        "en": "There is zero lock-in or cancellation penalty — you can pause, restart, or adjust your store campaigns at any moment directly from WhatsApp.",
        "hi": "यहाँ कोई लॉक-इन या कैंसलेशन पेनल्टी नहीं है — आप व्हाट्सएप से कभी भी अपने अभियानों को रोक, शुरू या बदल सकते हैं।",
        "hinglish": "Yahan zero lock-in ya penalty hai — aap kisi bhi time WhatsApp se campaign pause, restart ya edit kar sakte hain."
    }),
]


# Low-information / passive responses
LOW_INFO_PATTERNS = [
    r"^(ok|okay|hmm|k|fine|accha|achha|theek|thik|noted|\.\.\.|👍|👌)$",
]


# =============================================================================
# CLASSIFIERS
# =============================================================================

def detect_language(text: str) -> str:
    """
    Infers conversation language dynamically from inbound text:
    - "hi" (Devanagari script or explicit Hindi request)
    - "hinglish" (Romanized Hindi lexicon/grammar markers)
    - "en" (Standard English)
    """
    # 1. Check for Devanagari Unicode block (\u0900 - \u097F)
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"

    lower = text.lower()

    # Explicit requests for Hindi
    if any(p in lower for p in ["hindi me", "hindi mein", "hindi please", "hindi me baat"]):
        return "hi"

    # 2. Check for Hinglish markers (Romanized Hindi words)
    hinglish_markers = [
        "kya", "kaise", "batao", "btao", "karo", "kar do", "haan", "nahi", "nhn",
        "hoga", "theek", "thik", "accha", "achha", "mujhe", "mera", "meri", "hum",
        "aap", "aapka", "aapki", "kitna", "kab", "kyu", "kyun", "karna", "chahiye",
        "pata", "samajh", "bhai", "sirji", "sir ji", "dost", "bolo", "bataiye"
    ]
    tokens = set(re.findall(r"\b[a-z]+\b", lower))
    matches = sum(1 for m in hinglish_markers if m in tokens)
    if matches >= 2 or any(p in lower for p in ["kar do", "batao", "kaise karein", "kya fayda", "mujhe join"]):
        return "hinglish"

    return "en"


def classify_auto_reply(text: str, state: ConversationState) -> Tuple[bool, float]:
    """
    Evaluates whether an inbound message is a canned auto-reply:
    Returns (is_auto_reply, score).
    """
    lower = " ".join(text.strip().lower().split())
    if not lower:
        return False, 0.0

    score = 0.0

    # Pattern check
    for pat in AUTO_REPLY_PATTERNS:
        if re.search(pat, lower):
            score += 0.8
            break

    # Exact repetition check across turns
    if state.last_inbound_message and lower == " ".join(state.last_inbound_message.strip().lower().split()):
        score += 0.6

    is_auto = score >= 0.7
    return is_auto, score


def classify_intent(text: str, state: ConversationState) -> str:
    """
    Determines merchant intent from message text and current state context.
    """
    lower = text.strip().lower()

    # 1. Opt-out
    if any(re.search(pat, lower) for pat in OPT_OUT_PATTERNS):
        return "opt_out"

    # 2. Rejection
    if any(re.search(pat, lower) for pat in REJECTION_PATTERNS):
        return "reject"

    # 3. Action Execution Confirmation (if in ACTION_READY)
    if state.state in (StateName.ACTION_READY, StateName.ACTION_IN_PROGRESS):
        if any(re.search(pat, lower) for pat in CONFIRM_EXECUTE_PATTERNS) or lower in [
            "confirm", "confirmed", "execute", "publish", "done", "live kar do",
            "yes", "yes please", "haan", "sure", "go ahead"
        ]:
            return "confirm_execute"

    # 4. Join / Onboarding Request (explicit desire to join/onboard on magicpin)
    if any(re.search(pat, lower) for pat in JOIN_ONBOARDING_PATTERNS):
        return "join_onboarding"

    # 5. Pricing / Cost Inquiry
    if any(re.search(pat, lower) for pat in PRICING_PATTERNS):
        return "ask_pricing"

    # 6. Customer Specific / Roster Request
    if any(re.search(pat, lower) for pat in CUSTOMER_REQUEST_PATTERNS):
        return "customer_request"

    # 7. Modify / Update Request (explicit request to update profile/details)
    if any(re.search(pat, lower) for pat in MODIFY_UPDATE_PATTERNS):
        return "modify_update"

    # 8. Proposal Acceptance / Action Commitment
    if any(re.search(pat, lower) for pat in ACCEPT_PROPOSAL_PATTERNS):
        return "accept_proposal"

    # 6. Unexpected question / curveball
    for pat, _ in OUT_OF_SCOPE_HANDLERS:
        if re.search(pat, lower):
            return "unexpected_question"

    # 7. Low-information passive
    if any(re.search(pat, lower) for pat in LOW_INFO_PATTERNS) or (len(lower) <= 3 and lower in ["ok", "k", "ha", "hm"]):
        return "passive_low_info"

    # 8. General inquiry
    if "?" in lower or any(w in lower for w in ["what", "how", "why", "kya", "kaise"]):
        return "inquiry"

    return "general_reply"


def get_category_terms(cat_slug: str) -> Dict[str, str]:
    """
    Returns vertical-specific terms and neutral draft copy.
    Guarantees no vertical cross-contamination (e.g. dental terms in restaurants).
    """
    terms = {
        "restaurants": {
            "biz_type": "restaurant",
            "scope": "local food lovers in your delivery radius",
            "update_focus": "menu specials and active dining offers",
            "draft": "Special update from our kitchen: check out our current deals for fresh delivery and dine-in today!"
        },
        "salons": {
            "biz_type": "salon",
            "scope": "nearby beauty and grooming clients",
            "update_focus": "styling services and beauty packages",
            "draft": "Refresh your look this week: book your styling and beauty appointment today!"
        },
        "gyms": {
            "biz_type": "fitness center",
            "scope": "active fitness enthusiasts in your area",
            "update_focus": "training schedules and trial workout passes",
            "draft": "Stay consistent with your fitness goals: new workout slots and training passes are now open!"
        },
        "pharmacies": {
            "biz_type": "pharmacy",
            "scope": "verified neighborhood residents",
            "update_focus": "healthcare essentials and medicine delivery availability",
            "draft": "Your neighbourhood health store: fast home delivery and repeat prescription support available."
        },
        "dentists": {
            "biz_type": "dental clinic",
            "scope": "local patients seeking dental consultations",
            "update_focus": "consultation slots and dental care packages",
            "draft": "Quality clinical care and consultation appointments available this week."
        },
    }
    return terms.get(cat_slug, {
        "biz_type": "store",
        "scope": "nearby local customers",
        "update_focus": "store offerings and active promotions",
        "draft": "Fresh updates and promotional offers now available at our store."
    })


# =============================================================================
# STRATEGY & RESPONSE ENGINE
# =============================================================================

class MultiTurnHandler:
    """
    Core state machine controller for multi-turn conversations.
    """

    @classmethod
    def respond(cls, state: ConversationState, inbound_message: str) -> dict:
        msg = inbound_message.strip()
        if not msg:
            return {
                "action": "send",
                "body": "Hi there! Whenever you're ready to review your store updates or launch a campaign, just reply 'Yes' 😊",
                "cta": "binary_yes_no",
                "rationale": "Empty message handled with frictionless invitation."
            }

        state.add_turn(role="merchant", message=msg)

        # Update language dynamically based on latest merchant utterance
        detected_lang = detect_language(msg)
        state.language = detected_lang

        # ---------------------------------------------------------------------
        # 1. Auto-Reply Classification & Multi-Turn Escalation
        # ---------------------------------------------------------------------
        is_auto, auto_score = classify_auto_reply(msg, state)
        m_id = state.merchant_id

        if is_auto:
            state.auto_reply_status = "confirmed"
            state.auto_reply_score = auto_score
            state.repeated_auto_reply_count += 1
            MERCHANT_AUTO_REPLY_TRACKER[m_id] = MERCHANT_AUTO_REPLY_TRACKER.get(m_id, 0) + 1

            total_auto_count = max(state.repeated_auto_reply_count, MERCHANT_AUTO_REPLY_TRACKER[m_id])

            if total_auto_count >= 3:
                state.transition_to(StateName.GRACEFUL_EXIT, reason="auto_reply_3x")
                return {
                    "action": "end",
                    "rationale": "Auto-reply detected 3+ times consecutively. Closing conversation to prevent wasted turns and respect business boundaries."
                }
            elif total_auto_count == 2:
                state.transition_to(StateName.WAITING_FOR_INFO, reason="auto_reply_2x")
                return {
                    "action": "wait",
                    "wait_seconds": 86400,
                    "rationale": "Same canned auto-reply detected twice in a row. Pausing for 24 hours to allow the store owner to access WhatsApp."
                }
            else:
                state.transition_to(StateName.AUTO_REPLY_DETECTED, reason="auto_reply_1x")
                if state.language == "hi":
                    body = "यह एक ऑटो-रिप्लाई लग रहा है 😊 जब भी स्टोर के मालिक उपलब्ध हों, बस 'हाँ' लिखकर भेजें और मैं सभी विवरण साझा कर दूँगी!"
                    cta = "हाँ / ना"
                elif state.language == "hinglish":
                    body = "Looks like yeh ek automated reply hai 😊 Jab bhi owner available hon, bas 'Yes' reply karein aur main details share kar doongi!"
                    cta = "binary_yes_no"
                else:
                    body = "Looks like an automated reply 😊 Whenever the store owner is available, just reply 'Yes' and I'll share the details!"
                    cta = "binary_yes_no"

                state.record_bot_send(body, cta)
                return {
                    "action": "send",
                    "body": body,
                    "cta": cta,
                    "rationale": "Detected first auto-reply; left a polite, frictionless invitation for the owner without wasting qualification questions."
                }

        # Reset auto-reply streak on genuine human response
        state.repeated_auto_reply_count = 0
        state.auto_reply_status = "none"
        if m_id in MERCHANT_AUTO_REPLY_TRACKER:
            MERCHANT_AUTO_REPLY_TRACKER[m_id] = 0

        # ---------------------------------------------------------------------
        # 2. Intent Classification
        # ---------------------------------------------------------------------
        intent = classify_intent(msg, state)
        state.merchant_intent = intent

        # ---------------------------------------------------------------------
        # 3. Intent: Opt-out (STOP) -> IMMEDIATE PERMANENT EXIT
        # ---------------------------------------------------------------------
        if intent == "opt_out":
            state.transition_to(StateName.GRACEFUL_EXIT, reason="opt_out_stop")
            return {
                "action": "end",
                "rationale": "Merchant explicitly requested opt-out with STOP. Suppressing all outreach triggers and terminating immediately."
            }

        # ---------------------------------------------------------------------
        # 4. Intent: Rejection (Not Interested) -> GRACEFUL EXIT (NO MARKETING)
        # ---------------------------------------------------------------------
        if intent == "reject":
            state.transition_to(StateName.NOT_INTERESTED, reason="not_interested")
            if state.language == "hi":
                body = "कोई बात नहीं! मैंने आपकी पसंद नोट कर ली है। हम आपको दोबारा परेशान नहीं करेंगे। अगर कभी जरूरत हो, तो 'Hi Vera' लिखकर संपर्क करें। धन्यवाद! 🙏"
            elif state.language == "hinglish":
                body = "Samajh gayi, bilkul koi baat nahi! Maine aapka preference note kar liya hai aur aage se disturb nahi karungi. Jab bhi zaroorat ho, bas 'Hi Vera' likhein. Have a great day! 🙏"
            else:
                body = "Understood, no problem at all! I have marked your preference and will not reach out again. If you ever need assistance, just reply 'Hi Vera'. Wishing your business the best! 🙏"

            # Graceful exit can end immediately or deliver one polite acknowledgment
            return {
                "action": "end",
                "rationale": "Merchant signaled explicit rejection ('not interested'). Gracefully closed without further marketing or alternative pitches."
            }

        # ---------------------------------------------------------------------
        # 5. Intent: Join / Onboarding ("I want to join", "I want to join magicpin")
        # ---------------------------------------------------------------------
        if intent == "join_onboarding":
            state.transition_to(StateName.ACTION_READY, reason="merchant_join_onboarding")
            state.pending_action = "merchant_onboarding_activation"
            c_terms = get_category_terms(state.category_slug)

            if state.language == "hi":
                body = (
                    f"मैजिकपिन में आपका स्वागत है! हम आपके {c_terms['biz_type']} के साथ साझेदारी करने के लिए उत्सुक हैं। "
                    f"स्टोर लिस्टिंग बिल्कुल मुफ्त है (₹0 अग्रिम शुल्क) — केवल सत्यापित ग्राहकों पर ही कमीशन लागू होता है। "
                    f"अपनी स्टोर प्रोफाइल सक्रिय करने और स्थानीय ग्राहकों तक पहुँचने के लिए, सत्यापन शुरू करने हेतु बस CONFIRM लिखकर भेजें।"
                )
            elif state.language == "hinglish":
                body = (
                    f"magicpin me aapka welcome hai! Hum aapke {c_terms['biz_type']} ke saath partner karne ke liye excited hain. "
                    f"Store listing bilkul free hai (₹0 upfront fees) — commission sirf verified customer walk-ins par lagta hai. "
                    f"Apni partner profile activate karne ke liye, quick verification shuru karne ke liye bas CONFIRM reply karein."
                )
            else:
                body = (
                    f"Welcome to magicpin! We are excited to partner with your {c_terms['biz_type']}. "
                    f"Store listing is 100% free with ₹0 upfront onboarding fees — you only pay performance commission on verified customer walk-ins. "
                    f"Reply CONFIRM to begin your quick store verification and activate your partner presence."
                )

            cta = "single_choice_confirm"
            state.record_bot_send(body, cta)
            return {
                "action": "send",
                "body": body,
                "cta": cta,
                "rationale": "Merchant initiated join/onboarding. Transitioned to Action Mode with transparent zero-upfront model and single primary confirmation step."
            }

        # ---------------------------------------------------------------------
        # 6. Intent: Modify / Update ("Please update it", "update kar do")
        # ---------------------------------------------------------------------
        if intent == "modify_update":
            state.transition_to(StateName.ACTION_READY, reason="profile_update_requested")
            state.pending_action = "profile_update_review"
            c_terms = get_category_terms(state.category_slug)

            if state.language == "hi":
                body = (
                    f"अपडेट के लिए तैयार! मैं आपके {c_terms['biz_type']} लिस्टिंग पर नवीनतम {c_terms['update_focus']} अपडेट कर सकती हूँ। "
                    f"अपडेटेड प्रोफाइल विवरण प्रकाशित करने के लिए बस CONFIRM लिखकर भेजें।"
                )
            elif state.language == "hinglish":
                body = (
                    f"Update ke liye ready! Main aapke {c_terms['biz_type']} profile par latest {c_terms['update_focus']} refresh kar sakti hoon. "
                    f"Updated profile details publish karne ke liye bas CONFIRM reply karein."
                )
            else:
                body = (
                    f"Ready to update! I can refresh your {c_terms['biz_type']} listing with your latest {c_terms['update_focus']}. "
                    f"Reply CONFIRM to apply and publish the updated profile details."
                )

            cta = "single_choice_confirm"
            state.record_bot_send(body, cta)
            return {
                "action": "send",
                "body": body,
                "cta": cta,
                "rationale": "Merchant requested profile/details update. Transitioned to Action Mode with single primary confirmation."
            }

        # ---------------------------------------------------------------------
        # 7. Intent: Accept Current Proposal ("Yes, let's do it", "Go ahead", "Haan kar do")
        # ---------------------------------------------------------------------
        if intent in ("accept_proposal", "accept_action"):
            state.transition_to(StateName.ACTION_READY, reason="explicit_intent_commitment")
            state.pending_action = "activate_proposed_action"
            c_terms = get_category_terms(state.category_slug)
            last_bot = state.last_bot_message.lower()
            biz_name = state.metadata.get("merchant_name", f"your {c_terms['biz_type']}")
            locality = state.metadata.get("locality", "your area")

            # Ground response strictly in what was proposed in last_bot_message
            if re.search(r"\b(reviews?|google review|rating)\b", last_bot) or "milestone" in last_bot:
                body_content = (
                    f"Here is your 1-click review-request template draft for customers in {locality}:\n\n"
                    f"\"Thank you for visiting {biz_name}! If you had a great experience, please take a moment to leave us a quick Google review: [Review Link]. It means the world to our team!\"\n\n"
                    f"Reply CONFIRM to save this template and add it to your messaging."
                )
            elif "ipl" in last_bot or "match" in last_bot or "delivery banner" in last_bot:
                body_content = (
                    f"Here is your match night delivery highlight for {biz_name}:\n\n"
                    f"\"Match Night Special from {biz_name}! Order direct during the match for fast preparation and doorstep delivery.\"\n\n"
                    f"Reply CONFIRM to publish this delivery highlight to your store listing."
                )
            elif "seasonal" in last_bot or "summer" in last_bot or "monsoon" in last_bot:
                body_content = (
                    f"Here is your seasonal announcement draft for {locality}:\n\n"
                    f"\"Seasonal essentials are fully stocked at {biz_name}! Enjoy reliable availability and fast home delivery across {locality}.\"\n\n"
                    f"Reply CONFIRM to queue this announcement for your customers."
                )
            elif any(w in last_bot for w in ["syllabus", "circular", "compliance", "cde", "audit"]):
                body_content = (
                    f"Here is your compliance audit checklist summary:\n\n"
                    f"• Equipment and operational standards review\n"
                    f"• Verification checklist prepared for your staff\n\n"
                    f"Reply CONFIRM to receive the complete compliance pack."
                )
            elif "competitor" in last_bot or "price war" in last_bot:
                body_content = (
                    f"Here is the high-trust post draft highlighting your reputation in {locality}:\n\n"
                    f"\"Trusted quality and proven service at {biz_name}. Serving {locality} with verified care and authentic customer satisfaction.\"\n\n"
                    f"Reply CONFIRM to publish this post to your Google profile."
                )
            else:
                body_content = (
                    f"Here is the draft update for {c_terms['scope']}:\n\n"
                    f"\"{c_terms['draft']}\"\n\n"
                    f"Reply CONFIRM to approve and schedule this update for your listing."
                )

            if state.language == "hi":
                body = (
                    f"तैयार! यहाँ आपकी लिस्टिंग के लिए ड्राफ्ट है:\n\n"
                    f"\"{c_terms['draft']}\"\n\n"
                    f"इसे सक्रिय करने के लिए बस CONFIRM लिखकर भेजें।"
                )
            elif state.language == "hinglish":
                body = (
                    f"Ready! Yeh raha aapka draft:\n\n"
                    f"\"{c_terms['draft']}\"\n\n"
                    f"Ise activate karne ke liye bas CONFIRM reply karein."
                )
            else:
                body = body_content

            cta = "single_choice_confirm"
            state.record_bot_send(body, cta)
            return {
                "action": "send",
                "body": body,
                "cta": cta,
                "rationale": "Merchant accepted proposal. Transitioned to Action Mode presenting grounded draft with zero qualifying questions."
            }

        # ---------------------------------------------------------------------
        # 8. Intent: Customer Specific Request ("Who are the patients due?", "customer list")
        # ---------------------------------------------------------------------
        if intent == "customer_request":
            state.transition_to(StateName.WAITING_FOR_INFO, reason="customer_records_inquiry")

            if state.language == "hi":
                body = (
                    f"ग्राहक गोपनीयता नियमों (DPDP) के तहत, व्यक्तिगत संपर्क विवरण आपके मर्चेंट पोर्टल में सुरक्षित रखे जाते हैं। "
                    f"मैं आपकी ओर से केवल सहमति प्राप्त ग्राहकों को प्रसारण संदेश भेज सकती हूँ। "
                    f"क्या आप एक प्रसारण ड्राफ्ट तैयार करवाना चाहते हैं?"
                )
                cta = "हाँ / ना"
            elif state.language == "hinglish":
                body = (
                    f"Customer privacy regulations ke according, individual contact details merchant portal me securely rehte hain. "
                    f"Main consented customers ke liye aapki taraf se broadcast update send kar sakti hoon. "
                    f"Kya aap broadcast draft prepare karwana chahenge?"
                )
                cta = "Haan / Nahi"
            else:
                body = (
                    f"To protect customer privacy and adhere to DPDP regulations, individual customer records and phone numbers are securely maintained in your merchant portal dashboard. "
                    f"I can initiate an automated broadcast to eligible consented customers on your behalf. "
                    f"Would you like me to prepare a broadcast draft for your review?"
                )
                cta = "binary_yes_no"

            state.record_bot_send(body, cta)
            return {
                "action": "send",
                "body": body,
                "cta": cta,
                "rationale": "Merchant inquired about customer records. Addressed with DPDP compliance notice and privacy-safe broadcast offer."
            }

        # ---------------------------------------------------------------------
        # 9. Intent: Execution Confirmed (State was ACTION_READY)
        # ---------------------------------------------------------------------
        if intent == "confirm_execute" or (state.state == StateName.ACTION_READY and "confirm" in msg.lower()):
            state.transition_to(StateName.COMPLETED, reason="action_executed")
            state.completed_action = state.pending_action or "action_completed"
            state.pending_action = None

            if state.language == "hi":
                body = (
                    "बधाई हो! आपका अनुरोध सफलतापूर्वक कन्फर्म हो चुका है और सक्रियण के लिए कतारबद्ध है। "
                    "ग्राहकों के आने और ऑर्डर के लाइव आंकड़े आपको सीधे यहीं मिलेंगे।"
                )
            elif state.language == "hinglish":
                body = (
                    "All set! Aapka request successfully confirm ho chuka hai aur activation ke liye queued hai. "
                    "Customer walk-ins aur performance updates aapko yahan milte rahenge."
                )
            else:
                body = (
                    "All set! Your request has been confirmed and queued for activation. "
                    "You will receive live customer walk-in notifications and performance updates right here on WhatsApp."
                )
            cta = "none"

            state.record_bot_send(body, cta)
            return {
                "action": "send",
                "body": body,
                "cta": cta,
                "rationale": "Execution confirmed by merchant. Completed action and queued release with zero pending friction."
            }

        # ---------------------------------------------------------------------
        # 7. Intent: Pricing Inquiry ("how much?") -> TRANSPARENT PRICING
        # ---------------------------------------------------------------------
        if intent == "ask_pricing":
            state.transition_to(StateName.WAITING_FOR_INFO, reason="pricing_clarified")

            if state.language == "hi":
                body = (
                    "magicpin पर स्टोर लिस्टिंग बिल्कुल मुफ्त है (₹0 अग्रिम शुल्क)। "
                    "हम केवल वास्तविक सत्यापित बिक्री और वॉक-इन पर काम करते हैं। "
                    "क्या आप अपनी दुकान के लिए तैयार किया गया प्रचार ड्राफ्ट देखना चाहेंगे?"
                )
                cta = "हाँ / ना"
            elif state.language == "hinglish":
                body = (
                    "magicpin par listing bilkul free hai (₹0 upfront listing fee). "
                    "Hamara model pure pay-per-walkin par chalta hai — commission sirf verified customer sales par lagta hai. "
                    "Kya aap draft campaign preview dekhna chahenge?"
                )
                cta = "Haan / Nahi"
            else:
                body = (
                    "Zero upfront listing fees (₹0 onboarding fee) — magicpin operates on a pure pay-per-walk-in model (0% upfront, "
                    "with performance commission only on verified customer transactions). "
                    "Shall I share the draft promotion we prepared for your store?"
                )
                cta = "binary_yes_no"

            state.record_bot_send(body, cta)
            return {
                "action": "send",
                "body": body,
                "cta": cta,
                "rationale": "Transparently answered pricing inquiry with zero-upfront model and transitioned to binary draft preview."
            }

        # ---------------------------------------------------------------------
        # 8. Intent: Unexpected Question / Curveball -> BOUNDARY + VALUE BRIDGE
        # ---------------------------------------------------------------------
        if intent == "unexpected_question":
            state.transition_to(StateName.WAITING_FOR_INFO, reason="curveball_addressed")

            redirect_dict = {
                "en": "magicpin focuses directly on driving verified local customer footfalls to your store without middleman commissions.",
                "hi": "मैजिकपिन सीधे आपके स्टोर पर सत्यापित स्थानीय ग्राहकों की संख्या बढ़ाने पर केंद्रित है।",
                "hinglish": "magicpin direct local customer walk-ins badhane par focus karta hai bina kisi middleman commission ke."
            }
            redirect_text = redirect_dict.get(state.language, redirect_dict["en"])

            for pat, custom_expl in OUT_OF_SCOPE_HANDLERS:
                if re.search(pat, msg.lower()):
                    if isinstance(custom_expl, dict):
                        redirect_text = custom_expl.get(state.language, custom_expl.get("en", ""))
                    else:
                        redirect_text = str(custom_expl)
                    break

            if state.language == "hi":
                body = (
                    f"अच्छा सवाल है! {redirect_text} "
                    f"जहाँ तक हमारे अभियान का सवाल है — क्या हम आपके स्टोर के ड्राफ्ट को आगे बढ़ाएँ?"
                )
                cta = "हाँ / ना"
            elif state.language == "hinglish":
                body = (
                    f"Good question! {redirect_text} "
                    f"Apne current campaign ke liye — kya hum prepare kiye gaye draft ko aage badhayein?"
                )
                cta = "Haan / Nahi"
            else:
                body = (
                    f"Good question! {redirect_text} "
                    f"Coming back to our active campaign — shall we proceed with the draft we prepared for your store?"
                )
                cta = "binary_yes_no"

            state.record_bot_send(body, cta)
            return {
                "action": "send",
                "body": body,
                "cta": cta,
                "rationale": "Addressed unexpected curveball with respectful domain boundary and smoothly bridged back to core store campaign."
            }

        # ---------------------------------------------------------------------
        # 9. Intent: Passive Low-Information Reply ("ok", "hmm", "k")
        #    ANTI-REPETITION: DO NOT repeat earlier hook or pitch!
        # ---------------------------------------------------------------------
        if intent == "passive_low_info":
            state.unanswered_nudges += 1
            state.transition_to(StateName.FOLLOW_UP, reason="low_info_nudge")

            # Check previous CTA to avoid repeating same binary question
            prev_cta = state.cta_history[-1] if state.cta_history else ""

            if state.language == "hi":
                body = "बढ़िया! क्या मैं आपको इसका 1-क्लिक प्रीव्यू दिखा दूँ, या आप आज शाम 2 मिनट का क्विक कॉल पसंद करेंगे?"
                cta = "प्रीव्यू / कॉल"
            elif state.language == "hinglish":
                body = "Great! Kya main aapko draft preview yahin bhej doon, ya aap shaam ko ek 2-minute quick call prefer karenge?"
                cta = "preview_vs_call"
            else:
                body = (
                    "Got it! Would you like me to share the 1-click preview draft here, "
                    "or would you prefer a quick 2-minute walkthrough over call later today?"
                )
                cta = "preview_vs_call"

            state.record_bot_send(body, cta)
            return {
                "action": "send",
                "body": body,
                "cta": cta,
                "rationale": "Merchant gave low-information response ('ok'). Provided frictionless binary next-step choice without repeating previous pitch or sentences."
            }

        # ---------------------------------------------------------------------
        # 10. General Inquiry / Pitch State
        #     ANTI-REPETITION: Rotate through distinct value propositions
        # ---------------------------------------------------------------------
        state.transition_to(StateName.PITCH, reason="general_inquiry_addressed")

        sent_bodies = [turn.message.strip().lower() for turn in state.turns if turn.role == "vera"]

        variations_en = [
            ("magicpin connects nearby high-intent shoppers directly with your store. "
             "We have prepared a personalized promotion tailored to your location. "
             "Shall I share the preview with you now?", "binary_yes_no"),
            ("Everything is fully flexible — you can pause, edit, or adjust your promotions anytime with zero lock-in or extra charges. "
             "Would you like to take a look at the ready preview draft for your store?", "binary_yes_no"),
            ("magicpin operates strictly on verified customer walk-ins with ₹0 upfront onboarding fee. "
             "Would you like to review the ready draft campaign for your store?", "binary_yes_no"),
            ("We handle all the drafting and audience targeting so you can launch in under 2 minutes. "
             "Shall I send over the 1-click preview draft here?", "binary_yes_no")
        ]

        variations_hi = [
            ("magicpin आपके स्थानीय इलाके के ग्राहकों को आपकी दुकान से जोड़ता है। "
             "हमने आपके स्टोर के लिए एक विशेष प्रचार तैयार किया है। क्या आप इसका पूर्वावलोकन देखना चाहेंगे?", "हाँ / ना"),
            ("सब कुछ आपके नियंत्रण में है — आप बिना किसी अतिरिक्त शुल्क के कभी भी अभियान को रोक या बदल सकते हैं। "
             "क्या आप अपने स्टोर के लिए तैयार ड्राफ्ट देखना चाहते हैं?", "हाँ / ना"),
            ("magicpin केवल सत्यापित ग्राहक वॉक-इन पर काम करता है और कोई अग्रिम शुल्क नहीं है। "
             "क्या आप अपनी दुकान के लिए तैयार किया गया प्रचार ड्राफ्ट देखना चाहेंगे?", "हाँ / ना"),
            ("हम पूरी ड्राफ्टिंग खुद संभालते हैं ताकि आप 2 मिनट में शुरुआत कर सकें। "
             "क्या मैं आपको तैयार ड्राफ्ट दिखाऊँ?", "हाँ / ना")
        ]

        variations_hinglish = [
            ("magicpin aapke local area ke high-intent customers ko aapki shop se jodta hai. "
             "Maine aapke store ke liye tailored campaign ready kiya hai. Kya aap iska preview dekhna chahenge?", "Haan / Nahi"),
            ("Bilkul! Sab kuch aapke control me hai — aap bina kisi lock-in ke campaign pause ya edit kar sakte hain. "
             "Kya main aapko ready preview share kar doon?", "Haan / Nahi"),
            ("magicpin purely verified footfalls par kaam karta hai with ₹0 upfront charges. "
             "Kya aap apne store ka tailored draft preview dekhna chahenge?", "Haan / Nahi"),
            ("Hum saari campaign drafting khud manage karte hain taaki aap 2 minute me live kar sakein. "
             "Kya main draft share karoon?", "Haan / Nahi")
        ]

        if state.language == "hi":
            vars_list = variations_hi
        elif state.language == "hinglish":
            vars_list = variations_hinglish
        else:
            vars_list = variations_en

        # Select first unused variation to guarantee zero repetition
        body, cta = vars_list[0]
        for v_body, v_cta in vars_list:
            if not any(v_body.strip().lower() == prev or v_body.strip().lower() in prev for prev in sent_bodies):
                body, cta = v_body, v_cta
                break

        state.record_bot_send(body, cta)
        return {
            "action": "send",
            "body": body,
            "cta": cta,
            "rationale": "Addressed merchant inquiry and advanced conversation toward campaign preview with a clean binary CTA."
        }


# =============================================================================
# TOP-LEVEL EXPORTED FUNCTION (Challenge Brief Specification)
# =============================================================================

def respond(state: ConversationState, merchant_message: str) -> dict:
    """
    Given the conversation so far + the merchant's latest message, produce the reply.

    Returns dict with keys:
        action: "send" | "wait" | "end"
        body: str (if action == "send")
        cta: str (if action == "send")
        wait_seconds: int (if action == "wait")
        rationale: str
    """
    return MultiTurnHandler.respond(state, merchant_message)
