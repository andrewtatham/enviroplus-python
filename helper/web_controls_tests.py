"""Tests for the temperature and power parts of the web API. Nothing is really
restarted: the command runner is replaced."""
import json
import unittest
import urllib.error
import urllib.request

from helper import power
from helper import temperature_history
from helper import web_server


class FakeHeating(object):
    def __init__(self, can_stop=True):
        self.can_stop = can_stop
        self.stopped = False

    def stop_heating(self):
        self.stopped = True
        return self.can_stop

    def resume_heating(self):
        self.stopped = False


class WebControlsTestCase(unittest.TestCase):
    def setUp(self):
        self.ran = []
        self.addCleanup(setattr, power, 'run', power.run)
        power.run = self.ran.append

    def serve(self, heating):
        server = web_server.start(0, heating=heating)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.url = 'http://127.0.0.1:{}'.format(server.server_address[1])

    def request(self, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.url + path, data, {'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())

    def test_temperature_keeps_the_latest_readings(self):
        temperature_history._samples.clear()
        self.addCleanup(temperature_history._samples.clear)
        for i in range(temperature_history.SIZE + 5):
            temperature_history.record(i)
        self.serve(None)
        samples = self.request('/api/temperature')[1]['samples']
        self.assertEqual(len(samples), 160)
        self.assertEqual((samples[0]['c'], samples[-1]['c']), (5, 164))

    def test_restart_and_shutdown_stop_the_heater_first(self):
        for action in ('restart', 'shutdown'):
            heating = FakeHeating()
            self.serve(heating)
            self.assertEqual(self.request('/api/power', {'action': action})[0], 200)
            self.assertTrue(heating.stopped)
        self.assertEqual(self.ran, ['restart', 'shutdown'])

    def test_heater_failure_blocks_unless_forced(self):
        heating = FakeHeating(can_stop=False)
        self.serve(heating)
        self.assertEqual(self.request('/api/power', {'action': 'shutdown'})[0], 409)
        self.assertEqual(self.ran, [])
        self.assertFalse(heating.stopped)
        self.assertEqual(self.request('/api/power', {'action': 'shutdown', 'force': True})[0], 200)
        self.assertEqual(self.ran, ['shutdown'])

    def test_refused_command_resumes_heating(self):
        def refuse(action):
            raise RuntimeError('a password is required')
        power.run = refuse
        heating = FakeHeating()
        self.serve(heating)
        self.assertEqual(self.request('/api/power', {'action': 'restart'})[0], 500)
        self.assertFalse(heating.stopped)

    def test_bad_or_unavailable_requests(self):
        self.serve(FakeHeating())
        self.assertEqual(self.request('/api/power', {'action': 'halt'})[0], 400)
        self.serve(None)
        self.assertEqual(self.request('/api/power', {'action': 'restart'})[0], 503)
        self.assertEqual(self.ran, [])


if __name__ == '__main__':
    unittest.main()
