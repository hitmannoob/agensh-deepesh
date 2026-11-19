import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agensh.team_run import setting_int  # noqa: E402


class SettingTest(unittest.TestCase):
    def test_environment_then_profile_then_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AGENSH_PLANNING_TIMEOUT_S', None)
            self.assertEqual(setting_int({}, 'AGENSH_PLANNING_TIMEOUT_S', 2700), 2700)
            self.assertEqual(setting_int({'AGENSH_PLANNING_TIMEOUT_S': '900'}, 'AGENSH_PLANNING_TIMEOUT_S', 2700), 900)
            os.environ['AGENSH_PLANNING_TIMEOUT_S'] = '60'
            self.assertEqual(setting_int({'AGENSH_PLANNING_TIMEOUT_S': '900'}, 'AGENSH_PLANNING_TIMEOUT_S', 2700), 60)


if __name__ == '__main__':
    unittest.main()
