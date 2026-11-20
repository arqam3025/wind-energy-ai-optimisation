"""Hill of Towie loader: role guard, year grid convention and (when present) development data."""

import unittest

import pandas as pd

from publication_v2.stage4.kelmarsh import DataAccessError
from publication_v2.stage6 import hill_of_towie as h

HAVE_2016 = (h.ROOT / 'development' / '2016.zip').exists()


class Guards(unittest.TestCase):
    def test_sealed_and_validation_years_are_refused_by_default(self):
        for year in (2024, 2025):
            with self.assertRaises(DataAccessError):
                h.archive(year)

    def test_2026_is_never_admitted(self):
        with self.assertRaises(DataAccessError):
            h.archive(2026, allow=('development', 'validation', 'sealed_test', 'excluded'))

    def test_year_grid_counts_intervals_by_start(self):
        grid = h.year_grid(2016)
        self.assertEqual(grid[0], pd.Timestamp('2016-01-01 00:10', tz='UTC'))
        self.assertEqual(grid[-1], pd.Timestamp('2017-01-01 00:00', tz='UTC'))
        self.assertEqual(len(grid), 366 * 144)

    def test_geometry_places_target_at_origin(self):
        if not (h.ROOT / 'metadata' / 'Hill_of_Towie_turbine_metadata.csv').exists():
            self.skipTest('metadata not present')
        geo = h.geometry()
        self.assertEqual(geo.loc[h.TARGET, 'distance_m'], 0.0)
        self.assertEqual(len(geo), 21)


@unittest.skipUnless(HAVE_2016, 'Hill of Towie development data not present')
class DevelopmentData(unittest.TestCase):
    def test_2016_loads_on_the_full_grid(self):
        signals = h.load_year(2016)
        power = signals['power_kw']
        self.assertTrue(power.index.equals(h.year_grid(2016)))
        self.assertEqual(list(power.columns), list(h.TURBINES))
        self.assertLess(power['T10'].isna().mean(), 0.05)
        self.assertLessEqual(power.max().max(), h.RATED_KW * 1.05)

    def test_contract_frames(self):
        signals = h.load_year(2016)
        turbine, farm = h.turbine_frame(signals), h.farm_frame(signals)
        self.assertTrue({'realised_kw', 'wind_ms', 'wind_dir_deg'} <= set(turbine.columns))
        self.assertGreaterEqual(turbine['realised_kw'].min(), 0.0)
        self.assertLessEqual(farm['realised_kw'].max(), 21 * h.RATED_KW * 1.05)


if __name__ == '__main__':
    unittest.main()
