# Publication readiness

**The project is not ready for an unqualified confirmatory or deployment-efficacy paper.** It supports a transparent retrospective engineering study, including negative results, once manuscript and release checks below are completed. This assessment is a technical review in the existing workspace, not external peer review. The authoritative evidence is [RESEARCH_AUDIT.md](RESEARCH_AUDIT.md), [EXPERIMENTAL_RESULTS.md](EXPERIMENTAL_RESULTS.md) and [RESEARCH_LIMITATIONS.md](RESEARCH_LIMITATIONS.md).

## Defensible contribution and title

Suggested title: **“A Retrospective Audit of Forecast Uncertainty and Wind–Battery Model Predictive Control.”**

The defensible contribution is an executable empirical integration with strict residual-target eligibility, shared first-command battery physics, preserved controller provenance and trace-level accounting of ramp/energy trade-offs. Its value includes discovering chronology defects and reporting deterioration against uncontrolled wind. XGBoost, conformal calibration, wind–battery MPC and lexicographic optimisation are established ingredients; the [bounded literature review](literature_review.md) does not establish algorithmic priority. Claim neither a first-ever combination nor a new uncertainty theorem. Further closest-method review is needed to assess originality at publication standard.

## Seven-section paper outline

1. **Introduction and related work:** precise engineering question, established methods and scoped empirical contribution.
2. **Data and chronology:** source/version/rights, clock conventions, six target horizons, training/calibration/development boundaries, prior inspection and excluded block 6.
3. **Forecasting and uncertainty:** frozen inference, persistence/local-trend baselines, signed scores, strict eligibility, order statistic, floors/fallback, lower sets versus two-sided intervals.
4. **Battery control and execution:** source-matched equations, six-step scenarios, nonanticipative first requests, binary constraints, two solves with primary allowance, execution caps and accounting units.
5. **Experimental protocol and reproducibility:** retrospective 49-episode cohort, common baselines, cold resets, prespecified development studies, versioned hashes, solver settings and statistical assumptions.
6. **Results and diagnostic analysis:** all three original cases, paired totals/intervals, forecast trade-offs, event coverage, energy/inventory separation and only completed supplementary experiments.
7. **Discussion, limitations and conclusion:** negative uncontrolled comparison, uncertain ramp benefit, limited component attribution, realistic deployment gaps and genuinely fresh validation.

## Requirements before submission

- **Correct the scientific framing.** Keep retrospective status and both chronology defects prominent. Retain the original 49-block totals without presenting prior inspection as blinding. Report 27.86% throughput reduction, 0.77% exceedance reduction and sixteen fewer violations relative to fixed margins alongside adaptive's 21 additional violations relative to uncontrolled wind. Describe development's eleven additional adaptive violations as a separate development finding.
- **Complete manuscript reconciliation.** Check every displayed equation against implemented charge/discharge, scenario minima, SOC, soft reserve, primary allowance and execution rules. Use kW for summed ramp exceedance and kWh for energy. Separate actual export from hypothetical terminal-adjusted export; preserve error-metric and rapid-event-coverage trade-offs. Check rendered mathematical notation, reference metadata and figure/table links rather than relying on source Markdown alone.
- **Bound inference and originality.** Include all declared dependent-resampling lengths and small-segment warnings. Neither interval exclusion for throughput nor inclusion for ramps establishes general superiority, equivalence, guaranteed coverage or causation by rolling adaptation. Present new sensitivity/ablation experiments as separately versioned development evidence, with actual completion scope and solver failures. Pending computations supply no results.
- **Clear acquisition and release rights.** Establish dataset provenance/version and redistribution permission; select an appropriate source-code licence and verify model/output distribution rights. Preserve source attribution. Git publication requires a curated staged diff, secret/history and large-file review, access instructions for ignored artifacts, and an independently reproducible clean environment. Local files and untracked documents are not automatically part of a public release. No GitHub push is authorised by this document.

## Evidence needed for stronger claims

A confirmatory performance claim requires genuinely untouched data collected or reserved without research-team outcome inspection. Before access, freeze the controller/model identities, hypotheses, metrics, exposure, exclusions, dependency-aware analysis and every development/calibration target boundary. Preserve a full-horizon embargo so **all** calibration labels precede every scored decision, and include every development-designated source in overlap guards. New model fitting or controller selection, if desired, belongs to an explicitly separate development stage followed by fresh confirmation.

A deployment claim additionally requires realistic battery/network limits, measurement/forecast latency, solver-time feasibility, controller-failure behaviour and continuous-operation validation. Lifetime claims require a validated degradation model or measured aging outcomes. Until then, release the work as an auditable retrospective research artifact with candid limitations, without converting reproducible arithmetic into unsupported efficacy claims.
