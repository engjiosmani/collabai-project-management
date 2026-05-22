import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class SecuritySettingsImportTests(SimpleTestCase):
    def _import_settings(self, env):
        backend_dir = Path(__file__).resolve().parents[1]
        child_env = os.environ.copy()
        child_env.update(env)
        return subprocess.run(
            [sys.executable, '-c', 'import config.settings'],
            cwd=backend_dir,
            env=child_env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_secret_key_is_required_even_when_debug_true(self):
        result = self._import_settings({'DEBUG': 'True', 'SECRET_KEY': ''})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SECRET_KEY environment variable is required', result.stderr)

    def test_production_allowed_hosts_rejects_wildcards(self):
        result = self._import_settings({
            'DEBUG': 'False',
            'SECRET_KEY': 'test-secret-key-for-settings-import',
            'ALLOWED_HOSTS': 'api.example.com,*',
        })

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ALLOWED_HOSTS must not contain wildcards', result.stderr)
