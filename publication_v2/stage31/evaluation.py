"""Causal synthetic replay and common physical/accounting metrics."""
from dataclasses import asdict, is_dataclass, replace
from datetime import datetime, timedelta
import hashlib
import json
import math
from statistics import mean
from .battery import BatteryConfig, transition, grid_export, ramp_metrics
from .controllers import MPCConfig, CONTROLLERS, decide
from .scenarios import START, SyntheticScenario, forecast_for_step

TOLERANCE = 1e-6

def jsonable(value):
    if is_dataclass(value): return jsonable(asdict(value))
    if isinstance(value, datetime): return value.isoformat()
    if isinstance(value, dict): return {str(k):jsonable(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [jsonable(v) for v in value]
    return value


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(jsonable(value), sort_keys=True, separators=(',',':'), allow_nan=False).encode()).hexdigest()


def validate_plan(plan, battery, initial_energy_kwh, expected_horizon=6):
    if plan is None: return 0.
    charge,discharge,energy = plan['charge_kw'],plan['discharge_kw'],plan['energy_kwh']
    if len(charge)!=expected_horizon or len(discharge)!=expected_horizon or len(energy)!=expected_horizon+1 or abs(energy[0]-initial_energy_kwh)>TOLERANCE:
        raise ValueError('Invalid six-step plan boundary')
    largest=0.
    for i,(c,d) in enumerate(zip(charge,discharge)):
        next_energy=transition(battery,energy[i],c,d)
        largest=max(largest,abs(next_energy-energy[i+1]))
    if largest>TOLERANCE: raise ValueError('Predicted energy conservation failed')
    return largest


def summarize_trace(rows, battery, config):
    if not rows: raise ValueError('No synthetic intervals to score')
    dt=battery.delta_t_hours
    charge=sum(r['charge_kw'] for r in rows)*dt
    discharge=sum(r['discharge_kw'] for r in rows)*dt
    loss=sum(((1-battery.eta_charge)*r['charge_kw']+(1/battery.eta_discharge-1)*r['discharge_kw'])*dt for r in rows)
    wind=sum(r['wind_kw'] for r in rows)*dt
    exported=sum(max(0.,r['grid_kw']) for r in rows)*dt
    imported=sum(max(0.,-r['grid_kw']) for r in rows)*dt
    energies=[rows[0]['energy_before_kwh']]+[r['energy_after_kwh'] for r in rows]
    residuals=[];power_residuals=[];soc_violations=0;power_violations=0;simultaneous=0;grid_violations=0
    for i,r in enumerate(rows):
        values=[r[k] for k in ('wind_kw','grid_kw','charge_kw','discharge_kw','energy_before_kwh','energy_after_kwh','ramp_kw','ramp_exceedance_kw')]
        if not all(math.isfinite(x) for x in values):raise ValueError('Nonfinite synthetic trace')
        if i and abs(r['energy_before_kwh']-rows[i-1]['energy_after_kwh'])>TOLERANCE:raise ValueError('Battery state discontinuity')
        predicted=r['energy_before_kwh']+battery.eta_charge*r['charge_kw']*dt-r['discharge_kw']*dt/battery.eta_discharge
        residuals.append(abs(r['energy_after_kwh']-predicted))
        power_residuals.append(abs(r['grid_kw']-(r['wind_kw']+r['discharge_kw']-r['charge_kw'])))
        expected_ramp,expected_excess=ramp_metrics(r['grid_kw'],r['previous_grid_kw'],config.ramp_limit_kw)
        if abs(r['ramp_kw']-expected_ramp)>TOLERANCE or abs(r['ramp_exceedance_kw']-expected_excess)>TOLERANCE:raise ValueError('Inconsistent ramp metric')
        if i and abs(r['previous_grid_kw']-rows[i-1]['grid_kw'])>TOLERANCE:raise ValueError('Grid anchor discontinuity')
        soc_violations+=any(e<battery.min_energy_kwh-TOLERANCE or e>battery.max_energy_kwh+TOLERANCE for e in (r['energy_before_kwh'],r['energy_after_kwh']))
        power_violations+=r['charge_kw']<-TOLERANCE or r['discharge_kw']<-TOLERANCE or r['charge_kw']>battery.max_charge_kw+TOLERANCE or r['discharge_kw']>battery.max_discharge_kw+TOLERANCE
        simultaneous+=r['charge_kw']>TOLERANCE and r['discharge_kw']>TOLERANCE
        grid_violations+=(config.grid_min_kw is not None and r['grid_kw']<config.grid_min_kw-TOLERANCE) or (config.grid_max_kw is not None and r['grid_kw']>config.grid_max_kw+TOLERANCE)
    delta=energies[-1]-energies[0]
    balance=wind+imported-exported-delta-loss
    return {'intervals':len(rows),'ramp_violations':sum(r['ramp_exceedance_kw']>TOLERANCE for r in rows),
        'total_ramp_exceedance_kw':sum(r['ramp_exceedance_kw'] for r in rows),'maximum_ramp_kw':max(r['ramp_kw'] for r in rows),
        'charge_throughput_kwh':charge,'discharge_throughput_kwh':discharge,'total_throughput_kwh':charge+discharge,
        'minimum_soc':min(energies)/battery.capacity_kwh,'maximum_soc':max(energies)/battery.capacity_kwh,
        'soc_constraint_violations':int(soc_violations),'power_constraint_violations':int(power_violations),
        'simultaneous_charge_discharge_events':int(simultaneous),'grid_limit_violations':int(grid_violations),
        'optimisation_failures':sum(r['optimization_failed'] for r in rows),'safe_fallback_events':sum(r['fallback'] for r in rows),
        'forecast_fault_events':sum(r['forecast_fault'] is not None for r in rows),
        'computation_time_s_total':sum(r['computation_time_s'] for r in rows),
        'computation_time_s_mean':mean(r['computation_time_s'] for r in rows),'computation_time_s_max':max(r['computation_time_s'] for r in rows),
        'conversion_loss_kwh':loss,'wind_energy_kwh':wind,'actual_export_energy_kwh':exported,'actual_import_energy_kwh':imported,
        'net_grid_energy_kwh':exported-imported,'initial_energy_kwh':energies[0],'terminal_energy_kwh':energies[-1],
        'terminal_inventory_change_kwh':delta,'energy_accounting_residual_kwh':balance,
        'maximum_energy_update_residual_kwh':max(residuals),'maximum_power_balance_residual_kw':max(power_residuals)}


def simulate(scenario: SyntheticScenario, controller: str, *, battery: BatteryConfig | None=None,
             config: MPCConfig | None=None):
    battery=BatteryConfig(initial_soc=scenario.initial_soc) if battery is None else battery
    config=MPCConfig(grid_min_kw=scenario.grid_min_kw,grid_max_kw=scenario.grid_max_kw) if config is None else config
    if controller not in CONTROLLERS:raise ValueError('Unknown comparison controller')
    if not scenario.wind_kw or not scenario.initial_history_kw:raise ValueError('Synthetic observation history required')
    energy=battery.initial_energy_kwh;previous_grid=scenario.initial_history_kw[-1]
    history=tuple(scenario.initial_history_kw);rows=[];plans=[]
    for index in range(len(scenario.wind_kw)):
        decision_time=START+timedelta(minutes=index*battery.step_minutes)
        forecast,fault=forecast_for_step(scenario,history,decision_time,index,step_minutes=battery.step_minutes)
        action=decide(controller,forecast,decision_time,energy,previous_grid,battery,config)
        plan_residual=validate_plan(action.plan,battery,energy,1 if controller=='heuristic' else 6)
        if action.plan is not None:
            if abs(action.charge_kw-action.plan['charge_kw'][0])>TOLERANCE or abs(action.discharge_kw-action.plan['discharge_kw'][0])>TOLERANCE:raise ValueError('Applied action is not first planned move')
        # Realized current interval is released ONLY AFTER the action is sealed.
        wind=scenario.wind_kw[index]
        next_energy=transition(battery,energy,action.charge_kw,action.discharge_kw)
        grid=grid_export(wind,action.charge_kw,action.discharge_kw)
        ramp,excess=ramp_metrics(grid,previous_grid,config.ramp_limit_kw)
        rows.append({'decision_time':decision_time.isoformat(),'interval_end':(decision_time+timedelta(minutes=battery.step_minutes)).isoformat(),
            'wind_kw':wind,'previous_grid_kw':previous_grid,'grid_kw':grid,'charge_kw':action.charge_kw,'discharge_kw':action.discharge_kw,
            'energy_before_kwh':energy,'energy_after_kwh':next_energy,'ramp_kw':ramp,'ramp_exceedance_kw':excess,
            'forecast_sha256':canonical_sha256(forecast),'forecast_fault':fault,'status':action.status,'solver_status':action.solver_status,
            'optimization_failed':action.optimization_failed,'fallback':action.fallback,'fallback_reason':action.fallback_reason,
            'computation_time_s':action.computation_time_s,'plan_energy_residual_kwh':plan_residual})
        plans.append(jsonable(action.plan));energy=next_energy;previous_grid=grid;history=history+(wind,)
    metrics=summarize_trace(rows,battery,config)
    if any(metrics[k] for k in ('soc_constraint_violations','power_constraint_violations','simultaneous_charge_discharge_events')):
        raise ValueError('A physical battery safety invariant failed')
    if abs(metrics['energy_accounting_residual_kwh'])>TOLERANCE or metrics['maximum_energy_update_residual_kwh']>TOLERANCE or metrics['maximum_power_balance_residual_kw']>TOLERANCE:raise ValueError('Physical conservation failed')
    return {'data_kind':'SYNTHETIC_ONLY','scenario':scenario.name,'controller':controller,'seed':scenario.seed,
        'wind_sha256':canonical_sha256(scenario.wind_kw),'battery':jsonable(battery),'mpc_config':jsonable(config),
        'metrics':metrics,'rows':rows,'plans':plans}


def reproducibility_payload(run):
    """Exclude wall-clock timings; their equality is not a reproducibility claim."""
    copy=json.loads(json.dumps(jsonable(run),allow_nan=False))
    for k in tuple(copy['metrics']):
        if k.startswith('computation_time_'):del copy['metrics'][k]
    for row in copy['rows']:row.pop('computation_time_s',None)
    return copy


def paired_comparisons(runs):
    groups={}
    for run in runs:
        group=groups.setdefault(run['scenario'],{})
        if run['controller'] in group:raise ValueError('Duplicate scenario/controller comparison')
        group[run['controller']]=run
    result=[]
    keys=('ramp_violations','total_ramp_exceedance_kw','maximum_ramp_kw','total_throughput_kwh','conversion_loss_kwh','terminal_inventory_change_kwh')
    for scenario,controllers in groups.items():
        if set(controllers)!=set(CONTROLLERS):raise ValueError('Incomplete controller comparison')
        reference=controllers['uncontrolled']
        reference_rows=reference['rows']
        if not reference_rows or len(reference_rows)!=reference['metrics']['intervals']:
            raise ValueError('Invalid reference interval denominator')
        reference_cohort=[(r['decision_time'],r['interval_end'],r['wind_kw']) for r in reference_rows]
        for run in controllers.values():
            rows=run['rows']
            if len(rows)!=run['metrics']['intervals'] or [(r['decision_time'],r['interval_end'],r['wind_kw']) for r in rows]!=reference_cohort:
                raise ValueError('Comparator decision/target cohort differs')
            if rows[0]['previous_grid_kw']!=reference_rows[0]['previous_grid_kw'] or rows[0]['energy_before_kwh']!=reference_rows[0]['energy_before_kwh']:
                raise ValueError('Comparator initial realised state or grid anchor differs')
            if run['wind_sha256']!=reference['wind_sha256'] or run['battery']!=reference['battery'] or run['mpc_config']!=reference['mpc_config'] or run['metrics']['intervals']!=reference['metrics']['intervals']:raise ValueError('Unpaired comparison inputs')
            if [r['forecast_sha256'] for r in run['rows']]!=[r['forecast_sha256'] for r in reference['rows']]:raise ValueError('Comparator forecasts differ')
        pairs=[(name,'uncontrolled') for name in CONTROLLERS if name!='uncontrolled']+[('adaptive','deterministic'),('adaptive','fixed_margin')]
        for left,right in pairs:
            result.append({'scenario':scenario,'left':left,'right':right,'difference_sign':'left_minus_right;positive_is_more',
                **{k:controllers[left]['metrics'][k]-controllers[right]['metrics'][k] for k in keys}})
    return result
