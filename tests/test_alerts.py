import importlib.util
import unittest
from pathlib import Path


HELPER_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "plant_manager"
    / "alerts.py"
)
SPEC = importlib.util.spec_from_file_location("plant_manager_alerts", HELPER_PATH)
ALERTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ALERTS)
should_start_alert = ALERTS.should_start_alert


class ShouldStartAlertTests(unittest.TestCase):
    def test_crossing_below_threshold_starts_alert(self):
        self.assertTrue(should_start_alert(29, 30, 30, False, False))

    def test_value_at_threshold_does_not_start_alert(self):
        self.assertFalse(should_start_alert(30, 31, 30, False, False))

    def test_value_above_threshold_does_not_start_alert(self):
        self.assertFalse(should_start_alert(31, 32, 30, False, False))

    def test_already_dry_episode_does_not_repeat_alert(self):
        self.assertFalse(should_start_alert(20, 25, 30, False, False))

    def test_active_alert_does_not_repeat(self):
        self.assertFalse(should_start_alert(20, 30, 30, True, False))

    def test_pending_alert_does_not_duplicate(self):
        self.assertFalse(should_start_alert(20, 30, 30, False, True))

    def test_initial_low_reading_can_start_alert(self):
        self.assertTrue(should_start_alert(20, None, 30, False, False))


if __name__ == "__main__":
    unittest.main()
