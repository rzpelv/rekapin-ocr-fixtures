#!/usr/bin/env python3
"""Generate the synthetic BCA-style statement fixtures for Rekapin.

Single source of truth for both PDFs and the expected-parse JSON files.
All data is fake: fake names, fake account number, fake amounts.

Requires PyMuPDF (pip install PyMuPDF) to build the PDFs.
Run:  python3 fixtures/generate_fixtures.py
"""

import json
import os

import fitz  # PyMuPDF

HERE = os.path.dirname(os.path.abspath(__file__))
EXPECTED_DIR = os.path.join(HERE, "expected")

OPENING_BALANCE = 12_500_000

# (date, description, debit, credit, print_balance?)
# Balance is computed from the chain; `print_balance` marks the rows where
# the (BCA-style) statement actually prints the running balance.
TXNS = [
    ("2026-01-02", "TRF E-BANKING CR 02012026 PT MAJU BERSAMA", 0, 3_750_000, True),
    ("2026-01-03", "PEMBAYARAN TOKOPEDIA", 485_000, 0, False),
    ("2026-01-05", "TARIK TUNAI ATM BCA SUDIRMAN", 1_000_000, 0, False),
    ("2026-01-06", "TRF E-BANKING DB 06012026 BUDI SANTOSO", 2_250_000, 0, True),
    ("2026-01-08", "SETOR TUNAI CDM", 0, 5_000_000, False),
    ("2026-01-09", "PEMBAYARAN LISTRIK PLN", 312_500, 0, False),
    ("2026-01-10", "TRF E-BANKING CR 10012026 CV SINAR ABADI", 0, 8_400_000, True),
    ("2026-01-12", "TARIK TUNAI ATM", 500_000, 0, False),
    ("2026-01-13", "PEMBAYARAN SHOPEE", 175_000, 0, False),
    ("2026-01-14", "BIAYA ADMIN", 15_000, 0, True),
    ("2026-01-15", "TRF E-BANKING CR 15012026 PT NUSANTARA JAYA", 0, 4_600_000, False),
    ("2026-01-16", "PEMBAYARAN INTERNET", 299_000, 0, False),
    ("2026-01-18", "TARIK TUNAI ATM", 2_000_000, 0, True),
    ("2026-01-20", "TRF E-BANKING DB 20012026 DEWI LESTARI", 1_500_000, 0, False),
    ("2026-01-21", "SETOR TUNAI", 0, 2_000_000, False),
    ("2026-01-22", "PEMBAYARAN KARTU KREDIT", 1_250_000, 0, True),
    ("2026-01-24", "TRF E-BANKING CR 24012026 PT CAHAYA BARU", 0, 6_300_000, False),
    ("2026-01-26", "TARIK TUNAI ATM", 750_000, 0, True),
]

# Row 7 (1-based) is the corrupted row in the corrupted variant:
# Kredit 8.400.000 misread as 3.400.000 (single-digit OCR confusion, 8 -> 3).
# The printed Saldo on that row stays correct, so the balance chain breaks.
CORRUPTED_ROW = 7
CORRUPTED_CREDIT = 3_400_000


def idr(n):
    """Format an integer amount Indonesian-style: 12500000 -> '12.500.000'."""
    return f"{n:,}".replace(",", ".")


def build_rows(corrupted=False):
    """Return the transaction list with balances.

    Printed balances ALWAYS come from the true chain. In the corrupted
    variant only the Kredit amount on row 7 changes (the OCR misread);
    the Saldo column is read correctly, so the chain breaks at that row.
    """
    rows = []
    running = OPENING_BALANCE
    for i, (date, desc, debit, credit, printed) in enumerate(TXNS, 1):
        running = running - debit + credit
        rows.append({
            "row": i,
            "date": date,
            "description": desc,
            "debit": debit,
            "credit": credit,
            "balance": running,
            "balance_printed": running if printed else None,
        })
    if corrupted:
        # Only the amount is misread; printed balances stay true.
        rows[CORRUPTED_ROW - 1]["credit"] = CORRUPTED_CREDIT
    return rows


