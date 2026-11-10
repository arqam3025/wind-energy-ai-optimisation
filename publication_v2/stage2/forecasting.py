"""Six direct-horizon forecasters with a common feature-only prediction API.

This numerical adapter is deliberately ignorant of outcome scoring.  Production
callers must first validate the training ledger and dataset provenance through
the Stage 2 data gate.  Unit tests use explicitly labelled synthetic fixtures;
this module never reads a historical model or dataset by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
from importlib import metadata as package_metadata
import json
from pathlib import Path
import re
import tempfile
from typing import Any

import numpy as np

from publication_v2.protocol import FEATURE_SUPPORT, HORIZONS

FEATURE_NAMES = tuple(FEATURE_SUPPORT)
TARGET_NAMES = tuple(f"target_h{h}_kw" for h in range(1, 7))
MODEL_NAMES = ("persistence", "xgboost", "lightgbm")
SCHEMA = "publication_v2.stage2.forecaster.v1"
DEFAULT_HYPERPARAMETERS = {
    "persistence": {},
    "xgboost": {"n_estimators": 100, "max_depth": 4, "learning_rate": 0.05,
                "subsample": 1.0, "colsample_bytree": 1.0, "reg_alpha": 0.0, "reg_lambda": 1.0},
    "lightgbm": {"n_estimators": 100, "max_depth": 4, "num_leaves": 15, "learning_rate": 0.05,
                 "subsample": 1.0, "subsample_freq": 0, "colsample_bytree": 1.0, "reg_alpha": 0.0, "reg_lambda": 1.0,
                 "min_child_samples": 20},
}
_ALLOWED_OVERRIDES = {
    "persistence": set(),
    "xgboost": set(DEFAULT_HYPERPARAMETERS["xgboost"]) | {"min_child_weight", "gamma"},
    "lightgbm": set(DEFAULT_HYPERPARAMETERS["lightgbm"]) | {"min_split_gain", "min_child_weight"},
}


class ForecastingError(ValueError):
    """An adapter request or model artifact violates its declared contract."""


class DependencyUnavailable(ForecastingError):
    """The requested optional CPU forecasting dependency is unavailable."""


def _dependency(name: str):
    try:
        return importlib.import_module(name)
    except (ImportError, OSError) as error:
        raise DependencyUnavailable(
            f"{name} is unavailable or cannot load its native library; install the declared Stage 2 dependency. "
            "No model comparison can silently omit this method."
        ) from error


def dependency_versions(name: str) -> dict[str, str]:
    names = ["numpy"] + (["scikit-learn", "scipy", name] if name != "persistence" else [])
    result = {}
    for package in names:
        try:
            result[package] = package_metadata.version(package)
        except package_metadata.PackageNotFoundError as error:
            raise DependencyUnavailable(f"Missing installed package metadata: {package}") from error
    return result


def _matrix(value: Any, *, targets: bool = False) -> np.ndarray:
    expected = TARGET_NAMES if targets else FEATURE_NAMES
    if hasattr(value, "columns") and tuple(value.columns) != expected:
        raise ForecastingError(f"Column order must be exactly {expected}")
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ForecastingError("A finite numeric matrix is required") from error
    if array.ndim != 2 or array.shape[0] == 0 or array.shape[1] != len(expected):
        raise ForecastingError(f"Expected a nonempty N x {len(expected)} {'target' if targets else 'feature'} matrix")
    if not np.isfinite(array).all():
        raise ForecastingError("Missing or non-finite matrix values are not imputed")
    if targets and (array < 0).any():
        raise ForecastingError("Physical generation targets must be nonnegative under an explicit upstream mapping")
    return np.array(array, dtype=np.float64, order="C", copy=True)


def matrix_sha256(value: Any, *, targets: bool = False) -> str:
    array = _matrix(value, targets=targets)
    shape = json.dumps(list(array.shape), separators=(",", ":")).encode("ascii")
    return hashlib.sha256(shape + b"\n" + array.astype("<f8", copy=False).tobytes(order="C")).hexdigest()


def _configuration(name: str, seed: int, overrides: dict[str, Any] | None) -> dict[str, Any]:
    if name not in MODEL_NAMES:
        raise ForecastingError(f"Unknown forecaster: {name!r}")
    if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
        raise ForecastingError("Seed must be an integer in [0, 2**31-1]")
    if overrides is not None and not isinstance(overrides, dict):
        raise ForecastingError("Hyperparameters must be an explicit dictionary")
    overrides = overrides or {}
    unknown = set(overrides) - _ALLOWED_OVERRIDES[name]
    if unknown:
        raise ForecastingError(f"Unsupported/unsafe overrides (seed, threads and objective are locked): {sorted(unknown)}")
    parameters = {**DEFAULT_HYPERPARAMETERS[name], **overrides}
    for key, value in parameters.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value):
            raise ForecastingError(f"Invalid numeric hyperparameter: {key}")
        if key in ("n_estimators", "max_depth", "num_leaves", "min_child_samples"):
            if type(value) is not int or value < 1:
                raise ForecastingError(f"{key} must be a positive integer")
        elif key == "subsample_freq":
            if type(value) is not int or not 0 <= value <= 2**31 - 1:
                raise ForecastingError("subsample_freq must be an integer in [0, 2**31-1]")
        elif key in ("learning_rate", "subsample", "colsample_bytree"):
            if not 0 < value <= 1:
                raise ForecastingError(f"{key} must lie in (0,1]")
        elif value < 0:
            raise ForecastingError(f"{key} must be nonnegative")
    if name == "xgboost":
        parameters.update(objective="reg:squarederror", tree_method="hist", n_jobs=1, random_state=seed)
    elif name == "lightgbm":
        # LightGBM ignores subsample < 1 unless bagging frequency is positive.
        # Resolve the implicit frequency explicitly, and refuse contradictory
        # requests rather than record an ineffective sampling experiment.
        if "subsample_freq" not in overrides:
            parameters["subsample_freq"] = 1 if parameters["subsample"] < 1 else 0
        if parameters["subsample"] < 1 and parameters["subsample_freq"] == 0:
            raise ForecastingError("LightGBM subsample < 1 requires subsample_freq > 0")
        if parameters["subsample"] == 1 and parameters["subsample_freq"] != 0:
            raise ForecastingError("LightGBM subsample_freq > 0 is ineffective when subsample = 1")
        parameters.update(objective="regression", n_jobs=1, random_state=seed, deterministic=True,
                          force_col_wise=True, verbosity=-1, data_random_seed=seed,
                          feature_fraction_seed=seed, bagging_seed=seed)
    return parameters


def _native_lightgbm_sampling(estimator: Any, parameters: dict[str, Any]) -> dict[str, Any]:
    """Verify the backend's canonical fields, rather than wrapper aliases alone.

    LightGBM's native text format rounds floating parameter display values.
    Preserve the exact requested/effective input separately from this explicitly
    labelled serialized view. An uninspectable or ineffective backend fails.
    """
    try:
        native = estimator.model_to_string()
        fractions = re.findall(r"^\[bagging_fraction: ([^\]]+)\]$", native, re.MULTILINE)
        frequencies = re.findall(r"^\[bagging_freq: ([^\]]+)\]$", native, re.MULTILINE)
        if len(fractions) != 1 or len(frequencies) != 1:
            raise ValueError("Missing/ambiguous native sampling parameters")
        fraction, frequency = float(fractions[0]), int(frequencies[0])
        requested_fraction = parameters["subsample"]
        if (not np.isfinite(fraction) or not 0 < fraction <= 1
                or not np.isclose(fraction, requested_fraction, rtol=5e-6, atol=0)
                or frequency != parameters["subsample_freq"]
                or ((fraction < 1 and frequency > 0) != (requested_fraction < 1))):
            raise ValueError("Native bagging differs from the declared effective sampling configuration")
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ForecastingError(f"Cannot verify effective LightGBM native sampling: {error}") from error
    return {"bagging_fraction": fraction, "bagging_freq": frequency,
            "row_bagging_active": fraction < 1 and frequency > 0,
            "inspection_source": "LightGBM native model text; floating display values may be rounded"}


@dataclass
class FittedForecaster:
    name: str
    seed: int
    hyperparameters: dict[str, Any]
    requested_hyperparameters: dict[str, Any]
    estimators: tuple[Any, ...]
    training_rows: int
    training_features_sha256: str
    training_targets_sha256: str
    versions: dict[str, str]
    fitted_at_utc: str

    def predict(self, features: Any) -> np.ndarray:
        """Consume feature values only; outcomes are never a prediction argument."""
        array = _matrix(features)
        if self.name == "persistence":
            prediction = np.repeat(array[:, :1], len(HORIZONS), axis=1)
        elif self.name == "lightgbm":
            prediction = np.column_stack([estimator.predict(array, num_threads=1) for estimator in self.estimators])
        else:
            prediction = np.column_stack([estimator.predict(array) for estimator in self.estimators])
        if prediction.shape != (len(array), len(HORIZONS)) or not np.isfinite(prediction).all():
            raise ForecastingError("Forecaster returned missing/non-finite or misaligned predictions")
        return np.maximum(0.0, prediction)


def fit_forecaster(name: str, features: Any, targets: Any, *, seed: int = 20261101,
                   hyperparameters: dict[str, Any] | None = None) -> FittedForecaster:
    """Fit a synthetic fixture or an already chronology/provenance-validated batch.

    The enclosing Stage 2 pipeline, rather than this numerical adapter, owns
    eligibility, timestamps and split validation. All methods receive identical
    matrix shapes and hashes; no evaluation set, callback or early stopping is
    accepted. No historical model artifact is read or written.
    """
    parameters = _configuration(name, seed, hyperparameters)
    x, y = _matrix(features), _matrix(targets, targets=True)
    if len(x) != len(y):
        raise ForecastingError("Features and six-horizon labels must share every training row")
    versions = dependency_versions(name)
    estimators = []
    if name != "persistence":
        library = _dependency(name)
        constructor = library.XGBRegressor if name == "xgboost" else library.LGBMRegressor
        for horizon_index in range(len(HORIZONS)):
            estimator = constructor(**parameters)
            estimator.fit(x, y[:, horizon_index])
            if name == "lightgbm":
                _native_lightgbm_sampling(estimator.booster_, parameters)
            estimators.append(estimator if name == "xgboost" else estimator.booster_)
    return FittedForecaster(name=name, seed=seed, hyperparameters=parameters,
        requested_hyperparameters=dict(hyperparameters or {}),
        estimators=tuple(estimators), training_rows=len(x), training_features_sha256=matrix_sha256(x),
        training_targets_sha256=matrix_sha256(y, targets=True), versions=versions,
        fitted_at_utc=datetime.now(timezone.utc).isoformat())


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _reject_link(path: Path) -> None:
    current = path.absolute()
    while current != current.parent:
        if current.is_symlink() or getattr(current, "is_junction", lambda: False)():
            raise ForecastingError(f"Symlink/junction model artifact is not accepted: {path}")
        current = current.parent


def save_forecaster(model: FittedForecaster, directory: Path, *, training_provenance: dict) -> dict:
    """Save exclusive new native models; caller owns versioned output isolation."""
    if not isinstance(training_provenance, dict) or not training_provenance:
        raise ForecastingError("Explicit training provenance is required; unknown data clocks must not be invented")
    # Validate serializability before creating output; allow_nan=False refuses fabricated NaN metadata.
    json.dumps(training_provenance, allow_nan=False)
    directory = Path(directory)
    _reject_link(directory)
    directory.mkdir(parents=True, exist_ok=False)
    files, native_configs, native_sampling = {}, [], []
    expected_models = 0 if model.name == "persistence" else len(HORIZONS)
    if model.name not in MODEL_NAMES or len(model.estimators) != expected_models:
        raise ForecastingError("Model/horizon set is incomplete; partial artifact remains uncompleted")
    for index, estimator in enumerate(model.estimators, start=1):
        extension = "json" if model.name == "xgboost" else "txt"
        filename = f"h{index}.{extension}"
        with tempfile.TemporaryDirectory(dir=directory, prefix=".native_") as temporary:
            candidate = Path(temporary) / filename
            estimator.save_model(str(candidate))
            with (directory / filename).open("xb") as stream:
                stream.write(candidate.read_bytes())
        files[filename] = file_sha256(directory / filename)
        native_configs.append(json.loads(estimator.get_booster().save_config()) if model.name == "xgboost" else dict(estimator.params))
        if model.name == "lightgbm":
            native_sampling.append(_native_lightgbm_sampling(estimator, model.hyperparameters))
    manifest = {"schema_version": SCHEMA, "name": model.name, "seed": model.seed,
        "features": list(FEATURE_NAMES), "horizons_minutes": list(HORIZONS),
        "hyperparameters": model.hyperparameters, "requested_hyperparameters": model.requested_hyperparameters,
        "dependency_versions": model.versions, "native_row_sampling": native_sampling,
        "training_rows": model.training_rows, "training_features_sha256": model.training_features_sha256,
        "training_targets_sha256": model.training_targets_sha256,
        "fitted_at_utc": model.fitted_at_utc, "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "timestamp_interpretation": "Wall-clock execution metadata; not evidence of historical model/data availability",
        "training_provenance": training_provenance, "native_training_configs": native_configs,
        "prediction_postprocessing": "Nonnegative generation: max(0,prediction); no unverified rated-power cap",
        "model_files_sha256": files, "evaluation_used_for_fitting": False}
    with (directory / "manifest.json").open("x", encoding="utf-8", newline="") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return manifest


def load_forecaster(directory: Path, *, expected_manifest_sha256: str | None = None) -> FittedForecaster:
    directory = Path(directory)
    _reject_link(directory)
    manifest_path = directory / "manifest.json"
    _reject_link(manifest_path)
    if not manifest_path.is_file():
        raise ForecastingError("A completed forecast manifest is required")
    if expected_manifest_sha256 is not None and file_sha256(manifest_path) != expected_manifest_sha256:
        raise ForecastingError("Forecast manifest hash differs from the expected identity")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        name = manifest["name"]
        files = manifest["model_files_sha256"]
        if (manifest["schema_version"] != SCHEMA or name not in MODEL_NAMES
                or tuple(manifest["features"]) != FEATURE_NAMES or tuple(manifest["horizons_minutes"]) != HORIZONS):
            raise ValueError("Wrong model/schema/feature/horizon identity")
        if type(manifest["seed"]) is not int or not 0 <= manifest["seed"] <= 2**31 - 1:
            raise ValueError("Invalid saved random seed")
        if not isinstance(manifest["requested_hyperparameters"], dict):
            raise ValueError("Explicit requested hyperparameter metadata must be a dictionary")
        effective = _configuration(name, manifest["seed"], manifest["requested_hyperparameters"])
        if effective != manifest["hyperparameters"]:
            raise ValueError("Requested and effective hyperparameters are inconsistent")
        expected = set() if name == "persistence" else {f"h{i}.{'json' if name == 'xgboost' else 'txt'}" for i in range(1,7)}
        if set(files) != expected:
            raise ValueError("Missing or unexpected horizon model")
        for filename, expected_hash in files.items():
            path = directory / filename
            _reject_link(path)
            if not re.fullmatch('[0-9a-f]{64}', expected_hash) or file_sha256(path) != expected_hash:
                raise ValueError(f"Model hash mismatch: {filename}")
        if dependency_versions(name) != manifest["dependency_versions"]:
            raise ValueError("Model dependency environment differs from the saved versions")
        estimators = []
        if name != "persistence":
            library = _dependency(name)
            for filename in sorted(files):
                if name == "xgboost":
                    estimator = library.XGBRegressor(n_jobs=1)
                    estimator.load_model(str(directory / filename))
                    # Native model files preserve trees, not every generic runtime
                    # parameter. Restore the declared CPU/thread/seed profile after
                    # loading; this does not modify any serialized model bytes.
                    estimator.set_params(n_jobs=1, random_state=manifest["seed"])
                else:
                    estimator = library.Booster(model_file=str(directory / filename))
                    native_sampling = _native_lightgbm_sampling(estimator, effective)
                    if native_sampling != manifest["native_row_sampling"][len(estimators)]:
                        raise ValueError("Saved native row-sampling metadata differs from the model")
                estimators.append(estimator)
        if len(manifest["native_row_sampling"]) != (len(HORIZONS) if name == "lightgbm" else 0):
            raise ValueError("Incomplete or unexpected native row-sampling metadata")
        return FittedForecaster(name=name, seed=manifest["seed"], hyperparameters=manifest["hyperparameters"],
            requested_hyperparameters=manifest["requested_hyperparameters"],
            estimators=tuple(estimators), training_rows=manifest["training_rows"],
            training_features_sha256=manifest["training_features_sha256"],
            training_targets_sha256=manifest["training_targets_sha256"], versions=manifest["dependency_versions"],
            fitted_at_utc=manifest["fitted_at_utc"])
    except (OSError, KeyError, IndexError, TypeError, ValueError) as error:
        raise ForecastingError(f"Invalid/corrupt forecast artifact: {error}") from error
