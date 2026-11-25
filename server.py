#!/usr/bin/env python3
"""Local order-service fixture for LogiQlink's QA automation exercise.
Uses only Python's standard library. Deliberate contract defects are present.
"""
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST, PORT = '127.0.0.1', 8765
TOKEN = 'qa-assessment-token'
PRICES = {'NOTEBOOK': 150, 'MOUSE': 800}
lock = threading.Lock()
orders = {}
requests = {}
next_id = 1

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def send_json(self, code, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size <= 0 or size > 100000:
                raise ValueError('Invalid body size')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('JSON object required')
            return data
        except (ValueError, json.JSONDecodeError):
            return None

    def auth(self):
        if self.headers.get('Authorization') != f'Bearer {TOKEN}':
            self.send_json(401, {'error': 'unauthorized'})
            return False
        return True

    def do_GET(self):
        path = urlparse(self.path)
        if path.path == '/health':
            self.send_json(200, {'status': 'ok'})
            return
        if not self.auth():
            return
        if path.path == '/orders':
            status = parse_qs(path.query).get('status', [None])[0]
            if status is not None and status not in ('created', 'shipped', 'cancelled'):
                self.send_json(400, {'error': 'invalid_status'})
                return
            with lock:
                result = [dict(v) for v in orders.values()]
            # Intentional contract defect: status query is ignored.
            self.send_json(200, {'orders': result, 'count': len(result)})
            return
        if path.path.startswith('/orders/'):
            oid = path.path.split('/')[-1]
            with lock:
                order = orders.get(oid)
                result = dict(order) if order is not None else None
            if result is None:
                self.send_json(404, {'error': 'not_found'})
            else:
                self.send_json(200, result)
            return
        self.send_json(404, {'error': 'not_found'})

    def do_POST(self):
        global next_id
        path = urlparse(self.path).path
        if not self.auth():
            return
        if path == '/test/reset':
            with lock:
                orders.clear()
                requests.clear()
                next_id = 1
            self.send_json(200, {'reset': True})
            return
        if path == '/orders':
            data = self.read_json()
            if data is None:
                self.send_json(400, {'error': 'invalid_json'})
                return
            sku = data.get('sku')
            qty = data.get('quantity')
            email = data.get('customerEmail')
            request_id = data.get('requestId')
            if (sku not in PRICES or type(qty) is not int or qty < 0 or qty > 5
                or not isinstance(email, str) or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email)
                or not isinstance(request_id, str) or not request_id.strip()):
                # Intentional contract defect: quantity=0 is accepted.
                self.send_json(400, {'error': 'validation_failed'})
                return
            with lock:
                if request_id in requests:
                    existing = dict(orders[requests[request_id]])
                    self.send_json(200, existing)
                    return
                oid = f'ord-{next_id:04d}'
                next_id += 1
                item = {'id': oid, 'sku': sku, 'quantity': qty,
                        'customerEmail': email, 'requestId': request_id,
                        'total': PRICES[sku] * qty, 'status': 'created'}
                orders[oid] = item
                requests[request_id] = oid
                self.send_json(201, item)
                return
        match = re.fullmatch(r'/orders/(ord-\d+)/(ship|cancel)', path)
        if match:
            oid, action = match.groups()
            with lock:
                item = orders.get(oid)
                if item is None:
                    self.send_json(404, {'error': 'not_found'})
                    return
                if action == 'ship':
                    if item['status'] != 'created':
                        self.send_json(409, {'error': 'invalid_transition'})
                        return
                    item['status'] = 'shipped'
                else:
                    if item['status'] == 'cancelled':
                        self.send_json(409, {'error': 'invalid_transition'})
                        return
                    # Intentional contract defect: shipped orders can be cancelled.
                    item['status'] = 'cancelled'
                self.send_json(200, dict(item))
                return
        self.send_json(404, {'error': 'not_found'})

if __name__ == '__main__':
    print(f'Order API listening at http://{HOST}:{PORT}', flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
