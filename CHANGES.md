# CHANGES

## 2026-06-24

### 1) Fixed benchmark script duplication/syntax issue and stabilized graph generation
- Changed files:
  - `Teams com/tests/performance_test.py`
  - `Teams com/requirements-dev.txt`
- Commands run:
  1. `& "c:/Users/t-aftabkhan/OneDrive - Microsoft/Desktop/Aftab Khan - FinalYearProject/venv/Scripts/python.exe" tests/performance_test.py`
  2. `& "c:/Users/t-aftabkhan/OneDrive - Microsoft/Desktop/Aftab Khan - FinalYearProject/venv/Scripts/python.exe" -m pip install --upgrade matplotlib`
  3. `& "c:/Users/t-aftabkhan/OneDrive - Microsoft/Desktop/Aftab Khan - FinalYearProject/venv/Scripts/python.exe" tests/performance_test.py`
- Real observed result:
  - Benchmark completed successfully after fixes and matplotlib upgrade.
  - Artifacts produced in `Teams com/tests/artifacts/performance/`:
    - `raw_before.json`, `raw_after.json`
    - `summary_before.csv`, `summary_after.csv`
    - `comparison.csv`
    - `performance_comparison.png`
  - Measured means from `comparison.csv`:
    - Transcript Insertion: 0.070133 -> 0.160547 ms
    - Transcript Retrieval: 2.548656 -> 0.074132 ms
    - Message Creation: 0.118651 -> 0.156045 ms
    - Message Search: 5.695748 -> 0.057663 ms
    - Notification Creation: 0.033792 -> 0.114203 ms
    - Call Creation: 0.042477 -> 0.073992 ms
    - Summary Generation: 18.086055 -> 4.174372 ms

### 2) Fixed pytest suite fixture and attendance-login issues
- Changed files:
  - `Teams com/tests/conftest.py`
  - `Teams com/tests/test_first_class_suite.py`
- Command run:
  - `& "c:/Users/t-aftabkhan/OneDrive - Microsoft/Desktop/Aftab Khan - FinalYearProject/venv/Scripts/python.exe" -m pytest tests/test_first_class_suite.py --cov=app --cov-report=term-missing --cov-report=xml`
- Real observed result:
  - `7 passed`.
  - Coverage report generated: `Teams com/coverage.xml`.
  - Total coverage (from terminal output): `42%` for `app` package.

### 3) Rewrote dissertation sections to remove unsupported claims and align to executable evidence
- Changed file:
  - `finalReporr plan.md`
- What was updated:
  - Removed unsupported face-recognition accuracy/training metrics and replaced with implementation-truth section.
  - Corrected wellbeing implementation description to embedded external chatbot integration.
  - Replaced Section 7.3 numeric claims with exact measured benchmark artifact values.
  - Replaced non-executed test matrix claims with automated tests actually run.
  - Updated MoSCoW priority summary and figure/table wording to match current evidence.

### 4) Recalculated report word count from current file
- Command run:
  - `((Get-Content -Raw "finalReporr plan.md") | Select-String -AllMatches "[A-Za-z0-9']+").Matches.Count`
- Real observed result:
  - `15264`
- Applied update:
  - Top-level word count in `finalReporr plan.md` set to `15,264`.
