# Rekapin — OCR Fixtures (Public Demo)

[Rekapin](https://rekapin.web.id) turns Indonesian bank e-statements (PDF)
into financial reports: upload a statement, get extracted transactions, AI
categorisation, and an Excel export — plus a BSA (bank statement analysis)
mode for credit analysts.

The production codebase is private. This public repo holds the **synthetic
test fixtures for the OCR scan pipeline** and a standalone demo of the
balance-chain verification the parser relies on.

**All data in this repo is synthetic.** Fake names, fake account numbers,
fake amounts. No real person, account, or statement is represented here.

## The stack

Python + Flask (Gunicorn), self-hosted on Ubuntu behind nginx.
Text extraction with PyMuPDF; scanned PDFs go through pdf2image into
Tesseract and PaddleOCR; Excel export with openpyxl. Vercel builds branch
previews (see `vercel.json`).

## The BCA balance-chain case

BCA statements print the running balance (Saldo) on **only some rows**.
The parser must:

1. **Fill the blank rows** from the balance chain:
   `balance = previous balance − debit + credit`.
2. **Anchor on every printed balance** — the computed chain must match it,
   within tolerance: max(5% of the printed balance, Rp 100.000). The
   tolerance absorbs small drifts (e.g. unlisted admin fees).
3. **Flag a row that breaks the chain** instead of silently accepting it.
   A single OCR misread (`8 → 3`, `O → 0`, `S → 5`, `, → .`) shifts every
   balance after it, so the next printed anchor exposes it. After a flag,
   the chain resyncs to the printed balance (anchor reconciliation).

## Contents

| File | What it is |
| --- | --- |
| `fixtures/bca-statement-synthetic.pdf` | Fake BCA-style statement, 18 transactions, Saldo printed on 7 rows only |
| `fixtures/bca-statement-corrupted.pdf` | Same statement, one Kredit amount misread (8.400.000 → 3.400.000) — the chain breaks at row 7 |
| `fixtures/expected/bca-statement.json` | Expected parse output for the clean fixture |
| `fixtures/expected/bca-statement-corrupted.json` | Expected parse output for the corrupted fixture |
| `fixtures/generate_fixtures.py` | Generator (PyMuPDF) — single source of truth for the PDFs and JSONs |
| `test_balance_chain.py` | Standalone demo of the verification (stdlib only) |
| `vercel.json` | Standard Vercel config for the Flask app (`app.py` entry) |

## Run the demo

```bash
python3 test_balance_chain.py
```

Expected output: the clean fixture passes with 0 flagged rows; the
corrupted fixture flags exactly row 7.

## License

MIT — see `LICENSE`.
