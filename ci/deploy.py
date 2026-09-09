#!/usr/bin/env python3
"""Send only the tested repository/commit to the VM's restricted SSH command."""
import os
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    repo, commit, host = (os.environ[k] for k in ('GITHUB_REPOSITORY', 'GITHUB_SHA', 'DEPLOY_HOST'))
    for value, pattern in [(repo, r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*'),
                           (commit, r'[a-f0-9]{40}'), (host, r'[A-Za-z0-9][A-Za-z0-9.-]*')]:
        if not re.fullmatch(pattern, value):
            raise ValueError('Invalid deployment repository, commit, or host')
    with tempfile.TemporaryDirectory() as temp:
        key, known = Path(temp) / 'key', Path(temp) / 'known_hosts'
        key.write_text(os.environ['DEPLOY_SSH_KEY'].strip() + '\n')
        key.chmod(0o600)
        known.write_text(os.environ['DEPLOY_KNOWN_HOSTS'].strip() + '\n')
        subprocess.run(['ssh', '-T', '-i', str(key), '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
                        '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(known),
                        '-o', 'ConnectTimeout=15', 'athenaeum-deploy@' + host],
                       input=(repo + ' ' + commit + '\n').encode(), check=True, timeout=120)


if __name__ == '__main__':
    main()
