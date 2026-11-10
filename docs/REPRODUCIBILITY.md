# Reproducibility boundaries and synthetic test matrix

Use Python 3.12. The portable commands in the README deliberately use `-S -B`:
the selected suites need only the standard library and avoid bytecode output.

| Suite | Cases | Inputs / interpretation |
| --- | ---: | --- |
| Stage 1 integrity, inventory, protocol, runner, temporal audit | 59 | Invented temporary files and timestamp fixtures; one Windows symlink test may skip |
| Stage 2 conformal | 17 | Invented residual ledgers; no model fitting |
| Stage 2 metrics | 16 | Invented predictions/outcomes; software scoring only |
| Stage 2 environment | 15 | Mocked distribution/native-probe metadata; no native training |

The original data, lineage, retrospective/workflow integration and forecasting-fit
suites are excluded from default public discovery because they require private
artifacts or fit models. Their original versions remain privately preserved.
Do not interpret 107 shipped tests as coverage of those excluded workflows.

Stage 2 native dependencies have six exact direct pins. The original machine
inventory and its paths remain private. A clean dependency installation, portable
wheel/container hash lock and cross-OS numerical reproduction are unverified.

The earlier review export omitted 1,937 protected paths. This curated release
omits 2,155 of the 2,170 protected pathnames, plus the original preservation
manifest payloads required by production runners. Twelve already tracked
software/configuration/test files match their original protected bytes. Three
other pathnames (README and the two Git policies) contain newly derived public
versions, so 2,158 original protected versions are not distributed. No included
path overlaps the 59 frozen references. Protection continues
to apply to the untouched originals; no private research payload is published.

Stage 1 and Stage 2 production runners require those missing manifests and
authorized artifacts. Historical exposure checks also require the original raw
source and evaluation schedule. They remain fail-closed. A missing-file failure
is an input blocker, not permission to disable a guard or fabricate an input.

Current `verify_run` authenticates source and environment exactly, including
machine fingerprints; it is not a cross-machine artifact-only verifier. Such a
verifier would need separate reviewed implementation and narrower claims.

The public validation summary contains only executed software-test counts and
scope. Original raw test transcripts, environment paths and research evidence
remain private. No synthetic metrics are presented as research findings.
