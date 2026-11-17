# How to run the project

This guide is for anyone who wants to check the results or reuse the code: an examiner, a
reviewer, or you on a new computer. All commands are run from the repository root, in Git Bash
or another POSIX shell. Tested on Windows 11 with Python 3.12.5.

## 1. Set up (about 5 minutes)

```bash
git clone https://github.com/arqam3025/wind-energy-ai-optimisation.git
cd wind-energy-ai-optimisation
git checkout research/stage4-real-data      # final branch: Stages 3.1–4, results and paper draft
python -m venv .venv
source .venv/Scripts/activate               # macOS/Linux: source .venv/bin/activate
pip install numpy==2.5.4 scipy==1.18.1 pandas==3.0.6 scikit-learn==1.9.1 \
            xgboost==3.4.1 lightgbm==4.7.0 matplotlib==3.11.2
```

## 2. Check that everything works (about 1 minute)

```bash
for d in stage2/tests stage31/tests stage32/tests stage33/tests stage4/tests tests; do
  python -B -m unittest discover -s publication_v2/$d
done
```

Expected: 320 tests (48 + 135 + 32 + 27 + 19 + 59), all passing, with 1 skipped (a Windows
privilege test). Without the Kelmarsh data, one more Stage 4 test is skipped automatically.

## 3. Look at the results (no computation needed)

| What | Where |
|---|---|
| Paper draft | `docs/PAPER_DRAFT.md` |
| Simulation study: protocol and results | `docs/STAGE33_CONFIRMATORY_PROTOCOL.md`, `docs/STAGE33_CONFIRMATORY_RESULTS.md` |
| Real-data study: protocol and results | `docs/STAGE4_CONFIRMATORY_PROTOCOL.md`, `docs/STAGE4_REAL_DATA_RESULTS.md` |
| Figures 1–5 (simulation), Figure 6 (real data) | `docs/figures_stage33_confirmatory/`, `docs/figures_stage4_real_data/` |
| Statistical outputs, run records, deviation logs | `publication_v2/stage33/results/`, `publication_v2/stage4/results/` |
| Development history (everything tried) | `docs/STAGE33_DEVELOPMENT_NOTES.md`, `docs/STAGE4_DEVELOPMENT_NOTES.md` |

## 4. Reproduce the simulation study (about 6–9 hours on 16 cores)

The frozen run must use the frozen commit, and the runner refuses otherwise:

```bash
git worktree add --detach ../frozen-stage33 stage33-protocol-frozen
cd ../frozen-stage33
python -B -m publication_v2.stage33.confirmatory --out runs/confirmatory_repro
python -B -m publication_v2.stage33.confirmatory_analysis runs/confirmatory_repro --out runs/confirmatory_repro/analysis
```

The computation is deterministic. The primary tests should match
`publication_v2/stage33/results/confirmatory_v1/primary_tests.json`.

A quick demonstration on development seeds takes minutes:
`python -B -m publication_v2.stage33.experiment --help`.

## 5. Reproduce the real-data study (about 1.5 hours)

1. Download and verify the Kelmarsh data (CC-BY-4.0, about 20 GB including the sealed years):
   `bash publication_v2/stage4/fetch_kelmarsh.sh <data-folder>`. The default folder is
   `C:/ResearchData/kelmarsh_zenodo_16807551`; edit `ROOT` in `publication_v2/stage4/kelmarsh.py`
   if you use another.
2. Development round (2021):
   `python -B -m publication_v2.stage4.experiment --out runs/dev --stride 1 --prepare`.
   Use `--stride 20` for a quick demonstration of a few minutes.
3. Validation check (2022): add `--stage validation`.
4. Sealed test (2023–2024), from a clean checkout of the code commit used for the results:
   ```bash
   git worktree add --detach ../frozen-stage4 stage4-sealed-loader-fix
   cd ../frozen-stage4
   python -B -m publication_v2.stage4.confirmatory --out runs/sealed_repro
   ```
   The results should match `publication_v2/stage4/results/sealed_v3/tests.json`.
5. Figure 6: `python -B -m publication_v2.stage4.figures runs/sealed_repro/tests.json --out figs`.

## Notes

- Keep the computer awake during long runs. An interrupted run resumes with the same command from
  the same commit, and the interruption must be logged as a deviation.
- Text files must keep LF line endings (the repository uses `* -text`).
- The raw data is not redistributed. Cite the dataset: Plumley, C. & Takeuchi, R., *Kelmarsh wind
  farm data*, Zenodo, DOI 10.5281/zenodo.16807551.
