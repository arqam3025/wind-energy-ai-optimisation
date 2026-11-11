"""Analytical synthetic battery/unit/physical failure checks; no historical data."""
from dataclasses import FrozenInstanceError, replace
import math
import unittest

from publication_v2.stage31.battery import BatteryConfig, PhysicalError, transition, grid_export, ramp_metrics


class BatteryTests(unittest.TestCase):
    def test_default_units_and_energy_inventory(self):
        c = BatteryConfig()
        self.assertEqual(c.capacity_kwh, 2000)
        self.assertEqual(c.max_charge_kw, 1000)
        self.assertEqual(c.max_discharge_kw, 1000)
        self.assertEqual(c.min_energy_kwh, 800)
        self.assertEqual(c.max_energy_kwh, 1800)
        self.assertEqual(c.initial_energy_kwh, 1300)
        self.assertEqual(c.usable_energy_kwh, 1000)
        self.assertAlmostEqual(c.delta_t_hours, 1 / 6)
        with self.assertRaises(FrozenInstanceError):
            c.initial_soc = 0.5

    def test_ac_side_charge_energy_uses_efficiency(self):
        c = BatteryConfig()
        self.assertAlmostEqual(transition(c, 1300, 1000, 0), 1300 + 0.95 * 1000 / 6)

    def test_ac_side_discharge_divides_by_efficiency(self):
        c = BatteryConfig()
        self.assertAlmostEqual(transition(c, 1300, 0, 1000), 1300 - 1000 / (0.95 * 6))

    def test_round_trip_ac_energy_and_conversion_loss(self):
        c = BatteryConfig()
        charged = transition(c, 1300, 600, 0)
        discharge = 600 * c.eta_charge * c.eta_discharge
        final = transition(c, charged, 0, discharge)
        self.assertAlmostEqual(final, 1300)
        self.assertAlmostEqual((600 - discharge) * c.delta_t_hours, 9.75)

    def test_exact_soc_boundaries_and_idle(self):
        c = BatteryConfig()
        charge = (1800 - 1700) / (c.eta_charge * c.delta_t_hours)
        discharge = (900 - 800) * c.eta_discharge / c.delta_t_hours
        self.assertAlmostEqual(transition(c, 1700, charge, 0), 1800)
        self.assertAlmostEqual(transition(c, 900, 0, discharge), 800)
        self.assertEqual(transition(c, 800, 0, 0), 800)
        self.assertEqual(transition(c, 1800, 0, 0), 1800)

    def test_soc_violations_are_rejected_not_clipped(self):
        c = BatteryConfig()
        for e, charge, discharge in ((800, 0, 1), (1800, 1, 0), (799, 0, 0), (1801, 0, 0)):
            with self.subTest(values=(e, charge, discharge)), self.assertRaises(PhysicalError):
                transition(c, e, charge, discharge)

    def test_power_limit_negative_and_simultaneous_commands(self):
        c = BatteryConfig()
        for charge, discharge in ((1001, 0), (0, 1001), (-1, 0), (0, -1), (1, 1)):
            with self.subTest(commands=(charge, discharge)), self.assertRaises(PhysicalError):
                transition(c, 1300, charge, discharge)

    def test_tolerance_does_not_silently_clip_state(self):
        c = BatteryConfig()
        tiny_charge = 1e-7
        raw = transition(c, 1800, tiny_charge, 0)
        self.assertGreater(raw, 1800)
        self.assertAlmostEqual(raw, 1800 + c.eta_charge * tiny_charge * c.delta_t_hours)
        with self.assertRaises(PhysicalError):
            transition(c, 1800, tiny_charge, 0, tolerance=0)

    def test_nonfinite_boolean_and_unsupported_commands(self):
        c = BatteryConfig()
        for bad in (True, False, math.nan, math.inf, -math.inf, '1', None, 10**1000):
            for position in range(3):
                args = [1300, 0, 0]
                args[position] = bad
                with self.subTest(value=repr(bad)[:20], position=position), self.assertRaises(PhysicalError):
                    transition(c, *args)
        for bad in (-1, True, math.nan, math.inf, '1'):
            with self.assertRaises(PhysicalError):
                transition(c, 1300, 0, 0, tolerance=bad)
        with self.assertRaises(PhysicalError):
            transition(object(), 1300, 0, 0)

    def test_invalid_configuration(self):
        c = BatteryConfig()
        changes = [dict(capacity_kwh=0), dict(capacity_kwh=-1), dict(max_charge_kw=-1),
                   dict(max_discharge_kw=-1), dict(min_soc=-0.1), dict(max_soc=1.1),
                   dict(min_soc=0.9), dict(initial_soc=0.3), dict(initial_soc=1),
                   dict(eta_charge=0), dict(eta_discharge=0), dict(eta_charge=1.01),
                   dict(eta_discharge=1.01), dict(step_minutes=0), dict(step_minutes=1.5),
                   dict(step_minutes=True), dict(step_minutes=10**1000)]
        for row in changes:
            with self.subTest(change=row), self.assertRaises(PhysicalError):
                replace(c, **row)
        for name in ('capacity_kwh', 'max_charge_kw', 'max_discharge_kw', 'min_soc',
                     'max_soc', 'initial_soc', 'eta_charge', 'eta_discharge'):
            for value in (True, math.nan, math.inf, None):
                with self.subTest(field=name, value=value), self.assertRaises(PhysicalError):
                    replace(c, **{name: value})

    def test_configurable_units_and_idle_only_power_limits(self):
        c = BatteryConfig(capacity_kwh=1000, min_soc=0.1, max_soc=0.9, initial_soc=0.5,
                          eta_charge=1, eta_discharge=1, step_minutes=15)
        self.assertEqual(transition(c, 500, 100, 0), 525)
        idle = replace(c, max_charge_kw=0, max_discharge_kw=0)
        self.assertEqual(transition(idle, 500, 0, 0), 500)
        with self.assertRaises(PhysicalError):
            transition(idle, 500, 1, 0)

    def test_signed_grid_exchange_allows_import(self):
        self.assertEqual(grid_export(100, 200, 0), -100)
        self.assertEqual(grid_export(1000, 0, 500), 1500)
        self.assertEqual(grid_export(1000, 500, 0), 500)
        self.assertEqual(grid_export(0, 0, 0), 0)

    def test_grid_exchange_rejects_nonphysical_inputs(self):
        for bad in (-1, True, math.inf, math.nan, '1', None):
            for index in range(3):
                args = [100, 0, 0]
                args[index] = bad
                with self.subTest(value=bad, position=index), self.assertRaises(PhysicalError):
                    grid_export(*args)
        with self.assertRaises(PhysicalError):
            grid_export(1e308, 0, 1e308)

    def test_ramp_magnitude_threshold_equality_and_exceedance(self):
        self.assertEqual(ramp_metrics(100, 400), (300, 100))
        self.assertEqual(ramp_metrics(100, -100), (200, 0))
        self.assertEqual(ramp_metrics(-400, 100), (500, 300))
        self.assertEqual(ramp_metrics(100, 100), (0, 0))
        self.assertEqual(ramp_metrics(10, 0, 0), (10, 10))

    def test_ramp_invalid_reference_and_unsupported_values(self):
        for args in ((0, 0, -1), (True, 0, 200), (0, math.nan, 200), (0, 0, True),
                     (0, 0, math.inf), (1e308, -1e308, 200)):
            with self.subTest(args=args), self.assertRaises(PhysicalError):
                ramp_metrics(*args)


if __name__ == '__main__':
    unittest.main()
