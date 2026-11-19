"""HTTP API: contract, validation errors, observability headers and the sample/simulate endpoints."""

import unittest

from fastapi.testclient import TestClient

from windgrid import __version__
from windgrid.api import app


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.request = cls.client.get('/v1/sample').json()

    def test_health(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'version': __version__})

    def test_controllers_listed(self):
        body = self.client.get('/v1/controllers').json()
        names = {c['name'] for c in body['controllers']}
        self.assertEqual(body['default'], 'graded_mpc')
        self.assertTrue({'graded_mpc', 'stochastic_skill', 'adaptive', 'lowpass_fast', 'uncontrolled'} <= names)

    def test_sample_has_requested_rows(self):
        self.assertEqual(len(self.request['history']), 200)

    def test_dispatch_from_sample(self):
        response = self.client.post('/v1/dispatch', json=self.request)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body['forecast_available'])
        self.assertEqual(len(body['plan']['energy_kwh']), 7)
        self.assertAlmostEqual(body['net_battery_kw'], body['discharge_kw'] - body['charge_kw'])
        self.assertIn('X-Request-ID', response.headers)
        self.assertIn('X-Process-Time-ms', response.headers)

    def test_request_id_is_echoed(self):
        response = self.client.get('/health', headers={'X-Request-ID': 'abc123'})
        self.assertEqual(response.headers['X-Request-ID'], 'abc123')

    def test_schema_violation_is_422(self):
        bad = {**self.request, 'history': [{**self.request['history'][0], 'forecast_kw': [1, 2, 3]}] * 50}
        self.assertEqual(self.client.post('/v1/dispatch', json=bad).status_code, 422)
        self.assertEqual(self.client.post('/v1/dispatch', json={**self.request, 'unexpected': 1}).status_code, 422)

    def test_gap_in_history_is_400(self):
        history = self.request['history']
        bad = {**self.request, 'history': history[:60] + history[61:]}
        response = self.client.post('/v1/dispatch', json=bad)
        self.assertEqual(response.status_code, 400)
        self.assertIn('contiguous', response.json()['detail'])

    def test_simulate_episode(self):
        response = self.client.post('/v1/simulate', json={'controller': 'lowpass_fast', 'episode': 1})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(len(body['trace']), 48)
        self.assertIn('total_ramp_exceedance_kw', body['metrics'])
        self.assertEqual(self.client.post('/v1/simulate', json={'episode': 10_000}).status_code, 400)

    def test_openapi_document(self):
        paths = self.client.get('/openapi.json').json()['paths']
        self.assertTrue({'/health', '/v1/dispatch', '/v1/controllers', '/v1/simulate', '/v1/sample'} <= set(paths))


if __name__ == '__main__':
    unittest.main()
