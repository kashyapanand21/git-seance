
## 2026-10-28: P0 venv creation failed

- **What:** `py -3.11 -m venv .venv` printed "No suitable Python runtime found". Activate then failed, and `pip install` ran against the global Python.
- **Why:** I assumed Python 3.11 was installed without checking.
- **Fix:** Run `python --version` and `py -0` first, then create the venv from a Python that is 3.11 or higher. Confirm the `(.venv)` prefix before installing anything.
