# Wind Energy AI Optimisation: skill-aware battery control of wind-power ramps

**Raja Arqam Abdullah · MSc Artificial Intelligence · Teesside University**

A battery smooths short-term wind-power ramps using 10–60-minute forecasts with conformal
uncertainty, a scenario-based stochastic model predictive controller (MPC), and a causal
forecast-skill switch that keeps the battery idle, or scales its plan down, unless recent released
forecasts beat persistence. The repository also contains the WindGrid AI dashboard, which presents
the results.

## Status

Three pre-registered confirmatory studies. Each protocol was frozen (SHA-256 recorded in its runner)
before its test data was opened, and each test was run once from a clean checkout.

| Study | Design | Outcome |
|---|---|---|
| Simulation (Stage 3.3) | Held-out seeds; 18,900 episodes | 13/13 primary hypotheses supported |
| Real data, Kelmarsh (Stage 4) | SCADA, sealed 2023–2024; 2,048 paired episodes | 4/4 supported |
| Second site, Penmanshiel (Stage 5) | SCADA, sealed 2023–2024; 2,067 paired episodes; no re-tuning | 6/6 supported |

**Headlines.**
- Simulation: with skilful forecasts the controller removes 87–99% of ramp exceedance; without
  forecast skill the switch prevents harm of up to 38%.
- Real data: SCADA-only forecasts have little ramp skill (≈ 0.15 vs persistence), so reductions are
  small (−3.2% Kelmarsh, −3.3% to −3.7% Penmanshiel) but consistent, with no harm from weak forecasts.
  A perfect forecast would remove more than 99%: forecast quality is the bottleneck.
- The graded skill switch gives the binary switch's reduction with 47% less battery throughput.
  Adaptive MPC and a forecast-driven low-pass filter reduce exceedance more, but cost more battery
  per kW avoided.

## Documents

- **Manuscript draft:** [docs/MANUSCRIPT.md](docs/MANUSCRIPT.md)
- **How to run everything:** [docs/HOW_TO_RUN.md](docs/HOW_TO_RUN.md)
- **Results:** [simulation](docs/STAGE33_CONFIRMATORY_RESULTS.md) ·
  [Kelmarsh](docs/STAGE4_REAL_DATA_RESULTS.md) · [Penmanshiel](docs/STAGE5_SECOND_SITE_RESULTS.md)
- **Frozen protocols:** [simulation](docs/STAGE33_CONFIRMATORY_PROTOCOL.md) ·
  [Kelmarsh](docs/STAGE4_CONFIRMATORY_PROTOCOL.md) · [Penmanshiel](docs/STAGE5_CONFIRMATORY_PROTOCOL.md).
  Deviations are logged with each result set.
- **Development notes:** [Stage 3.3](docs/STAGE33_DEVELOPMENT_NOTES.md) ·
  [Stage 4](docs/STAGE4_DEVELOPMENT_NOTES.md) · [Stage 5](docs/STAGE5_DEVELOPMENT_NOTES.md)
- **Data admission:** [Kelmarsh](docs/DATA_ADMISSION_KELMARSH.md) · [Penmanshiel](docs/DATA_ADMISSION_PENMANSHIEL.md)

## Quick start (Windows)

Dashboard (open http://127.0.0.1:8501; the Real-Data Validation page shows both wind farms):

```powershell
.venv\Scripts\python.exe -m streamlit run app\dashboard.py --server.address 127.0.0.1 --server.port 8501
```

Tests:

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests
.venv\Scripts\python.exe -B -m unittest discover -s publication_v2/stage5/tests
```

The other stage suites (`publication_v2/stage31` … `stage4`) and the full run commands are listed in
[docs/HOW_TO_RUN.md](docs/HOW_TO_RUN.md).

## Repository map

| Path | Content |
|---|---|
| `publication_v2/stage2/` | Forecasting contract (14 causal features, six horizons) and conformal intervals |
| `publication_v2/stage31/`–`stage33/` | Battery MILP, synthetic wind, stochastic MPC, skill switch, simulation study |
| `publication_v2/stage4/` | Kelmarsh real-data pipeline, closed loop, analysis, frozen runner |
| `publication_v2/stage5/` | Graded switch, low-pass baseline, economics, site-generic loader, Penmanshiel runner |
| `app/` | WindGrid AI dashboard (Streamlit) |
| `src/windresearch/`, `scripts/`, `audits/` | Earlier retrospective XGBoost study and its audits (see below) |
| `docs/` | Manuscript, protocols, results, figures and records |

## Earlier work in this repository

The project began as a retrospective study with XGBoost forecasts and two-stage MPC on a Kaggle
SCADA dataset; its MPC controllers *worsened* aggregate ramp exceedance, a negative result that
motivated the later stages. That study, its audits and the first eight dashboard pages are preserved
unchanged. Their full descriptions are the two pre-merge READMEs:
[WindGrid dashboard phase](docs/legacy/README_windgrid_dashboard_phase.md) and
[research branch history](docs/legacy/README_research_branch.md).

## Data

- Kelmarsh wind farm data, Plumley & Takeuchi, Zenodo DOI 10.5281/zenodo.16807551 (CC-BY-4.0).
- Penmanshiel wind farm data, Zenodo DOI 10.5281/zenodo.16807304 (CC-BY-4.0).
- Raw data is not redistributed here; download and checksum instructions are in the data admission records.

## Status of the manuscript

Unpublished MSc working draft; no journal citation or DOI is assigned. `[CITE: …]` placeholders mark
references still to be added by the author.
