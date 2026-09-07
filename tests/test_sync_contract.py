import subprocess
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


class SyncContractTests(unittest.TestCase):
    def test_push_plan_excludes_markdown_and_preflights_source(self):
        result = subprocess.run(
            [str(PROJECT_DIR / "synch.sh"), "push-plan"],
            cwd=PROJECT_DIR,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("main.py", result.stdout)
        self.assertIn("Preflight passed", result.stdout)
        self.assertNotIn("README.md", result.stdout)
        self.assertNotIn("QCRL_SYNC.md", result.stdout)


if __name__ == "__main__":
    unittest.main()
