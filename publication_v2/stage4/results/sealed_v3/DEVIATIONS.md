# Deviations: Stage 4 sealed run (protocol d8337ad9…, frozen commit e772ef0)

## D1: the sealed run failed closed at data loading; no results were produced

- **What happened:** on 2026-11-17 at 14:03 UTC the runner started from a clean checkout of
  `e772ef0` (protocol hash verified). At 14:05 the loader refused 2023, because its timestamps are
  not the complete, unique 10-minute grid. That check was designed on 2018–2022, which were all
  exactly one row per interval. No forecasts, episodes, metrics or tests were computed, and no
  power or wind value from 2023–2024 was analysed or viewed.
- **Structural inspection (timestamps only), disclosed:** to diagnose the failure, only the
  timestamp column of the 2023 and 2024 files of all six turbines was read. Findings:
  - every 10-minute interval of each year is present (none missing, none off-grid);
  - each file holds 2,122,200 extra rows on valid timestamps (2,174,760 rows for 52,560 intervals
    in 2023; 2,174,904 for 52,704 in 2024), about 41 rows per timestamp;
  - the header still declares UTC and the full-year interval.
  A second structural check, to see whether the repeated rows are identical, was not run, pending
  the author's decision.
- **Status:** the protocol and its hypotheses are unchanged. Any loader change is a post-freeze
  defect fix and will be recorded here, together with the new commit and run directory.

### D1 continued: diagnosis, author decision, defect fix (2026-11-17)

- **Author decision:** the author approved a second structural check of the sealed files: row
  counts and comparisons only, with no values printed. Findings, for 2023 turbine 1:
  - the files are cumulative exports, written in blocks of 655 rows, each block re-writing all
    earlier rows;
  - each timestamp has at most two distinct row versions, and nothing else;
  - for all 52,400 timestamps with two versions, the only difference is "value → NaN" in every
    differing column. The later copy is an all-NaN blank row.
- **Rule, fixed before any outcome was computed:**
  - each timestamp keeps its single distinct non-blank row;
  - a timestamp with only blank rows is missing (no imputation);
  - two different non-blank rows for one timestamp make the loader refuse.
  The resolved rows are parsed with the same pandas CSV parser as 2018–2022.
- **Verification:** the fixed loader reproduces the development (2021) and validation (2022)
  series, forecasts and training-data hash **bit for bit**. Three new unit tests cover cumulative
  blank copies, blank-only timestamps and conflict refusal (17 tests pass).
- **Protocol:** unchanged, same SHA-256 `d8337ad9…`. Hypotheses, forecasters, controllers,
  margins and analysis are unchanged.
- **Re-run:** the sealed test is run once into `runs/sealed_v2` from a clean checkout of the
  defect-fix commit (recorded in that run's `STARTED.json`). `runs/sealed_v1` is kept as the
  record of the failed-closed attempt.

### D1 continued: second fail-closed stop and corrected implementation (2026-11-17)

- **What happened:** the run into `runs/sealed_v2` (commit `ff939f8`) stopped at 14:20 while
  loading 2023, with "two different non-blank rows for 2023-01-01 00:00:00". No outcome was
  computed. The `ff939f8` rule treated a row as blank only if every field was NaN, but the later
  copies keep the few fields whose values were identical in both versions, so they were not fully
  blank.
- **Corrected implementation, same principle:** the structural check showed that versions differ
  only by value → NaN.
  - The most complete version of each timestamp is kept.
  - The loader refuses if two versions disagree on any non-missing value, or if each has a value
    the other lacks.
  Two further unit tests were added (19 pass). The 2021 and 2022 series, forecasts and training
  hash are again reproduced bit for bit. The protocol is unchanged.
- **Re-run:** into `runs/sealed_v3` from a clean checkout of the corrected commit.
  `runs/sealed_v1` and `runs/sealed_v2` are kept as records of the two fail-closed attempts.
