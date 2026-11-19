"""WindGrid dispatch API (FastAPI).

Endpoints
- ``GET  /health``           liveness and version
- ``GET  /v1/controllers``   available controllers and battery configuration
- ``POST /v1/dispatch``      one battery decision from a window of released history
- ``GET  /v1/sample``        a ready-made request built from the bundled Penmanshiel sample
- ``POST /v1/simulate``      closed-loop replay of one sample episode for a controller

Interactive documentation is served at ``/docs`` (OpenAPI). Every response carries an
``X-Request-ID`` and an ``X-Process-Time-ms`` header; each request is logged as one JSON line.
Run with ``windgrid serve`` or ``uvicorn windgrid.api:app``.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from publication_v2.stage31.battery import BatteryConfig

from . import __version__, service, simulate

log = logging.getLogger('windgrid.api')
ControllerName = Literal[tuple(service.CONTROLLERS)]  # type: ignore[valid-type]


class Interval(BaseModel):
    model_config = ConfigDict(extra='forbid')
    interval_end: datetime = Field(description='End of the 10-minute interval, timezone-aware (UTC recommended)')
    realised_kw: float | None = Field(description='Released interval-mean power (kW); null if missing')
    forecast_kw: list[float | None] | None = Field(
        default=None,
        min_length=6,
        max_length=6,
        description='Forecast issued at interval_end for the next six intervals (10..60 min); null if missing',
    )


class DispatchRequest(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={
            'description': (
                'The newest interval is the decision time. Provide at least 40 contiguous intervals; about 200 '
                'give full conformal calibration. Missing inputs make the controller fail closed (battery idle).'
            )
        },
    )
    controller: ControllerName = service.DEFAULT_CONTROLLER
    battery_energy_kwh: float = Field(description='Stored energy now (kWh); default battery 2,000 kWh, SOC 40–90%')
    previous_grid_kw: float = Field(description='Grid export in the interval that just ended (kW)')
    history: list[Interval] = Field(min_length=service.MIN_HISTORY, max_length=service.MAX_HISTORY)


class Plan(BaseModel):
    charge_kw: list[float] = []
    discharge_kw: list[float] = []
    energy_kwh: list[float] = []


class DispatchResponse(BaseModel):
    decision_time: str
    controller: str
    charge_kw: float
    discharge_kw: float
    net_battery_kw: float = Field(description='Discharge minus charge (kW); positive adds to grid export')
    energy_after_kwh: float
    forecast_available: bool
    skill_score: float | None = Field(description='Released skill vs persistence (1 = perfect, 0 = no better)')
    skill_weight: float | None = Field(description='Graded-switch weight in [0, 1] (graded controllers only)')
    forecast_kw: list[float] | None
    interval_lower_kw: list[float] | None
    interval_upper_kw: list[float] | None
    status: str
    solver_status: int | None
    fallback: bool
    optimization_failed: bool
    reason: str | None
    computation_ms: float
    plan: Plan


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    controller: ControllerName = service.DEFAULT_CONTROLLER
    forecast: Literal[simulate.SAMPLE_FORECASTS] = 'lightgbm_spatial'  # type: ignore[valid-type]
    episode: int = Field(default=0, ge=0, description='Index into the eligible sample episodes')


class SimulateResponse(BaseModel):
    start: str
    controller: str
    forecast: str
    episodes_available: int
    metrics: dict
    trace: list[dict]


app = FastAPI(
    title='WindGrid dispatch API',
    version=__version__,
    description=(
        'Forecast-aware battery dispatch for smoothing wind-power ramps. The controllers are the ones '
        "validated in the project's pre-registered studies; this service adds input validation, "
        'fail-closed behaviour and observability.'
    ),
)


@app.middleware('http')
async def observe(request: Request, call_next):
    request_id = request.headers.get('X-Request-ID') or uuid.uuid4().hex
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - started) * 1000
    response.headers['X-Request-ID'] = request_id
    response.headers['X-Process-Time-ms'] = f'{elapsed:.1f}'
    log.info(
        json.dumps(
            {
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'status': response.status_code,
                'ms': round(elapsed, 1),
            }
        )
    )
    return response


@app.get('/health')
def health():
    return {'status': 'ok', 'version': __version__}


@app.get('/v1/controllers')
def controllers():
    return {
        'default': service.DEFAULT_CONTROLLER,
        'controllers': [
            {'name': s.name, 'role': s.role, 'description': s.description} for s in service.CONTROLLERS.values()
        ],
        'battery': asdict(BatteryConfig()),
        'ramp_limit_kw_per_10min': 200.0,
    }


@app.post('/v1/dispatch', response_model=DispatchResponse)
def dispatch(request: DispatchRequest):
    try:
        series = service.make_series(
            [i.interval_end for i in request.history],
            [i.realised_kw for i in request.history],
            [i.forecast_kw for i in request.history],
        )
        return service.dispatch(series, request.battery_energy_kwh, request.previous_grid_kw, request.controller)
    except (service.HistoryError, ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get('/v1/sample', response_model=DispatchRequest)
def sample(controller: ControllerName = service.DEFAULT_CONTROLLER, rows: int = 200):
    """A valid dispatch request from the bundled sample (newest ``rows`` intervals of one day)."""
    if not service.MIN_HISTORY <= rows <= 1000:
        raise HTTPException(status_code=400, detail='rows must be between 40 and 1000')
    series = simulate.load_sample()['lightgbm_spatial']
    starts = simulate.sample_episode_starts('lightgbm_spatial')
    end = next((k for k in starts if k + 1 >= rows), starts[-1]) + 12  # a full window, mid-episode
    lo = max(0, end + 1 - rows)
    history = [
        {
            'interval_end': series.times[k].isoformat(),
            'realised_kw': float(series.realised[k]),
            'forecast_kw': [float(v) for v in series.predictions[k]],
        }
        for k in range(lo, end + 1)
    ]
    return {
        'controller': controller,
        'battery_energy_kwh': 1300.0,
        'previous_grid_kw': float(series.realised[end]),
        'history': history,
    }


@app.post('/v1/simulate', response_model=SimulateResponse)
def run_simulation(request: SimulateRequest):
    series = simulate.load_sample()[request.forecast]
    starts = simulate.sample_episode_starts(request.forecast)
    if request.episode >= len(starts):
        raise HTTPException(status_code=400, detail=f'episode must be < {len(starts)}')
    result = simulate.replay(series, starts[request.episode], request.controller)
    return {**result, 'episodes_available': len(starts)}
