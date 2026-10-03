"""Exercise the deployed wrapper with fake AWS and runuser commands."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


TEMPLATE = Path(__file__).parents[1] / "infra/aws/qcrl-collector.yaml"
ARN_PREFIX = "arn:aws:secretsmanager:us-east-2:123456789012:secret:probe-"


class ProbeConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        template = TEMPLATE.read_text()
        wrapper = textwrap.dedent(template.split(
            "cat >/usr/local/bin/qcrl-authenticated-probe <<'SHELL'\n", 1
        )[1].split("          SHELL\n", 1)[0])
        # Tests run as an ordinary user; the deployed wrapper still requires root.
        root_guard = '''if [[ "$EUID" -ne 0 ]]; then
  echo "Run with sudo; the secret is streamed directly to the unprivileged probe." >&2
  exit 2
fi
'''
        self.assertIn(root_guard, wrapper)
        wrapper = wrapper.replace(root_guard, "")
        envfile = self.root / "collector.env"
        envfile.write_text(
            'QCRL_PROBE_CONFIG_PARAMETER=/qcrl/test/probe-secret-arn\n'
            'QCRL_PROJECT_DIR=/opt/qcrl\n'
            'QCRL_PROBE_SECRET_ARN=stale-value\n'
        )
        wrapper = wrapper.replace("/etc/qcrl-collector.env", str(envfile))
        self.wrapper = self.root / "wrapper"
        self.wrapper.write_text(wrapper)
        aws = self.root / "aws"
        aws.write_text(textwrap.dedent('''\
            #!/usr/bin/env python3
            import json, os, sys
            with open(os.environ['CALL_LOG'], 'a') as handle:
                handle.write(json.dumps(sys.argv[1:]) + '\\n')
            if sys.argv[1:3] == ['ssm', 'get-parameter']:
                if os.environ.get('SSM_FAILURE'):
                    raise SystemExit(9)
                print(os.environ['PARAM_VALUE'])
            elif sys.argv[1:3] == ['secretsmanager', 'get-secret-value']:
                print('{"synthetic":true}')
            else:
                raise SystemExit(10)
        '''))
        aws.chmod(0o755)
        runuser = self.root / "runuser"
        runuser.write_text('#!/bin/sh\ncat >/dev/null\nprintf "probe executed\\n"\n')
        runuser.chmod(0o755)

    def run_probe(self, value, *, failure=False):
        log = self.root / "calls.jsonl"
        log.write_text("")
        env = dict(os.environ, PATH=f"{self.root}:{os.environ['PATH']}",
                   PARAM_VALUE=value, CALL_LOG=str(log))
        if failure:
            env['SSM_FAILURE'] = '1'
        else:
            env.pop('SSM_FAILURE', None)
        result = subprocess.run(['bash', str(self.wrapper), '0x' + 'ab' * 32],
                                env=env, text=True, capture_output=True)
        return result, [json.loads(line) for line in log.read_text().splitlines()]

    def test_reads_updated_reference_on_each_invocation(self):
        for suffix in ('old', 'new'):
            result, calls = self.run_probe(ARN_PREFIX + suffix)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(['ssm', 'get-parameter'], calls[0][:2])
            self.assertEqual(ARN_PREFIX + suffix,
                             calls[1][calls[1].index('--secret-id') + 1])
            self.assertNotIn('synthetic', result.stdout)

    def test_disabled_configuration_never_reads_secret(self):
        result, calls = self.run_probe('disabled')
        self.assertEqual(2, result.returncode)
        self.assertEqual(1, len(calls))
        self.assertIn('not configured', result.stderr)

    def test_invalid_reference_never_reads_secret(self):
        for value in ('', 'None', 'wrong-reference', ARN_PREFIX + ';echo bad'):
            with self.subTest(value=value):
                result, calls = self.run_probe(value)
                self.assertEqual(2, result.returncode)
                self.assertEqual(1, len(calls))

    def test_ssm_failure_fails_closed(self):
        result, calls = self.run_probe(ARN_PREFIX + 'new', failure=True)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(1, len(calls))

    def test_shell_syntax(self):
        result = subprocess.run(['bash', '-n', str(self.wrapper)], capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == '__main__':
    unittest.main()
