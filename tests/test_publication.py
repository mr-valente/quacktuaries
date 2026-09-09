"""CI builds without a registry and sends only tested source to restricted SSH."""
import os
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class DeploymentRequestTests(unittest.TestCase):
    def test_request_pins_host_key_and_sends_only_repo_and_commit(self):
        main = runpy.run_path(str(ROOT / 'ci/deploy.py'))['main']
        env = {'GITHUB_SHA': 'a'*40, 'GITHUB_REPOSITORY': 'fixture/app', 'DEPLOY_HOST': 'vm.example.test',
               'DEPLOY_SSH_KEY': 'synthetic-key', 'DEPLOY_KNOWN_HOSTS': 'synthetic-host-key'}
        def execute(args, **kwargs):
            self.assertIn('StrictHostKeyChecking=yes', args)
            self.assertIn('BatchMode=yes', args)
            self.assertEqual(kwargs['input'], ('fixture/app ' + 'a'*40 + '\n').encode())
            key = Path(args[args.index('-i') + 1])
            self.assertEqual(key.stat().st_mode & 0o777, 0o600)
            return None
        with patch.dict(os.environ, env), patch('subprocess.run', side_effect=execute) as run:
            main()
            self.assertEqual(run.call_count, 1)
        self.assertFalse(any('docker' in str(c) for c in run.call_args_list))

    def test_bad_request_never_opens_ssh(self):
        main = runpy.run_path(str(ROOT / 'ci/deploy.py'))['main']
        for key, bad in [('GITHUB_SHA', 'main; id'), ('GITHUB_REPOSITORY', '../other'), ('DEPLOY_HOST', '-oProxyCommand=id')]:
            env = {'GITHUB_SHA': 'a'*40, 'GITHUB_REPOSITORY': 'fixture/app', 'DEPLOY_HOST': 'vm.example.test', key: bad}
            with self.subTest(key=key), patch.dict(os.environ, env), patch('subprocess.run') as run:
                with self.assertRaises(ValueError): main()
                run.assert_not_called()


if __name__ == '__main__': unittest.main()
