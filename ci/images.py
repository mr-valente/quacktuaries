#!/usr/bin/env python3
"""Build and smoke-test native images without publishing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def run(*args, capture=False, timeout=900):
    return subprocess.run(list(map(str, args)), check=True, cwd=ROOT, timeout=timeout,
                          stdout=subprocess.PIPE if capture else None).stdout


def smoke(service, image):
    name = 'athenaeum-ci-' + uuid.uuid4().hex[:12]
    args = ['docker', 'run', '--detach', '--name', name, '--pull', 'never', '--network', 'none',
            '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '512m',
            '--tmpfs', '/tmp:rw,nosuid,nodev,size=32m', '--tmpfs', '/data:rw,nosuid,nodev,size=32m,uid=10001,gid=10001',
            '--tmpfs', '/config:rw,nosuid,nodev,size=32m,uid=10001,gid=10001']
    if service == 'quacktuaries':
        args += ['--env', 'APP_ENV=production', '--env', 'ROOT_PATH=/quacktuaries',
                 '--env', 'SESSION_SECRET=synthetic-ci-only-' + 'x' * 40]
    elif service == 'edge':
        args += ['--env', 'SITE_DOMAIN=localhost', '--env', 'ACME_EMAIL=fixture@example.invalid', '--env', 'LOCAL_HTTPS_PORT=8443']
    args += [image]
    if service == 'edge':
        args += ['caddy', 'run', '--config', '/etc/caddy/Caddyfile.local', '--adapter', 'caddyfile']
    try:
        run(*args, capture=True)
        for _ in range(60):
            state = json.loads(run('docker', 'inspect', name, capture=True))[0]['State']
            if state.get('Health', {}).get('Status') == 'healthy':
                if service == 'quacktuaries':
                    status = json.loads(run('docker', 'exec', name, 'python', '-m', 'app.operations', 'drain', capture=True))
                    assert status['held'] and not status['active_class']
                    run('docker', 'exec', name, 'python', '-m', 'app.operations', 'release')
                return
            if not state['Running']:
                raise RuntimeError('Native container exited')
            time.sleep(1)
        raise RuntimeError('Native container health deadline exceeded')
    finally:
        run('docker', 'rm', '--force', name, capture=True)


def check_operations():
    spec = {'x86_64': ('amd64', 'cbe24006683f8eb669266162894b9a522a1af52f2665fbc63a4bb032ed26ac10'),
            'aarch64': ('arm64', '6b8dc4333c53a5a57c9e5834e3a48f92605d7154014cd07269ff3327db5d37f4')}
    target, expected = spec[platform.machine()]
    import tarfile
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        with urllib.request.urlopen(f'https://github.com/FiloSottile/age/releases/download/v1.3.2/age-v1.3.2-linux-{target}.tar.gz', timeout=30) as source:
            raw = source.read(20_000_000)
        assert hashlib.sha256(raw).hexdigest() == expected, 'age checksum mismatch'
        archive = work / 'age.tgz'
        archive.write_bytes(raw)
        with tarfile.open(archive) as tar:
            for binary in ('age', 'age-keygen'):
                dest = work / binary
                dest.write_bytes(tar.extractfile('age/' + binary).read())
                dest.chmod(0o700)
        env = dict(os.environ, ATHENAEUM_TEST_AGE=str(work / 'age'))
        subprocess.run(['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
                       cwd=ROOT, env=env, check=True, timeout=300)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['check', 'build'])
    args = parser.parse_args()
    contract = json.loads((ROOT / 'ci/images.json').read_text())['services']
    arch = {'x86_64': 'amd64', 'aarch64': 'arm64'}[platform.machine()]
    if args.command in ('check', 'build'):
        for service, c in contract.items():
            image = 'athenaeum-ci-' + service + ':local'
            run('docker', 'buildx', 'build', '--load', '--platform', 'linux/' + arch, '--file', c['dockerfile'], '--tag', image, '.')
            smoke(service, image)
            if service == 'quacktuaries':
                run('docker', 'run', '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                    '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,nosuid,nodev,size=64m',
                    '--mount', f'type=bind,src={ROOT / "tests"},dst=/tests,readonly', image,
                    'python', '-m', 'unittest', 'discover', '-s', '/tests', '-p', 'test_deployment.py', '-v')
                run('python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_publication.py', '-v')
        if args.command == 'check' and 'athenaeum' in contract:
            check_operations()
        return


if __name__ == '__main__':
    main()
