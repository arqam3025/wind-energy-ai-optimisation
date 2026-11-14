# Data admission record: Kelmarsh wind farm SCADA (Stage 4 real-data validation)

**Status:** ADMITTED_FOR_DEVELOPMENT (years 2018–2021) by the study author on 2026-11-14.
Validation year 2022: admitted for a single pre-freeze check. **Test years 2023–2024: SEALED.**
They have been downloaded and MD5-verified, but must not be extracted, read or summarised until
a Stage 4 real-data protocol is frozen and committed.
No independent reviewer decision is claimed. This record documents the author's decision and the
evidence behind it.

## 1. Source and rights

| Item | Value |
|---|---|
| Dataset | Kelmarsh wind farm data |
| Publisher / creators | Cubico Sustainable Investments Ltd; Zenodo creators Plumley, C.; Takeuchi, R. |
| Persistent identifier | DOI 10.5281/zenodo.16807551 (published 2025-08-12) |
| Licence | **CC-BY-4.0** (Zenodo licence field `cc-by-4.0`; record text: released under a CC-BY-4.0 open data license, provided as is) |
| Attribution requirement | Cite the dataset DOI and the creators in any publication or redistribution |
| Site | Kelmarsh, UK; 6 × Senvion MM92 (12.3 MW) |
| Retrieved | 2026-11-14 via the Zenodo REST API; the record metadata is archived at `metadata/zenodo_record_16807551.json` |

CC-BY-4.0 permits reuse, including in publications, with attribution. No other licence
condition is assumed.

## 2. Acquisition and integrity

Script: `publication_v2/stage4/fetch_kelmarsh.sh`, which verifies every file against the MD5
published by Zenodo. Storage is outside git, at `C:/ResearchData/kelmarsh_zenodo_16807551/`
(`metadata/`, `development/`, `validation/`, `sealed_test/`). No raw data is committed or
redistributed.

| Role | File | MD5 (published) |
|---|---|---|
| metadata | Kelmarsh_WT_static.csv | af3a038f0f7fddfc1608ad0bfc8cf5ba |
| metadata | Kelmarsh_WT_dataSignalMapping.csv | ca8fe399ab15ae7111d3214c632efd36 |
| metadata | Kelmarsh_Grid_Meter_4458.zip | 2696caad88ea08ac22e5fa00da9c3c46 |
| development | Kelmarsh_SCADA_2018_3084.zip | 972e5280172216a5fe76dcab19c741b0 |
| development | Kelmarsh_SCADA_2019_3085.zip | 14348a1572b722e1be10e53cd145c39a |
| development | Kelmarsh_SCADA_2020_3086.zip | e189e02da98f32e74acc72e8559ef0db |
| development | Kelmarsh_SCADA_2021_4456.zip | 4e0ef3d65f067fd3d8f3d30e79ab01ae |
| validation | Kelmarsh_SCADA_2022_4457.zip | b695d2b21cd5a236b2e690e0a43df5ab |
| sealed_test | Kelmarsh_SCADA_2023_5961.zip | 685d9589347d1866f6f2cfe45b9af4f4 |
| sealed_test | Kelmarsh_SCADA_2024_5962.zip | e9e3318f5b393d8596ff1801f8da0414 |

Not acquired: 2016–2017 (early and partial years), PMU data.

## 3. Study roles (fixed before any data was opened)

- **Development (2018–2021):** exploratory analysis, data cleaning rules, forecaster training,
  and controller and switch checks on real data.
- **Validation (2022):** one pre-freeze check of the complete pipeline; no design iteration on
  its results beyond fixing defects (any fix is documented).
- **Sealed test (2023–2024):** used only by the frozen Stage 4 protocol, once.

The split was chosen on 2026-11-14 from file names and sizes only, before any file was opened.
Prior exposure: this project has not previously used Kelmarsh data. The dataset is public and
widely used by others, so this record claims **author non-exposure only**, not that the data is
untouched in general.

## 4. Open questions to resolve during development (from the documentation and the 2018–2021 data only)

1. Timestamp timezone, and whether a 10-minute row is labelled by the start or the end of its
   interval (determines causal alignment).
2. Which power signal to use (active power average, kW) and how it relates to the grid meter.
3. Curtailment, downtime and availability flags, and the exclusion rules (fixed on development
   data and applied unchanged to the test years).
4. Farm-level aggregation (sum of 6 turbines) versus a single turbine, and the scaling of the
   battery and ramp limit to the chosen level (decided on development data, recorded in the protocol).
5. Gaps and missing intervals: the policy is no imputation; affected decisions are skipped and
   counted.
6. Data available at decision time (operational latency assumption), stated explicitly.

## 5. Second site: Kaggle T1 (Berker Isen)

This site remains **PENDING_REVIEW** under `docs/DATA_GOVERNANCE.md`. Before admission, the author
must confirm the licence stated on the Kaggle dataset page and record it here, together with the
canonical file identity and the timestamp semantics. Until then it is not used in any Stage 4 result.
