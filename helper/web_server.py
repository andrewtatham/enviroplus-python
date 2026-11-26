"""Tiny dependency-free web UI for managing holiday dates. No authentication:
intended for the home network only."""
import datetime
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from helper import holiday_store

PAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web', 'index.html')
MAX_BODY = 4096


class Handler(BaseHTTPRequestHandler):
    timeout = 30

    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype='application/json'):
        if isinstance(body, dict):
            body = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def _state(self):
        today = datetime.date.today()
        return {'today': today.isoformat(),
                'on_holiday': holiday_store.is_holiday(today),
                'holidays': holiday_store.load()}

    def do_GET(self):
        path = self.path.split('?')[0]
        if path in ('/', '/index.html'):
            with open(PAGE, 'rb') as f:
                return self._send(200, f.read(), 'text/html; charset=utf-8')
        if path == '/api/state':
            return self._send(200, self._state())
        self._send(404, {'error': 'not found'})

    def do_POST(self):
        # Requiring a JSON content type stops other websites posting forms here.
        if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            return self._send(415, {'error': 'expected application/json'})
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 <= length <= MAX_BODY:
                raise ValueError
            data = json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(data, dict):
                raise ValueError
        except ValueError:
            return self._send(400, {'error': 'bad request'})

        path = self.path.split('?')[0]
        try:
            if path == '/api/add':
                holiday = holiday_store.add(data.get('from'), data.get('to'), data.get('note'))
                logging.info('web: holiday added {from} to {to}'.format(**holiday))
            elif path == '/api/delete':
                if not holiday_store.delete(data.get('id')):
                    return self._send(404, {'error': 'That holiday no longer exists'})
                logging.info('web: holiday deleted')
            else:
                return self._send(404, {'error': 'not found'})
        except ValueError as exc:
            return self._send(400, {'error': str(exc)})
        except OSError as exc:
            logging.warning('web: unable to save holidays: {}'.format(exc))
            return self._send(500, {'error': 'Unable to save'})
        self._send(200, self._state())


def start(port=8080):
    """Serve in a background thread. Returns None if the port is unavailable,
    because heater control matters more than the web page."""
    try:
        server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    except OSError as exc:
        logging.warning('web: unable to listen on port {}: {}'.format(port, exc))
        return None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logging.info('web: listening on port {}'.format(server.server_address[1]))
    return server