def build_pdf(path, rows, corrupted=False):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    x0, x1 = 40, 555
    y = 48

    def text(s, size=10, bold=False, x=x0, ypos=None, align_left=True):
        nonlocal y
        yy = ypos if ypos is not None else y
        font = "hebo" if bold else "helv"
        if align_left:
            page.insert_text((x, yy), s, fontsize=size, fontname=font)
        else:
            tw = fitz.get_text_length(s, fontsize=size, fontname=font)
            page.insert_text((x - tw, yy), s, fontsize=size, fontname=font)
        return yy

    text("REKENING KORAN  —  SYNTHETIC TEST FIXTURE", size=14, bold=True)
    y = 66
    text("BCA-style layout  •  ALL DATA IS FAKE  •  generated for parser testing", size=9)
    y = 80
    if corrupted:
        text("CORRUPTED TEST VARIANT — row 7 Kredit misread 8.400.000 -> 3.400.000;",
             size=9, bold=True)
        y = 94
        text("the Saldo column is unchanged, so the balance chain breaks at that row.",
             size=9, bold=True)
        y = 108
    page.draw_line((x0, y), (x1, y))

    y += 20
    text("No. Rekening : 1234567890", size=10)
    y += 15
    text("Nama         : BUDI CONTOH", size=10)
    y += 15
    text("Periode      : 01 Jan - 31 Jan 2026", size=10)
    y += 15
    text("Mata Uang    : IDR", size=10)
    y += 15
    text(f"Saldo Awal   : {idr(OPENING_BALANCE)}", size=10, bold=True)

    # Table header
    y += 26
    page.draw_rect(fitz.Rect(x0, y - 12, x1, y + 4), color=(0, 0, 0), fill=(0.85, 0.85, 0.85))
    text("Tanggal", size=9, bold=True, ypos=y)
    text("Keterangan", size=9, bold=True, x=115, ypos=y)
    text("Debit", size=9, bold=True, x=430, ypos=y, align_left=False)
    text("Kredit", size=9, bold=True, x=500, ypos=y, align_left=False)
    text("Saldo", size=9, bold=True, x=555, ypos=y, align_left=False)

    y += 18
    for r in rows:
        d, m, yy = r["date"].split("-")[2], r["date"].split("-")[1], r["date"].split("-")[0]
        text(f"{d}/{m}/{yy}", size=9, ypos=y)
        text(r["description"], size=9, x=115, ypos=y)
        if r["debit"]:
            text(idr(r["debit"]), size=9, x=430, ypos=y, align_left=False)
        if r["credit"]:
            text(idr(r["credit"]), size=9, x=500, ypos=y, align_left=False)
        if r["balance_printed"] is not None:
            text(idr(r["balance_printed"]), size=9, x=555, ypos=y, align_left=False)
        y += 17

    closing = rows[-1]["balance"]
    y += 8
    page.draw_line((x0, y), (x1, y))
    y += 18
    text(f"Saldo Akhir  : {idr(closing)}", size=10, bold=True)
    y += 30
    text("Synthetic fixture — Rekapin OCR pipeline test data.", size=8)
    y += 12
    text("No real person, account, or statement is represented here.", size=8)

    doc.save(path)
    doc.close()


def build_json(path, rows, corrupted=False):
    data = {
        "synthetic": True,
        "fixture": "bca-statement-corrupted" if corrupted else "bca-statement",
        "account": "1234567890",
        "holder": "BUDI CONTOH",
        "period": "2026-01-01 to 2026-01-31",
        "currency": "IDR",
        "opening_balance": OPENING_BALANCE,
        "closing_balance": rows[-1]["balance"],
        "note": ("BCA-style layout: the Saldo column is printed on only some rows. "
                 "Blank rows must be filled from the running balance chain."),
        "transactions": [
            {
                "row": r["row"],
                "date": r["date"],
                "description": r["description"],
                "debit": r["debit"],
                "credit": r["credit"],
                "balance_printed": r["balance_printed"],
            }
            for r in rows
        ],
    }
    if corrupted:
        data["corruption"] = {
            "row": CORRUPTED_ROW,
            "field": "credit",
            "true_value": 8_400_000,
            "corrupted_value": CORRUPTED_CREDIT,
            "note": ("Single-digit OCR misread (8 -> 3). The printed Saldo on the "
                     "row is unchanged, so the balance chain breaks exactly here."),
        }
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    os.makedirs(EXPECTED_DIR, exist_ok=True)

    clean_rows = build_rows(corrupted=False)
    build_pdf(os.path.join(HERE, "bca-statement-synthetic.pdf"), clean_rows)
    build_json(os.path.join(EXPECTED_DIR, "bca-statement.json"), clean_rows)
    print(f"clean fixture: {len(clean_rows)} txns, closing "
          f"{idr(clean_rows[-1]['balance'])}")

    bad_rows = build_rows(corrupted=True)
    build_pdf(os.path.join(HERE, "bca-statement-corrupted.pdf"), bad_rows, corrupted=True)
    build_json(os.path.join(EXPECTED_DIR, "bca-statement-corrupted.json"),
               bad_rows, corrupted=True)
    print(f"corrupted fixture: row {CORRUPTED_ROW} credit "
          f"{idr(8_400_000)} -> {idr(CORRUPTED_CREDIT)}")


if __name__ == "__main__":
    main()
