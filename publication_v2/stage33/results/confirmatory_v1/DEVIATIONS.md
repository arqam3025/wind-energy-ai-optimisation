# Deviations from the frozen protocol: confirmatory_v1

## D1: interruption by an operating-system restart, then resumed (protocol Section 7.2)

- **What happened:** the run started on 2026-11-14 at 18:08 from the frozen commit `c59a2c1`.
  Conditions `oracle25` (19:03), `oracle50` (19:48) and `oracle100` (21:52) completed and were
  written atomically. During `oracle150`, Windows Update restarted the computer (System event log
  ID 1074: TrustedInstaller / MoUsoCoreWorker initiated restarts at 00:03–00:08 on 2026-11-15;
  boot at 00:09). The process exited with code 4 and no Python traceback. No partial result file
  was written for `oracle150`.
- **Action:** resumed with the identical command from a clean, detached checkout of the frozen commit
  `c59a2c1` (the runner verifies that the protocol hash and the git head match `STARTED.json`).
  Completed conditions are kept unchanged; missing conditions are computed by the same
  deterministic code.
- **Impact on results:** none expected. Computation is deterministic and independent across
  conditions, and no code, configuration, seed or analysis was changed. No results were inspected
  before the resume; the per-condition files were not opened.

## D2: operating-system standby pauses during the run (no effect on outcomes; timing affected)

- **What happened:** after the resume, the computer entered modern standby several times
  (System event log, Kernel-Power IDs 506/507, between 2026-11-15 03:11 and 2026-11-16 18:28).
  The worker processes were suspended and continued on wake. The run completed on 2026-11-16 at
  22:55 with exit code 0 and all nine condition files checksummed in `COMPLETED.json`.
- **Impact on outcomes:** none. The computation is deterministic and suspension does not change
  any solver input or output.
- **Impact on timing:** the recorded wall-clock computation time per decision includes standby
  periods for the decisions in progress when the machine slept, so the mean and maximum times are
  inflated (maximum episode-mean above 1,000 s). Computation time (protocol Section 6, item 7) is
  therefore reported as the median and 95th percentile only, which are robust to these few
  outliers. Timing was never an outcome of any hypothesis.
