# Data admission record: Hill of Towie wind farm SCADA (Stage 6 third-site confirmation)

**Status:** ADMITTED_FOR_DEVELOPMENT (2016–2023) by the study author on 2026-11-20.
- **Validation year 2024:** admitted for a single pre-freeze check.
- **Test year 2025: SEALED.** It is downloaded and MD5-verified, but must not be read or summarised
  until a Stage 6 protocol is frozen and committed. The only permitted exception is a
  timestamp/row-structure check that prints no values, if the loader fails (as in Kelmarsh D1).
- **2026 (January–April): EXCLUDED.** It is not downloaded and will not be used.

This record was written and committed **before any SCADA data file was opened**. Only the Zenodo
record metadata, the README and the small description/metadata CSVs below were read. No
independent reviewer decision is claimed.

## 1. Source and rights

| Item | Value |
|---|---|
| Dataset | Hill of Towie wind farm open dataset, version 2.0.0 |
| Publisher / creators | RES on behalf of TRIG; Zenodo creators Clerc, A.; Lingkan, E. |
| Persistent identifier | DOI 10.5281/zenodo.20204946 (published 2026-05-18); v1.0.0 is DOI 10.5281/zenodo.14870023 |
| Licence | **CC-BY-4.0** (Zenodo licence field `cc-by-4.0`) |
| Attribution | Cite the DOI and the creators in any publication |
| Site | Hill of Towie, Scotland, UK; 21 × Siemens SWT-2.3-VS-82 (2.3 MW, 59 m hub, 82 m rotor), commercial operation 2012-05-12 |
| Retrieved | 2026-11-20 via the Zenodo REST API |

## 2. Data facts that set the rules (from the README and record description)

- **Timestamps are UTC and mark the END of each 10-minute period.** This already equals the
  project's interval-end convention, so the loader must **not** add 10 minutes. Kelmarsh and
  Penmanshiel label the start, and their loaders do add it.
- **Layout:** each year zip holds monthly CSV tables `{table}_{YYYY}_{MM}.csv`. Turbine rows are
  joined on `StationId` (T01 = 2304510 … T21 = 2304530). The farm grid meter is in
  `tblGridScientific` (`ActivePowerMean`, MW).
- **Interventions that change turbine behaviour:**
  - AeroUp: blade retrofit on T13 (completed 2021-09-29), then all other turbines from 2022-07-14
    to 2023-05-26. It changes the power curve; it is inside the development years and is a feature
    of the data, not an exclusion.
  - TuneUp: control trial on T02, T03, T06, T08, T09, T13, T16, T20 from 2024-03-14 and T21 from
    2024-05-02, ending 2024-08-31. It falls in the validation year and is disclosed. The control
    turbine below is not a TuneUp turbine.
  - **Dynamic Yaw: toggled on and off every 50 minutes on 14 turbines from 2026-01-07** (T16–T21
    from 2026-02-03). That would create artificial ramps, **so all of 2026 is excluded.**
- **LiDAR** data exists only from 2025-08-21, inside the sealed period. It is not used for
  development and is out of scope for Stage 6.

## 3. Roles and units (fixed now, before reading data)

| Role | Years | Use |
|---|---|---|
| development | 2016–2023 | design, feature engineering, model selection, controller tuning |
| validation | 2024 | one pre-freeze defect check, as in Stages 4–5 |
| sealed_test | 2025 | opened once, by the frozen Stage 6 runner only |
| excluded | 2026 | not downloaded; Dynamic Yaw toggling |

- **Turbine-level control unit:** **T10.** It is the turbine closest to the farm centroid
  (57.5054 N, 3.0707 W), so upwind turbines exist for every wind direction, and it is not a TuneUp
  turbine. All other 20 turbines are available as forecast inputs.
- **Farm-level control unit:** the sum of the 21 turbines' 10-minute active power. The grid meter
  (`tblGridScientific.ActivePowerMean`) is used only as a consistency check.
- Battery sizes and ramp references for each unit are design choices. They are made on
  development data only and fixed in the Stage 6 protocol.

Data rules are the same as in Stages 4–5: UTC interval-end index, y = max(0, P), no imputation,
rows absent from a file are missing, and duplicate timestamps are resolved only by an exact or
most-complete-version rule with refusal on conflict.

## 4. Files (MD5 as published by Zenodo; stored outside git at `C:/ResearchData/hill_of_towie_zenodo_20204946/`)

| Role | File | MD5 (published) |
|---|---|---|
| metadata | README.md | 8ed39a082ac77a698e591b1bc9863e1c |
| metadata | Hill_of_Towie_turbine_metadata.csv | bb9673e7adb522b7e15a62f3e7ada6c8 |
| metadata | Hill_of_Towie_tables_description.csv | e138e6caaec5aed652bc8eda727f322b |
| metadata | Hill_of_Towie_turbine_fields_description.csv | d77de82c0b094f0788d4ed9b54ddfdfa |
| metadata | Hill_of_Towie_grid_fields_description.csv | beb450d696fa4aca3572ccf35cf74d7b |
| metadata | Hill_of_Towie_alarms_description.csv | 65117a1d5740da6af2653147be471692 |
| metadata | Hill_of_Towie_AeroUp_install_dates.csv | 6145283b4d93c00b7f614143f6f27972 |
| development | 2016.zip | 74c6807483a6e8c767b9082afff6558d |
| development | 2017.zip | c7cbe0b4d99c69994b95b1c1557ce0a4 |
| development | 2018.zip | 5d3a77aa05c75ea8476cc279a24d48ac |
| development | 2019.zip | ca240b179200f5db25a273a1291eb597 |
| development | 2020.zip | 51b9cd3a98469373302722d1ab8094b7 |
| development | 2021.zip | 86d59d93afab4916bf06949a8986e644 |
| development | 2022.zip | 3861de12eb3ba588f48259c918ade242 |
| development | 2023.zip | 45eceb1855af89cf4dc215f2ab97eda1 |
| validation | 2024.zip | 89783562792fd71fc7a8543faf93ab18 |
| sealed_test | 2025.zip | d3cd7edb535a45ffca1c7028b397f035 |

## 5. Prior exposure

The author has not used Hill of Towie data before. The dataset is public, so only **author
non-exposure** is claimed. The Kelmarsh and Penmanshiel results, including their sealed tests,
informed the Stage 6 design; that is the purpose of a third-site confirmation and will be stated in
the protocol.
