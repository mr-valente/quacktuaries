"""Deployment regressions using a real server and disposable SQLite database."""
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.parse import urlencode, urlsplit


class DeploymentTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        self.env = dict(os.environ, APP_ENV='production', ROOT_PATH='/quacktuaries',
                        SESSION_SECRET='deployment-fixture-' + 'x' * 40,
                        DB_PATH=str(self.data / 'app.db'), PORT=str(self.port),
                        FORWARDED_ALLOW_IPS='127.0.0.1')
        self.env.pop('SESSION_SECRET_FILE', None)
        self.start()
        self.addCleanup(self.stop)

    def start(self):
        self.process = subprocess.Popen([sys.executable, '-m', 'app'], env=self.env,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            if self.process.poll() is not None:
                self.fail('Server exited during startup')
            try:
                if self.request('GET', '/_health')[0] == 200:
                    break
            except OSError:
                pass
            time.sleep(0.05)
        else:
            self.fail('Server did not become ready')

    def stop(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()

    def request(self, method, path, form=None, cookie=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        headers = {'Host': 'valentemath.com', 'X-Forwarded-Proto': 'https'}
        if cookie:
            headers['Cookie'] = cookie
        if form is not None:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        conn.request(method, path, body=urlencode(form) if form is not None else None, headers=headers)
        response = conn.getresponse()
        result = response.status, dict(response.getheaders()), response.read().decode()
        conn.close()
        return result

    def test_prefixed_login_forms_redirects_cookie_and_readiness(self):
        status, _, html = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn('https://valentemath.com/quacktuaries/join', html)
        status, headers, body = self.request('GET', '/static/favicon.svg')
        self.assertEqual(status, 200)
        self.assertIn('image/svg+xml', headers['content-type'])
        self.assertIn('<svg', body)
        status, headers, _ = self.request('POST', '/admin/login', {'teacher_name': 'Fixture Teacher'})
        self.assertEqual(status, 303)
        self.assertEqual(headers['location'], 'https://valentemath.com/quacktuaries/admin/dashboard')
        cookie = headers['set-cookie']
        for part in ('quacktuaries_session=', 'path=/quacktuaries', 'httponly', 'secure', 'samesite=lax'):
            self.assertIn(part, cookie.lower())
        self.assertNotIn('domain=', cookie.lower())
        session = cookie.split(';')[0]
        status, _, html = self.request('GET', '/admin/sessions/new', cookie=session)
        self.assertEqual(status, 200)
        self.assertIn('https://valentemath.com/quacktuaries/admin/session/create', html)
        status, headers, _ = self.request('POST', '/admin/session/create', {'device_count': 2}, session)
        self.assertEqual(status, 303)
        path = urlsplit(headers['location']).path.removeprefix('/quacktuaries')
        session_id = path.rsplit('/', 1)[1]
        self.assertEqual(self.request('POST', f'/admin/session/{session_id}/start', {}, session)[0], 303)
        status, _, html = self.request('GET', path, cookie=session)
        self.assertEqual(status, 200)
        self.assertIn('https://valentemath.com/quacktuaries/api/session/', html)
        self.assertIn('/timer', html)
        # Neither a generic sibling cookie nor an absent session authenticates.
        for other in (None, session.replace('quacktuaries_session=', 'session=')):
            status, headers, _ = self.request('GET', '/admin/dashboard', cookie=other)
            self.assertEqual(status, 303)
            self.assertEqual(headers['location'], 'https://valentemath.com/quacktuaries/admin/')
        # Readiness must not recreate an unexpectedly missing database.
        database = self.data / 'app.db'
        database.rename(self.data / 'held.db')
        status, _, body = self.request('GET', '/_health')
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body), {'status': 'unavailable'})
        self.assertFalse(database.exists())

    def test_missing_production_secret_and_directory_fail_without_initializing(self):
        for change in ({'SESSION_SECRET': ''}, {'ROOT_PATH': '/../bad'},
                       {'DB_PATH': str(self.data / 'absent' / 'app.db')}):
            env = dict(self.env, **change)
            result = subprocess.run([sys.executable, '-c', 'import app.main'], env=env,
                                    capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.data / 'absent').exists())

    def operation(self, command):
        result = subprocess.run([sys.executable, '-m', 'app.operations', command], env=self.env,
                                capture_output=True, check=True, timeout=30)
        return json.loads(result.stdout)

    def test_update_gate_protects_lobbies_and_active_classes(self):
        self.assertFalse(self.operation('status')['active_class'])
        self.assertTrue(self.operation('drain')['held'])
        self.assertEqual(self.request('POST', '/admin/login', {'teacher_name': 'Held Fixture'})[0], 503)
        self.assertEqual(self.request('GET', '/_health')[0], 200)
        self.operation('release')
        _, headers, _ = self.request('POST', '/admin/login', {'teacher_name': 'Class Fixture'})
        cookie = headers['set-cookie'].split(';')[0]
        _, headers, _ = self.request('POST', '/admin/session/create', {'device_count': 2}, cookie)
        session_id = urlsplit(headers['location']).path.rsplit('/', 1)[1]
        for start in (False, True):
            if start:
                self.request('POST', f'/admin/session/{session_id}/start', {}, cookie)
            state = self.operation('drain')
            self.assertTrue(state['active_class'])
            self.assertFalse(state['held'])
            self.assertEqual(self.request('GET', '/')[0], 200)
        self.request('POST', f'/admin/session/{session_id}/end', {}, cookie)
        self.assertTrue(self.operation('drain')['held'])
        self.operation('release')

    def test_drain_waits_for_admitted_requests_before_deciding(self):
        # Hold the same shared request lock from another process and commit a
        # class before releasing it; the draining process must observe it.
        holder = subprocess.Popen([sys.executable, '-c',
            'from app.operations import LOCK; import fcntl,sys; '
            'f=open(LOCK,"a"); fcntl.flock(f,fcntl.LOCK_SH); print("ready",flush=True); sys.stdin.readline()'],
            env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.assertEqual(holder.stdout.readline().strip(), 'ready')
        drain = subprocess.Popen([sys.executable, '-m', 'app.operations', 'drain'], env=self.env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            _, headers, _ = self.request('POST', '/admin/login', {'teacher_name': 'In-flight Fixture'})
            self.request('POST', '/admin/session/create', {'device_count': 2}, headers['set-cookie'].split(';')[0])
            self.assertIsNone(drain.poll())
        finally:
            holder.communicate('\n', timeout=5)
        output, error = drain.communicate(timeout=30)
        self.assertEqual(drain.returncode, 0, error)
        self.assertTrue(json.loads(output)['active_class'])
        self.assertFalse(json.loads(output)['held'])

    def test_standalone_root_deployment_remains_usable(self):
        self.stop()
        self.env['ROOT_PATH'] = ''
        self.start()
        status, _, html = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn('href="https://valentemath.com/join"', html)
        self.assertEqual(self.request('GET', '/static/favicon.svg')[0], 200)
        status, headers, _ = self.request('POST', '/admin/login', {'teacher_name': 'Standalone Fixture'})
        self.assertEqual(status, 303)
        self.assertEqual(headers['location'], 'https://valentemath.com/admin/dashboard')
        self.assertIn('path=/', headers['set-cookie'].lower())


if __name__ == '__main__':
    unittest.main()
