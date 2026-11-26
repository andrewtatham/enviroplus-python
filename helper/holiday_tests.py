"""Tests for the holiday store and the web API, using a temporary holidays.json."""
import datetime
import json
import os
import tempfile
import unittest
import urllib.error
import urllib.request

from helper import holiday_store
from helper import web_server


class TempStoreTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.addCleanup(setattr, holiday_store, 'PATH', holiday_store.PATH)
        holiday_store.PATH = os.path.join(directory.name, 'holidays.json')


class HolidayStoreTestCase(TempStoreTestCase):
    def test_defaults_until_file_exists(self):
        self.assertTrue(holiday_store.is_holiday(datetime.datetime(2026, 11, 27, 9, 0)))
        self.assertFalse(holiday_store.is_holiday(datetime.date(2026, 11, 28)))

    def test_range_includes_both_ends(self):
        holiday_store.add('2026-12-24', '2026-12-31')
        for day, expected in ((23, False), (24, True), (31, True)):
            self.assertEqual(holiday_store.is_holiday(datetime.datetime(2026, 12, day, 23, 59)), expected)

    def test_single_day_and_delete(self):
        h = holiday_store.add('2027-01-04', '', 'x')
        self.assertEqual(h['to'], '2027-01-04')
        self.assertTrue(holiday_store.delete(h['id']))
        self.assertFalse(holiday_store.delete(h['id']))
        self.assertFalse(holiday_store.is_holiday(datetime.date(2027, 1, 4)))

    def test_deleting_everything_does_not_restore_defaults(self):
        self.assertTrue(holiday_store.delete('initial'))
        self.assertEqual(holiday_store.load(), [])

    def test_rejects_bad_input(self):
        for args in (('',), (None,), ('2026-02-30',), (5,), ('2026-12-02', '2026-12-01')):
            with self.assertRaises(ValueError):
                holiday_store.add(*args)

    def test_damaged_file_keeps_last_good_and_is_not_overwritten(self):
        holiday_store.add('2027-03-01')
        holiday_store.load()
        with open(holiday_store.PATH, 'w') as f:
            f.write('{nonsense')
        self.assertTrue(holiday_store.is_holiday(datetime.date(2027, 3, 1)))
        with self.assertRaises(ValueError):
            holiday_store.add('2027-04-01')
        with open(holiday_store.PATH) as f:
            self.assertEqual(f.read(), '{nonsense')


class WebServerTestCase(TempStoreTestCase):
    def setUp(self):
        super().setUp()
        server = web_server.start(0)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.url = 'http://127.0.0.1:{}'.format(server.server_address[1])

    def request(self, path, body=None, ctype='application/json'):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.url + path, data, {'Content-Type': ctype})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read()

    def test_page(self):
        status, body = self.request('/')
        self.assertEqual(status, 200)
        self.assertIn(b'<h1>Heater</h1>', body)

    def test_add_and_delete(self):
        status, body = self.request('/api/add', {'from': '2027-05-04', 'note': 'trip'})
        self.assertEqual(status, 200)
        added = [h for h in json.loads(body)['holidays'] if h['note'] == 'trip']
        self.assertEqual(self.request('/api/delete', {'id': added[0]['id']})[0], 200)
        self.assertEqual(self.request('/api/delete', {'id': added[0]['id']})[0], 404)

    def test_errors(self):
        self.assertEqual(self.request('/api/add', {'from': 'soon'})[0], 400)
        self.assertEqual(self.request('/api/add', [1])[0], 400)
        self.assertEqual(self.request('/api/add', {'from': '2027-05-04'}, 'text/plain')[0], 415)
        self.assertEqual(self.request('/holidays.json')[0], 404)


if __name__ == '__main__':
    unittest.main()
