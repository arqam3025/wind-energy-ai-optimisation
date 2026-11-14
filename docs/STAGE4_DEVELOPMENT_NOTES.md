# Stage 4 development notes: Kelmarsh real data

**Study role:** REAL_DATA_DEVELOPMENT (2018–2021 only). The validation year (2022) and the sealed
test years (2023–2024) have not been opened.

## Round 0: data facts (2026-11-14)

Source files: turbine 1 (`Turbine_Data_Kelmarsh_1_*`), read directly from the verified archives.

| Year | Rows | First → last timestamp | Irregular steps | Power missing | Power range (kW) | Mean (kW) | Downtime/curtailment rows | Ramps > 200 kW | 95th-percentile ramp (kW) |
|---|---|---|---|---|---|---|---|---|---|
| 2018 | 52,560 | 00:00 Jan 1 → 23:50 Dec 31 | 0 | 3.4% | −16 … 2080 | 602 | 4.3% | 12.7% | 327 |
| 2019 | 52,560 | same | 0 | 0.2% | −18 … 2081 | 604 | 1.0% | 13.6% | 334 |
| 2020 | 52,704 | same | 0 | 0.9% | −16 … 2079 | 716 | 1.9% | 14.1% | 341 |
| 2021 | 52,560 | same | 0 | 1.0% | −17 … 2076 | 554 | 3.1% | 11.6% | 312 |

Answers to the open questions in `DATA_ADMISSION_KELMARSH.md`:

1. **Timezone: UTC**, stated in each file header ("Time zone: UTC").
2. **Interval labelling: start of interval.** This is inferred, because each yearly file is
   declared as `[YYYY-01-01 00:00, YYYY+1-01-01 00:00)` and runs 00:00 → 23:50. The label t
   therefore denotes the mean over [t, t+10 min), and that value becomes available at t + 10 min
   at the earliest. The Stage 2/3 convention (target time = end of interval) maps as
   target_time = label + 10 min.
3. **Signal:** `Power (kW)`, the 10-minute mean active power. Small negative values are auxiliary
   consumption; the target is y = max(0, P), consistent with `docs/METHODS.md`.
4. **Flags:** `Lost Production to Downtime and Curtailment Total (kWh)` and the per-cause columns
   are present for exclusion rules.
5. **Scale:** each turbine is a Senvion MM92 rated at 2.05 MW (static metadata), essentially the
   2 MW turbine of the synthetic generator. The single-turbine study therefore keeps the battery
   (2 MWh, ±1 MW) and the ramp reference (200 kW per 10 min) unchanged, with no rescaling. This
   decision is to be confirmed in the Stage 4 protocol.

Observation: the real ramp frequency (12–14% of intervals above 200 kW) is of the same order as
in the synthetic generator, so ramp control is a meaningful task on real data.
