#!/usr/bin/env python3
"""
Test composition across all 30 canonical test pairs in dataset/expanded/test_pairs.json
"""

import sys
import io
import json
from pathlib import Path

# Configure utf-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from bot import compose

EXPANDED_DIR = Path(__file__).parent / "dataset" / "expanded"

def load_expanded_data():
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

def test_all_30():
    print("Loading expanded dataset...")
    categories, merchants, customers, triggers, test_pairs = load_expanded_data()
    print(f"Loaded {len(categories)} categories, {len(merchants)} merchants, {len(customers)} customers, {len(triggers)} triggers.")
    print(f"Testing all {len(test_pairs)} canonical test pairs (T01 - T30)...\n")

    for pair in test_pairs:
        test_id = pair["test_id"]
        trg_id = pair["trigger_id"]
        m_id = pair["merchant_id"]
        c_id = pair.get("customer_id")

        trigger = triggers[trg_id]
        merchant = merchants[m_id]
        cat_slug = merchant["category_slug"]
        category = categories[cat_slug]
        customer = customers.get(c_id) if c_id else None

        res = compose(category, merchant, trigger, customer)

        # Validation assertions
        assert "body" in res and isinstance(res["body"], str) and len(res["body"]) > 20
        assert "cta" in res and isinstance(res["cta"], str)
        assert "send_as" in res and res["send_as"] in ("vera", "merchant_on_behalf")
        assert "suppression_key" in res and isinstance(res["suppression_key"], str)
        assert "rationale" in res and isinstance(res["rationale"], str)

        if customer:
            assert res["send_as"] == "merchant_on_behalf", f"Test {test_id} has customer but send_as={res['send_as']}"
        else:
            assert res["send_as"] == "vera", f"Test {test_id} has no customer but send_as={res['send_as']}"

        assert "http://" not in res["body"] and "https://" not in res["body"]

        print(f"[{test_id}] {trg_id[:35]:35} | send_as={res['send_as']:18} | cta={res['cta']:18} | body_len={len(res['body']):3}")

    print("\nALL 30 CANONICAL TEST PAIRS COMPOSED AND VALIDATED SUCCESSFULLY!")

if __name__ == "__main__":
    test_all_30()
