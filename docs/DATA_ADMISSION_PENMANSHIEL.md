# Data admission record: Penmanshiel wind farm SCADA (Stage 5 second-site confirmation)

**Status:** ADMITTED_FOR_DEVELOPMENT (2018–2021) by the study author on 2026-11-17.
- **Validation year 2022:** admitted for a single pre-freeze check.
- **Test years 2023–2024: SEALED.** They are downloaded and MD5-verified, but must not be read or
  summarised until a Stage 5 protocol is frozen and committed. The only permitted exception is a
  timestamp/row-structure check that prints no values, if the loader fails, as in Kelmarsh D1.

No independent reviewer decision is claimed.

## 1. Source and rights

| Item | Value |
|---|---|
| Dataset | Penmanshiel wind farm data |
| Publisher / creators | Cubico Sustainable Investments Ltd; Zenodo creators Plumley, C.; Takeuchi, R. |
| Persistent identifier | DOI 10.5281/zenodo.16807304 (record published 2025-08-13) |
| Licence | **CC-BY-4.0** (Zenodo licence field `cc-by-4.0`) |
| Attribution | Cite the DOI and the creators in any publication |
| Site | Penmanshiel, UK; 14 × Senvion MM82 (28.7 MW; 2.05 MW each, the same rating as the Kelmarsh MM92s). There is no WT03 |
| Retrieved | 2026-11-17 via the Zenodo REST API |

## 2. Why these turbines and years (decided from file names and sizes only)

The record provides 2016–2022 for WT01–10 and WT11–15, but **2024 only for WT11–15**, and 2023 for
WT01–10 only in partial files (February, March, Q2, Q3–Q4). The study therefore uses the
**WT11–15 group**, which is complete for 2018–2024:

- **Control unit:** turbine WT11. Forecast inputs come from neighbours WT12–WT15 (4 neighbours;
  Kelmarsh had 5).
- **Development:** 2018–2021. **Validation:** 2022 (one check). **Sealed test:** 2023–2024.

The choices mirror Kelmarsh: one turbine, the same battery (2 MWh, ±1 MW) and the same ramp
reference (200 kW per 10 min). The Stage 4 design is transferred, not re-tuned.

## 3. Files (all MD5-verified against Zenodo; stored outside git at `C:/ResearchData/penmanshiel_zenodo_16807304/`)

| Role | File | MD5 (published) |
|---|---|---|
| metadata | Penmanshiel_WT_static.csv | c4cd4191234c1a67a391fe5d2978256b |
| development | Penmanshiel_SCADA_2018_WT11-15_3116.zip | 7c40dc00df6d6301427213e15170b927 |
| development | Penmanshiel_SCADA_2019_WT11-15_3117.zip | 92747a976716c5f35d9ee6462958fd7a |
| development | Penmanshiel_SCADA_2020_WT11-15_3118.zip | c73323f21451c08247dbdb5d1a1434a9 |
| development | Penmanshiel_SCADA_2021_WT11-15_4461.zip | f5804b90089ce4d50dc5117fda6f675c |
| validation | Penmanshiel_SCADA_2022_WT11-15_4463.zip | 5f4743133a9cf65ad33de139b43f96b4 |
| sealed_test | Penmanshiel_SCADA_2023_WT_11-15_5964.zip | 813ad4635cf50b9d96b253ee53175086 |
| sealed_test | Penmanshiel_SCADA_2024_WT_11-15_5966.zip | e0a700cad1d45f4130272feaef244b12 |

## 4. Prior exposure

The author has not used Penmanshiel data before. The dataset is public and widely used, so only
**author non-exposure** is claimed. The Kelmarsh results informed the design; that is the purpose
of a second-site confirmation and is stated in the protocol.
