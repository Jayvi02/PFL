# UPF Loan Manager

An offline Windows desktop app that replaces the `PF LOAN Calculation.xlsx` workbook for University Provident Fund loan renewals. You keep employee records, work out each person's loan with the workbook's formulas, build the monthly renewal list, and export it for UGC as the text file and the printed sheet.

Built with Python 3.12, PySide6 (Qt), SQLite, SQLAlchemy and Alembic, openpyxl, ReportLab and pytest, and packaged with PyInstaller. There is no login: the app opens straight to the dashboard, and the audit log records the Windows account name.

## Run it from source

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/), a single-file Python manager.
2. In the repository folder, run:

```bat
uv venv -p 3.12 .venv
uv pip install -p .venv -e ".[dev]"
.venv\Scripts\python -m upf_loans
```


## Build the Windows program

GitHub builds it automatically on every change to `main`. The first time, download `UPFLoanManager-windows.zip` from the [latest release](https://github.com/Jayvi02/PFL/releases/tag/latest), unzip it somewhere you own (for example `C:\UPFLoanManager`), and run `UPFLoanManager.exe`. After that, the app checks GitHub when it starts; when a newer build exists an **Update available** button appears at the top. **Settings → Check for updates** does the same check any time, and **Download and install** updates the app (a backup is made first; your data is not touched).

Each GitHub build is numbered `1.0.<build number>`. The number is shown at the bottom of the sidebar and in Settings → Updates, so after an update you can see it changed.

To build it yourself instead, run `packaging\build_windows.bat`. It runs the tests, builds `dist\UPFLoanManager\UPFLoanManager.exe`, then runs the exe's `--self-test` check. Copy the whole `dist\UPFLoanManager` folder to the office PC. Nothing needs to be installed there.

Your data is kept on the computer that runs the app, in `%LOCALAPPDATA%\UPFLoans` by default, never in the program folder. **Settings → Backup & restore → Move data folder…** copies it to another folder (for example `D:\UPFLoans` or a drive that IT backs up) and uses that from then on; the choice is remembered in `%LOCALAPPDATA%\UPFLoans\data-location.txt`. The data folder holds:

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

The text file is the "PF LOAN send UGC" sheet saved the way Excel's **Text (Tab delimited)** option saves it, which is what UGC has been receiving. Fields are separated by tabs:

1. the title (`RENEWAL OF U.P.F. LOAN - APPLICATION FOR THE MONTH OF  …`) and the university name
2. the column headings
3. one row per employee: serial number, name, PF number, NIC, request month and year, last loan month and year, the three amounts as `000000000000.00`, and the university code
4. the totals row, two blank lines, then the signatory, the university name and the letter date

Every row must also fit the UGC field limits from the "new format2007" sheet: name up to 50 characters, PF number up to 8, NIC exactly 10 (9 digits followed by V or X), and amounts that are not negative. If any row breaks a limit, no file is written and the screen lists every row that needs fixing. Lines end in Windows CRLF by default; you can change this in Settings.

## Project layout

```
src/upf_loans/
  core/       calculation, UGC text format, money and validation (no database or UI)
  db/         SQLAlchemy models, session and Alembic migrations
  services/   employees, renewals, settings, audit log, backup, import, exports
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
