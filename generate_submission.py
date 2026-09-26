#!/usr/bin/env python3
"""
Generate submission.jsonl for the magicpin AI Challenge
======================================================

Generates exactly 30 lines (T01 - T30) from the canonical test pairs in
dataset/expanded/test_pairs.json by calling the production compose() function.

Zero hardcoding: all responses are dynamically grounded in the active contexts.
"""

import sys
import io
import json
from pathlib import Path

# Ensure UTF-8 output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from bot import compose

EXPANDED_DIR = Path(__file__).parent / "dataset" / "expanded"
OUTPUT_FILE = Path(__file__).parent / "submission.jsonl"


def load_dataset():
    categories = {}
    for f in (EXPANDED_DIR / "categories").glob("*.json"):
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
            categories[data["slug"]] = data

    merchants = {}
    for f in (EXPANDED_DIR / "merchants").glob("*.json"):
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
            merchants[data["merchant_id"]] = data

    customers = {}
    for f in (EXPANDED_DIR / "customers").glob("*.json"):
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
            customers[data["customer_id"]] = data

    triggers = {}
    for f in (EXPANDED_DIR / "triggers").glob("*.json"):
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
            triggers[data["id"]] = data

    with open(EXPANDED_DIR / "test_pairs.json", encoding="utf-8") as fp:
        test_pairs = json.load(fp)["pairs"]

    return categories, merchants, customers, triggers, test_pairs


def generate_submission():
    print(f"Loading data from {EXPANDED_DIR}...")
    categories, merchants, customers, triggers, test_pairs = load_dataset()
    print(f"Loaded {len(test_pairs)} test pairs. Generating {OUTPUT_FILE}...\n")

    lines = []
    seen_ids = set()

    for pair in test_pairs:
        test_id = pair["test_id"]
        trg_id = pair["trigger_id"]
        m_id = pair["merchant_id"]
        c_id = pair.get("customer_id")

        assert test_id not in seen_ids, f"Duplicate test_id: {test_id}"
        seen_ids.add(test_id)

        trigger = triggers[trg_id]
        merchant = merchants[m_id]
        cat_slug = merchant["category_slug"]
        category = categories[cat_slug]
        customer = customers.get(c_id) if c_id else None

        # Execute genuine compose() call
        result = compose(category, merchant, trigger, customer)

        entry = {
            "test_id": test_id,
            "body": result["body"],
            "cta": result["cta"],
            "send_as": result["send_as"],
            "suppression_key": result["suppression_key"],
            "rationale": result["rationale"],
        }
        lines.append(entry)
        print(f"  [COMPOSED] {test_id} ({trigger['kind']}) -> send_as={entry['send_as']}, cta={entry['cta']}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fp:
        for entry in lines:
            fp.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\nSuccessfully generated {OUTPUT_FILE} with {len(lines)} lines.")
    return len(lines)


def validate_submission():
    print(f"\n--- Validating {OUTPUT_FILE} ---")
    assert OUTPUT_FILE.exists(), f"Submission file {OUTPUT_FILE} does not exist!"

    with open(OUTPUT_FILE, "r", encoding="utf-8") as fp:
        raw_lines = [line.strip() for line in fp if line.strip()]

    # 1. Exact line count
    assert len(raw_lines) == 30, f"Expected 30 lines, got {len(raw_lines)}"
    print(f"  [PASS] Line count: {len(raw_lines)} == 30")

    required_keys = {"test_id", "body", "cta", "send_as", "suppression_key", "rationale"}
    valid_send_as = {"vera", "merchant_on_behalf"}
    valid_ctas = {"binary_yes_no", "multi_choice_slot", "open_ended", "binary_confirm_cancel", "none"}
    seen_ids = set()

    for idx, raw in enumerate(raw_lines, 1):
        try:
            entry = json.loads(raw)
        except Exception as e:
            raise AssertionError(f"Line {idx} is invalid JSON: {e}")

        # Required fields
        missing = required_keys - set(entry.keys())
        assert not missing, f"Line {idx} missing required keys: {missing}"

        test_id = entry["test_id"]
        assert test_id == f"T{idx:02d}", f"Expected test_id T{idx:02d}, got {test_id}"
        assert test_id not in seen_ids, f"Duplicate test_id: {test_id}"
        seen_ids.add(test_id)

        # Body checks
        body = entry["body"]
        assert isinstance(body, str) and len(body.strip()) > 30, f"Line {idx} body too short or empty"
        assert "http://" not in body and "https://" not in body, f"Line {idx} contains forbidden URL"

        # CTA checks
        assert entry["cta"] in valid_ctas, f"Line {idx} invalid CTA: {entry['cta']}"

        # Send_as checks
        assert entry["send_as"] in valid_send_as, f"Line {idx} invalid send_as: {entry['send_as']}"

        # Suppression key
        assert entry["suppression_key"] and isinstance(entry["suppression_key"], str), f"Line {idx} missing suppression_key"

        # Rationale
        assert entry["rationale"] and len(entry["rationale"]) > 10, f"Line {idx} rationale too brief"

    print("  [PASS] All 30 lines parsed successfully with valid schema, no URLs, and valid CTAs.")
    print("  [PASS] All test IDs match T01 through T30 with zero duplicates.")


if __name__ == "__main__":
    generate_submission()
    validate_submission()
