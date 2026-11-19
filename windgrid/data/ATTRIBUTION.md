# Demo sample attribution

`penmanshiel_2022_sample.npz` holds 14 days (February 2022) of 10-minute interval-mean power for
Penmanshiel turbine WT11, plus two forecasts computed by this project (persistence and a
neighbour-turbine LightGBM model fitted on 2018–2021).

- **Source data:** Penmanshiel wind farm SCADA data, Zenodo, DOI
  [10.5281/zenodo.16807304](https://doi.org/10.5281/zenodo.16807304).
- **Licence of the source data:** Creative Commons Attribution 4.0 International (CC-BY-4.0).
- **Changes:** one turbine's active power, resampled to the project's interval-end grid
  (label + 10 min), cut to a two-week window; forecasts added. Provenance and checksums are in
  `sample_provenance.json`, and `make_sample.py` regenerates the file.

2022 was the Stage 5 pre-freeze validation year. It is not part of the sealed 2023–2024 test.
The project's code licence (MIT) does not apply to this data; the CC-BY-4.0 terms do.
