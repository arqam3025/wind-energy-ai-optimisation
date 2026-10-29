"""Explicit chronology guards for new studies; never rewrite historical artifacts."""
from collections.abc import Mapping
from pathlib import Path
import pandas as pd


class ProtocolError(ValueError):
    """An experiment violates its declared information or output boundary."""


def require_static_calibration_available(
    calibration: pd.DataFrame, decision_time: pd.Timestamp, horizon_steps: int = 6
) -> None:
    """All residual targets, including the last, must precede a scored decision."""
    if 'timestamp' not in calibration or calibration.empty:
        raise ProtocolError('A nonempty timestamped calibration table is required.')
    if not 1 <= horizon_steps <= 6:
        raise ProtocolError('Only the existing one-to-six forecast steps are available.')
    origins = pd.to_datetime(calibration.timestamp, errors='raise')
    decision = pd.Timestamp(decision_time)
    if origins.isna().any():
        raise ProtocolError('Missing calibration origin timestamp.')
    for horizon in range(1, horizon_steps + 1):
        targets = origins + pd.Timedelta(minutes=10 * horizon)
        unavailable = targets >= decision
        if unavailable.any():
            raise ProtocolError(
                f'Fixed calibration is not observable at {decision}: horizon '
                f'{10*horizon} min has {int(unavailable.sum())} target(s) at or after '
                f'the decision; latest target {targets.max()}. Use a declared later '
                'episode or a separately versioned target-purged calibration. '
                'The original calibration is not modified.'
            )


def target_purged_calibration(
    calibration: pd.DataFrame, first_decision: pd.Timestamp, horizon_steps: int = 6
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return new target-safe rows plus rejected rows; never mutate the input.

    A shared six-model calibration origin is retained only if every horizon
    target is already observable. Recalibrating on this projection is a new
    study, not an in-place correction of the original frozen quantiles.
    """
    if 'timestamp' not in calibration or calibration.empty or not 1<=horizon_steps<=6:
        raise ProtocolError('Need nonempty calibration timestamps and one-to-six horizons.')
    origins=pd.to_datetime(calibration.timestamp,errors='raise')
    if origins.isna().any() or origins.duplicated().any():
        raise ProtocolError('Calibration origins must be present and unique.')
    keep=origins+pd.Timedelta(minutes=10*horizon_steps)<pd.Timestamp(first_decision)
    retained=calibration.loc[keep].copy()
    excluded=calibration.loc[~keep].copy()
    if retained.empty:raise ProtocolError('Target purge leaves no calibration observations.')
    require_static_calibration_available(retained,first_decision,horizon_steps)
    return retained,excluded


def role_target_overlap(
    schedule: pd.DataFrame, blocks: Mapping[int, pd.DataFrame], horizon_steps: int = 6
) -> pd.DataFrame:
    """Audit every development role, including block 6, by target rather than origin."""
    required = {'block_id', 'evaluation_role'}
    if not required.issubset(schedule.columns):
        raise ProtocolError('Schedule requires block_id and evaluation_role.')
    if schedule.block_id.duplicated().any():
        raise ProtocolError('Duplicate schedule block ID.')
    development_targets: set[pd.Timestamp] = set()
    for row in schedule.itertuples():
        if row.evaluation_role == 'development':
            origins = pd.to_datetime(blocks[int(row.block_id)].timestamp, errors='raise')
            for horizon in range(1, horizon_steps + 1):
                development_targets.update(origins + pd.Timedelta(minutes=10*horizon))
    records = []
    for row in schedule.itertuples():
        if row.evaluation_role != 'evaluation':
            continue
        origins = pd.to_datetime(blocks[int(row.block_id)].timestamp, errors='raise')
        for horizon in range(1, horizon_steps + 1):
            for origin in origins:
                target = origin + pd.Timedelta(minutes=10*horizon)
                if target in development_targets:
                    records.append({'block_id': int(row.block_id), 'origin': origin,
                                    'horizon_minutes': 10*horizon, 'target': target})
    return pd.DataFrame(records, columns=['block_id','origin','horizon_minutes','target'])


def require_cohort_interpretation(overlap: pd.DataFrame, *, retrospective: bool) -> None:
    """An overlapping legacy cohort cannot silently become a new clean holdout."""
    if not retrospective and not overlap.empty:
        raise ProtocolError(
            f'{len(overlap)} evaluation horizon-target pairs overlap declared development. '
            'Do not claim a clean holdout or silently drop observations. '
            'Use a newly approved independent protocol, or explicitly label this '
            'unchanged historical cohort retrospective.'
        )


def require_new_output_directory(path: Path) -> Path:
    """Never skip or trust a pre-existing partial result by existence alone."""
    try:
        path.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise ProtocolError(f'Refusing existing experiment output directory: {path}') from error
    return path
