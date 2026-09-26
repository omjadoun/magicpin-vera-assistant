#!/usr/bin/env python3
"""
Inspect and audit all 30 canonical outputs from compose()
"""
import sys
import io
import json
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

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

def inspect_all(start=0, end=30):
    categories, merchants, customers, triggers, test_pairs = load_expanded_data()
    print(f"Total test pairs to audit: {len(test_pairs)} (showing {start} to {end})\n")

    for pair in test_pairs[start:end]:
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

        print(f"============================================================")
        print(f"TEST {test_id} | Trigger: {trigger['kind']} ({trg_id})")
        print(f"Merchant: {merchant['identity']['name']} ({cat_slug}) | Customer: {customer.get('name') if customer else 'None'}")
        print(f"Send As: {res['send_as']} | CTA: {res['cta']}")
        print(f"Suppression Key: {res['suppression_key']}")
        print(f"BODY:\n{res['body']}")
        print(f"RATIONALE:\n{res['rationale']}")
        print()

if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    inspect_all(start, end)
