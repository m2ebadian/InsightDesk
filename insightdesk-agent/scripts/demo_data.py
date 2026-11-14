"""Loads the sample documents and asks a bunch of questions so the Insights page has data.

    python scripts/demo_data.py                       # API on localhost:8000
    python scripts/demo_data.py --spread-days 7       # also spread the questions over the last week

--spread-days edits the SQLite file directly, so only use it on a local demo database.
Needs httpx (pip install httpx).
"""

import argparse
import random
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

# (question, rating) where rating is True/False for helpful/not helpful, or None to leave unrated
QUESTIONS = [
    ("What issues are slowing down the support process?", True),
    ("Which process has the highest number of repeated errors?", True),
    ("How long is the warranty on premium parts?", True),
    ("What should I check before creating a replacement order?", True),
    ("How fast do we need to respond to urgent tickets?", True),
    ("Can customers return opened parts?", True),
    ("What happens if the customer doesn't send the broken part back?", True),
    ("Which month had the lowest customer satisfaction?", None),
    ("When should I escalate a ticket?", True),
    ("Who is building the part number lookup table?", None),
    ("Why do we ship the wrong replacement part?", True),
    ("What should the team prioritize next?", False),
    ("How many vacation days do new hires get?", None),
    ("Is there a discount for bulk orders?", None),
    ("Who should I contact about shipping problems?", True),
    ("What does the refurbished warranty cover?", None),
    ("How do I reset a customer's portal password?", False),
    ("What is the average resolution time for warranty lookups?", None),
]


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--spread-days", type=int, default=0)
    parser.add_argument(
        "--db", default=str(Path(__file__).resolve().parents[1] / "backend/data/insightdesk.db")
    )
    args = parser.parse_args()

    with httpx.Client(base_url=args.url, timeout=30) as client:
        loaded = client.post("/documents/sample").json()
        print(f"Loaded {len(loaded['uploaded'])} sample documents")

        ids = []
        for question, rating in QUESTIONS:
            answer = client.post("/ask", json={"question": question}).json()
            ids.append(answer["id"])
            if rating is not None:
                client.post(f"/questions/{answer['id']}/feedback", json={"helpful": rating})
            print(f"[{answer['confidence']:>6}] {question}")

    if args.spread_days:
        now = datetime.now(UTC)
        with sqlite3.connect(args.db) as conn:
            for question_id in ids:
                when = now - timedelta(
                    days=random.randint(0, args.spread_days - 1), hours=random.randint(0, 8)
                )
                conn.execute(
                    "UPDATE questions SET asked_at = ? WHERE id = ?",
                    (when.isoformat(timespec="seconds"), question_id),
                )
        print(f"Spread {len(ids)} questions over the last {args.spread_days} days")


if __name__ == "__main__":
    main()
