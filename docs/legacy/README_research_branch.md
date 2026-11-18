> README of branch research/stage5-improvements before the merge on 2026-11-18 (Stage 3.1 to Stage 5 research). Preserved unchanged except that relative links now point from this folder.

# Wind Energy AI Optimisation: skill-gated stochastic MPC for wind–battery ramp control

MSc research project. A battery smooths short-term wind-power ramps using 10–60-minute forecasts
with conformal uncertainty, a scenario-based stochastic MPC, and a forecast-skill safety switch
that keeps the battery idle unless recent released forecasts beat persistence.

**Current status (branch `research/stage4-real-data`).**

| Study | Design | Outcome |
|---|---|---|
| Simulation (Stage 3.3) | Pre-registered; held-out seeds; 18,900 episodes | 13/13 primary hypotheses supported |
| Real data (Stage 4) | Pre-registered; Kelmarsh SCADA, sealed 2023–2024; 2,048 paired episodes | 4/4 primary hypotheses supported |

Real-data headline: −3.2% ramp exceedance with 73% less battery throughput than adaptive MPC, and
no harm with weak forecasts. A perfect forecast would give −99.8%, so forecast quality is the
bottleneck.

- **Run it:** [docs/HOW_TO_RUN.md](../../docs/HOW_TO_RUN.md). 320 automated tests.
- **Paper draft:** [docs/MANUSCRIPT.md](../../docs/MANUSCRIPT.md).
- **Results:** [simulation](../../docs/STAGE33_CONFIRMATORY_RESULTS.md) · [real data](../../docs/STAGE4_REAL_DATA_RESULTS.md).
- **Protocols:** [simulation](../../docs/STAGE33_CONFIRMATORY_PROTOCOL.md) · [real data](../../docs/STAGE4_CONFIRMATORY_PROTOCOL.md).
  Deviations are logged with each result set.
- **Data:** Kelmarsh wind farm data, Plumley & Takeuchi, Zenodo DOI 10.5281/zenodo.16807551
  (CC-BY-4.0). It is not redistributed here.

The sections below are the earlier README, kept unchanged as a historical record.

---

## Earlier README: Stage 3.1 local synthetic MPC development

This research source adds a six-step battery MILP and five
synthetic controller comparators. See [the Stage 3.1 design, results and test report](../../docs/PUBLICATION_V2_STAGE31_MPC_DESIGN.md).
The inherited published code is the base at `968773d8`; its release manifest
continues to authenticate that historical parent, not this expanded Stage 3.1/3.1.1 source version.

**Synthetic data only. PENDING_REVIEW. BLOCKED_CONFIRMATORY_TEST.**
Local source history and remote publication are separate approval steps. Run the synthetic tests with
`python -B -m unittest discover -s publication_v2/stage31/tests -v` after selecting
an environment with `publication_v2/stage31/requirements.txt` installed.

## Scientific audit and local freeze

The [Stage 3.1.1 scientific audit](../../docs/PUBLICATION_V2_STAGE311_MPC_SCIENTIFIC_AUDIT.md)
records certificate and run-verifier corrections, negative baseline findings and
the 242-case synthetic suite (241 passed, one Windows privilege skip). Versioned
reports retain their status at preparation, including preapproval no-commit
wording; they are preserved research records. Generated runs and private source
snapshots are excluded from source commits. New manifests record the synthetic
development stage without making a hardcoded Git dirty/clean claim.

## Archived description of the published Stage 2.9 parent

The following text describes that parent release, including its narrower scope;
it is retained for context rather than asserted as a current Stage 3.1 inventory.

### Published Publication V2 baseline

Development-only forecasting and uncertainty software for research on 10–60-minute
wind-generation forecasts and later wind–battery ramp-mitigation MPC integration.
This curated branch is a new root snapshot. It contains no original research
data, saved models, experimental result tables, frozen manifests or private audits.

**Data admission: PENDING_REVIEW. Confirmatory status: BLOCKED_CONFIRMATORY_TEST.**
No new forecast accuracy, coverage improvement, controller efficacy or independent
validation is claimed. This is not a complete reproduction of historical experiments.

## Implemented code

- Persistence, XGBoost and LightGBM interfaces sharing fourteen causal features,
  six horizons (10, 20, 30, 40, 50, 60 minutes), cohort rules and scoring contracts.
- Static, rolling and recency-weighted horizon-specific conformal intervals.
- Strict chronology, feature/target availability, lineage, exclusion, retrospective
  study-role and fail-closed admission validators.
- MAE, RMSE, bias, rapid-event errors, empirical coverage, width, drift and
  floor-binding accounting. Metrics are implemented; real-data results are absent.

The measured-generation target is `max(0, raw_power_kw)`. It is not a measurement
of unconstrained theoretically available wind power. No new MPC algorithm or
historical controller implementation is included in this code-only snapshot.

## Synthetic validation — no dataset or model fitting

Use Python **3.12**; validation was executed with Python 3.12.5. From the repository
root, these standard-library-only commands work on Windows and POSIX systems:

```text
python -S -B -m unittest discover -s publication_v2/tests -v
python -S -B -m unittest discover -s publication_v2/stage2/tests -v
```

Only the three self-contained Stage 2 test modules are shipped. The tests use
invented fixtures and mocks, do not train forecasting models, and do not need
SCADA observations. A Windows account without symlink privileges skips one
fixture. Private-artifact integration and model-fitting suites are not represented
as passed by these commands. See [reproducibility](../../docs/REPRODUCIBILITY_STAGE29_RELEASE.md).

The separate native forecasting dependency declaration is
`publication_v2/stage2/requirements.txt`. An optional isolated installation is:

```text
python -m venv .venv
```

Then select the environment explicitly. On Windows:

```text
.venv/Scripts/python.exe -m pip install -r publication_v2/stage2/requirements.txt
```

On POSIX systems:

```text
.venv/bin/python -m pip install -r publication_v2/stage2/requirements.txt
```

The dependency installation is not needed for the
`-S` synthetic tests. A fresh native installation was not validated here.
Do not invoke research training merely because dependencies install successfully.

## Data source and rights

Historical attribution is Berker Isen's
[Wind Turbine SCADA Dataset](https://www.kaggle.com/datasets/berkerisen/wind-turbine-scada-dataset).
The source URL is attribution, not evidence of an authenticated release, approved
usage or redistribution permission. Release identity, rights, timezone, interval
semantics, operational availability and transformation evidence need independent
review. No dataset is supplied or approved. See [data governance](../../docs/DATA_GOVERNANCE.md).

## Reproduction limits

The previous 281-file review export lacked 1,937 of 2,170 protected paths.
This smaller curated release has 2,155 protected pathnames absent. Twelve
software/configuration/test paths match their original protected bytes; three
existing pathnames (README and the two Git policies) contain newly derived public
versions. Thus 2,158 original protected versions are not distributed. No frozen reference or data/model/result payload is
included. Original preservation manifests remain private and are also absent.
Missing artifact inventory, rights review and an independently exercised environment
are required before full execution. Production gates deliberately fail closed.

The original 49 inspected evaluation blocks are retrospective, not untouched
confirmation. The archived negative finding that uncontrolled wind had fewer
aggregate ramp violations than the archived MPC controllers remains unchanged
in private evidence. No historical measurements or results were recalculated.

See [methods](../../docs/METHODS.md), [release audit](../../docs/RELEASE_AUDIT_SUMMARY.md) and
the machine-readable release manifest under `publication_v2/publication/`.
Public synthetic tests do not establish operational deployability, grid compliance,
battery lifetime improvement or journal readiness. No new data licence is assigned.
