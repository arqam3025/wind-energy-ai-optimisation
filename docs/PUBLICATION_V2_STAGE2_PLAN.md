# Publication v2: gated Stage 2 implementation plan

Prepared 1 November 2026. Stage 2 is planned, not implemented or executed by Stage 1. The [Stage 1 protocol](PUBLICATION_V2_PROTOCOL.md) and [actual Stage 1 report](PUBLICATION_V2_STAGE1_REPORT.md) govern readiness. The [earlier audit](RESEARCH_AUDIT.md), [retrospective results](EXPERIMENTAL_RESULTS.md) and [publication assessment](PUBLICATION_READINESS.md) remain required context.

## Gate A: establish a defensible data and access record

Obtain an authenticated source release or new acquisition with documented units, timezone/DST/interval meaning, missing-data policy, observation/feature delivery latency, processing lineage and license. Preserve exact input checksums and legal retrieval instructions. Establish the saved-model/fitted-preprocessor identities and attested fitting/access cutoffs before deciding whether the frozen predictors are eligible for the proposed new cohort. A structurally reconstructable historical split is not a substitute for historical access evidence.

For confirmatory evaluation, obtain genuinely uninspected data and a custody/reservation record. Suitable candidates could be a newly acquired chronological period or a separately reserved turbine/site, but neither qualifies by name alone. Evidence must show no outcome access or influence on model, uncertainty or controller choices, compatibility with feature and target requirements, and a freeze before authorized access. Include at least 60 minutes of complete causal feature lookback before the first scored origin and 60 minutes of target support after the last scored origin, with every required timestamp join available. Required duration and event counts must be justified by a prespecified power/precision or exposure plan, not chosen after examining favourable outcomes or simply reusing the historical 49-block count.

If that evidence is unavailable, keep `BLOCKED_CONFIRMATORY_TEST`. Historical data may support explicitly retrospective software reproduction or exploratory development; it must not become an independent test through a new folder, renamed split or additional embargo.

## Gate B: lock the experimental question before outcome access

Specify the primary question, comparison, metrics, exposure duration, exclusions, numerical tolerances and dependence-aware analysis. Freeze all dataset/model/controller/configuration identities and chronology rules. Keep development and confirmation roles distinct, with horizon-specific label purging, verified availability and all-horizon target-disjointness checks. Separate the operational information stream from outcome scoring with access controls where practical.

Retain three essential comparison cases under common periods, initial/terminal conventions, physical parameters, observation/decision latency, boundaries and metrics: uncontrolled wind, frozen fixed-margin MPC and frozen adaptive one-sided MPC. The historical selection of adaptive on development data remains a historical fact, not a new choice inferred from test outcomes. Additional persistence/nominal/oracle cases, if included, require a prespecified purpose and identical physical/scoring conventions. Any perfect-forecast oracle is explicitly nondeployable and is not an unconditional upper bound on every metric under mixed objectives and finite horizons.

Do not quietly redesign the controller after examining confirmation outcomes. New forecasting or MPC methods belong to an explicitly authorized development stage with separately reserved confirmation data; they are outside current Stage 1 scope.

## Gate C: implement source-matched adapters and guarded execution

After the data and experiment gates pass, implement new adapters under versioned paths, retaining frozen algorithms, models and parameters. Build a decision-input boundary that admits only validated features, observed state, forecasts and strictly eligible residuals. Keep future actuals available to the scorer only after first-action commitment. Persist event and availability times, model/feature/residual identities, committed commands and execution outcomes.

Require regression tests against the frozen objective and physical fallback, future-outcome intervention tests, charge/discharge and SOC/power/energy checks, solver-failure handling, and recorded numerical acceptance thresholds. Log actual solver status, stage objectives and available diagnostics without inventing unavailable values. Add atomic checkpoints and fail-closed completion verification before running the locked experiment. Compare committed-source byte identities on the supported platforms and test a clean environment using only documented accessible inputs.

## Gate D: execute once, retain failures and analyse as declared

Run the frozen registered comparison on the authorized untouched cohort. Preserve solver failures, missing observations, exclusions and interrupted runs; do not silently drop difficult intervals or recycle partially written outputs. Stop and document any violated chronology/provenance assumption. A later correction requires a new version and a disclosed impact assessment, not replacement of an inconvenient result.

Use paired comparisons at the predeclared chronological unit, with dependence handling justified for the new period and explicit limitations if few independent weather segments exist. Do not treat overlapping horizons as IID observations or choose resampling length by significance. Report all prespecified outcomes and cases where control worsens grid behaviour. Keep actual export, conversion loss, terminal stored energy and hypothetical terminal-adjusted export distinct. Throughput and equivalent-full-cycle proxies do not establish battery lifetime.

The negative historical uncontrolled-wind comparison remains in context regardless of the new outcomes. Replication, a negative result or an inconclusive interval is scientifically acceptable. No controller is selected on the confirmation set.

## Gate E: reconcile the paper and curate a reproducible release

Reconcile every equation, figure, table, reference and scientific claim with the locked implementation and actual completion record. Clearly separate historical retrospective results from any new independent experiment and disclose remaining access/dependence/measurement limits. Do not claim a new coverage theorem, algorithmic priority, universal grid compliance or journal readiness without the additional evidence those claims need.

Curate code, exact environment records, manifests, accessible artifacts, aggregate tables and rights-cleared figures. Validate an external clean-clone reproduction and review the staged diff, secrets, large files, licenses and data access instructions. Obtain author/supervisor approval for submission or publication. Stage 1 commits remain on `research/publication-v2`; merging or publishing is a separate explicitly authorized action.
