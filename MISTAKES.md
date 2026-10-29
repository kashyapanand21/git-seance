## 2026-10-28: P0 venv creation failed

- **What:** `py -3.11 -m venv .venv` printed "No suitable Python runtime found". Activate then failed, and `pip install` ran against the global Python.
- **Why:** I assumed Python 3.11 was installed without checking.
- **Fix:** Run `python --version` and `py -0` first, then create the venv from a Python that is 3.11 or higher. Confirm the `(.venv)` prefix before installing anything.

## 2026-10-28: P2 test failures

- **Porcelain assertion:** `fix not in plain` failed because `blame --porcelain` prints a `previous <sha>` line. Fix: check only the first line's sha.
- **Tie in blame majority:** a 2-line hunk split 1:1 between fix and reformat, so the test did not exercise "reformat wins". Fix: 3-line hunk where the reformat owns 2 lines.
- **`git log -L` oldest = file creation:** `-L` walks back to the file's first commit, not the commit that added the lines. Decision: dropped from the fallback chain (R3 deviation, approved as option A). `log_l` is kept and tested only to document the limit.Decision pending (A: drop from chain, B: keep with caveat

## 2026-10-28: P6 Ollama crashed on GPU

- **What:** `gemma4:e4b` and `gemma3:12b` returned HTTP 500 (`CUDA error: shared object initialization failed`, exit 0xc0000409). My first guess (curl quoting) was wrong.
- **Why (likely, not proven):** RTX 4050 has 6 GB VRAM; both crashing models are larger. `qwen2.5:3b` fits and worked.
- **Fix:** `SEANCE_NUM_GPU=0` forces CPU. gemma4:e4b also "thinks" by default, so we send `think: false`.
