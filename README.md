# UPF Loan Manager

An offline Windows desktop app that replaces the `PF LOAN Calculation.xlsx` workbook for University Provident Fund loan renewals. You keep employee records, work out each person's loan with the workbook's formulas, build the monthly renewal list, and export it for UGC as the fixed-width text file and the printed sheet.

Built with Python 3.12, PySide6 (Qt), SQLite, SQLAlchemy and Alembic, openpyxl, ReportLab, Argon2 and pytest, and packaged with PyInstaller.

## Run it from source

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/), a single-file Python manager.
2. In the repository folder, run:

```bat
uv venv -p 3.12 .venv
uv pip install -p .venv -e ".[dev]"
.venv\Scripts\python -m upf_loans
```

The first time it starts, it asks you to create the administrator account.

## Build the Windows program

Run `packaging\build_windows.bat`. It runs the tests, builds `dist\UPFLoanManager\UPFLoanManager.exe`, then runs the exe's `--self-test` check. Copy the whole `dist\UPFLoanManager` folder to the office PC. Nothing needs to be installed there.

Your data is kept in `%LOCALAPPDATA%\UPFLoans`, not in the program folder:

- the database: `upf_loans.sqlite3`
- daily automatic backups (the last 30 are kept): `backups\`
- the error log: `upf_loans.log`

## How a loan is calculated

These are the formulas from the workbook's MAIN sheet, applied column by column. The source is `src/upf_loans/core/eligibility.py`. All the numbers shown in **bold** can be changed under **Settings → Loan rules**.

| Step | Excel | Rule |
| --- | --- | --- |
| PF balance | G = E + F | balance at last statement + contributions since then |
| Existing loan | J = H − I | loan balance at cut-off − deductions since then |
| Cap 1 | U | salary × **48** |
| Cap 2 | V | salary balance × **120** |
| Cap 3 | W | PF balance × **0.65** |
| Lowest | X | MIN(U, V, W) |
| Loan ability | Y | X − (Q − PF balance × **0.1**) when Q is above PF balance × 0.1; otherwise X |
| Instalment | Z | INT(Y ÷ **120**), rounded down like Excel |
| Loan approved | AA | instalment × 120 |
| Balance payable | AC | loan approved − existing loan |
| Loan in hand | AG | balance payable − other university loans (K to P) |
| Flag | AD | "< 60%" when salary balance ≤ instalment |

- No interest is charged and there are no monthly contribution records, because the workbook has neither.
- Money is handled as `Decimal` and stored in whole cents, never as floating-point numbers.
- Each saved row keeps a copy of the rule values it was calculated with.

## The UGC text file

Every line is exactly 127 characters, using the field widths from the "new format2007" sheet:

| Field | Width | Format |
| --- | --- | --- |
| Name | 50 | left-aligned, padded with spaces |
| PF number | 8 | left-aligned |
| NIC | 10 | left-aligned |
| Request month / year | 2 / 4 | month zero-padded |
| Last loan month / year | 2 / 4 | month zero-padded; left blank if there is none |
| Loan approved, existing balance, balance payable | 15 each | `000000000000.00` |
| University code | 2 | right-aligned, e.g. ` F` |

Lines end in Windows CRLF by default; you can change this in Settings. NICs are always the 10-character format (9 digits followed by V or X); the app rejects any other format when you save an employee. If any row doesn't fit the file layout, no file is written and the screen lists every row that needs fixing.

## Project layout

```
src/upf_loans/
  core/       calculation, fixed-width format, money and validation (no database or UI)
  db/         SQLAlchemy models, session and Alembic migrations
  services/   employees, renewals, settings, users, audit log, backup, import, exports
  reports/    UGC Excel sheet, calculation workbook, employee list, PDF
  ui/         PySide6 windows, pages, dialogs, widgets and theme
tests/        pytest suite, including the workbook's own rows as test cases
packaging/    PyInstaller spec and Windows build script
```

## Tests

```bat
.venv\Scripts\python -m pytest -q
```

On Linux CI, set `QT_QPA_PLATFORM=offscreen` before running the tests.
