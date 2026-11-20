#!/usr/bin/env python3
"""Balance-chain verification demo for the Rekapin synthetic fixtures.

Stdlib only. Run:  python3 test_balance_chain.py

The problem (real, from BCA statements): the running balance (Saldo) is
printed on only SOME rows. The parser must:

  1. Fill the blank rows from the balance chain:
     balance = previous balance - debit + credit.
  2. Treat every printed balance as an anchor: the computed chain must
     match it, within tolerance.
  3. Flag a row whose amount breaks the chain instead of silently
     accepting it — a single OCR misread (e.g. 8 -> 3, O -> 0, S -> 5)
     shifts every balance after it.

Tolerance per anchor check: max(5% of the printed balance, Rp 100.000).
The tolerance absorbs small drifts (e.g. unlisted admin fees); a real
misread produces a far larger gap.

After a flagged row, the chain resyncs to the printed balance (anchor
reconciliation), so one bad amount does not cascade into false flags.

Expected results:
  - bca-statement.json            -> 0 flagged rows (clean chain)
  - bca-statement-corrupted.json  -> exactly 1 flagged row (row 7)
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPECTED_DIR = os.path.join(HERE, "fixtures", "expected")

TOLERANCE_PCT = 0.05
TOLERANCE_MIN = 100_000  # Rp


def verify(data):
    """Walk the chain, fill blank balances, flag anchor mismatches.

    Returns (filled, flagged):
      filled  — transactions with a computed 'balance' on every row
      flagged — rows whose computed balance disagrees with the printed
                balance beyond tolerance
    """
    running = data["opening_balance"]
    filled, flagged = [], []
    for tx in data["transactions"]:
        running = running - tx["debit"] + tx["credit"]
        printed = tx.get("balance_printed")
        row = dict(tx)
        row["balance_computed"] = running
        row["balance"] = printed if printed is not None else running
        if printed is not None:
            tolerance = max(TOLERANCE_PCT * printed, TOLERANCE_MIN)
            if abs(running - printed) > tolerance:
                flagged.append({
                    "row": tx["row"],
                    "date": tx["date"],
                    "description": tx["description"],
                    "computed": running,
                    "printed": printed,
                    "difference": running - printed,
                    "tolerance": tolerance,
                })
            # Anchor reconciliation: resync to the printed balance.
            running = printed
        filled.append(row)
    return filled, flagged


def idr(n):
    return f"Rp {n:,}".replace(",", ".")


def check(filename, expect_flag_rows):
    path = os.path.join(EXPECTED_DIR, filename)
    with open(path) as f:
        data = json.load(f)
    filled, flagged = verify(data)
    n_filled = sum(1 for tx in data["transactions"]
                   if tx.get("balance_printed") is None)
    print(f"\n{filename}")
    print(f"  {len(filled)} transactions, "
          f"{n_filled} blank balances filled from the chain")
    if flagged:
        for fl in flagged:
            print(f"  FLAGGED row {fl['row']} ({fl['date']}): "
                  f"computed {idr(fl['computed'])} vs printed "
                  f"{idr(fl['printed'])} "
                  f"(diff {idr(fl['difference'])}, "
                  f"tolerance {idr(int(fl['tolerance']))})")
            print(f"    {fl['description']}")
    else:
        print("  no rows flagged — chain matches every printed anchor")
    got = [fl["row"] for fl in flagged]
    ok = got == expect_flag_rows
    print(f"  expected flags {expect_flag_rows}, got {got} -> "
          f"{'PASS' if ok else 'FAIL'}")
    return ok


def main():
    ok = True
    ok &= check("bca-statement.json", [])
    ok &= check("bca-statement-corrupted.json", [7])
    print("\n" + ("ALL CHECKS PASSED" if ok else "CHECKS FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
