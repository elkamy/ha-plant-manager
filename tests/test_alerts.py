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
parse_percentage = ALERTS.parse_percentage
parse_delay_minutes = ALERTS.parse_delay_minutes
normalize_notify_services = ALERTS.normalize_notify_services
normalize_notify_entities = ALERTS.normalize_notify_entities
parse_reading = ALERTS.parse_reading


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


class ConfigurationHelperTests(unittest.TestCase):
    def test_percentage_falls_back_for_non_numeric_value(self):
        self.assertEqual(parse_percentage("invalid", 30), 30.0)

    def test_percentage_falls_back_for_out_of_range_or_non_finite_values(self):
        for value in (-1, 101, float("nan"), float("inf")):
            with self.subTest(value=value):
                self.assertEqual(parse_percentage(value, 30), 30.0)

    def test_percentage_accepts_valid_numeric_strings(self):
        self.assertEqual(parse_percentage("27.5", 30), 27.5)

    def test_delay_falls_back_for_invalid_or_out_of_range_values(self):
        for value in ("invalid", -1, 1441, None):
            with self.subTest(value=value):
                self.assertEqual(parse_delay_minutes(value, 10), 10)

    def test_delay_accepts_zero_and_maximum(self):
        self.assertEqual(parse_delay_minutes(0, 10), 0)
        self.assertEqual(parse_delay_minutes(1440, 10), 1440)

    def test_notify_services_filters_invalid_and_duplicate_values(self):
        self.assertEqual(
            normalize_notify_services([
                "notify.mobile_app_phone",
                "notify.mobile_app_phone",
                "sensor.pachira",
                "notify.",
                "notify. bad",
                None,
            ]),
            ["notify.mobile_app_phone"],
        )

    def test_notify_services_accepts_single_string(self):
        self.assertEqual(
            normalize_notify_services("notify.mobile_app_phone"),
            ["notify.mobile_app_phone"],
        )

    def test_alert_helper_rejects_non_finite_readings(self):
        self.assertFalse(should_start_alert(float("nan"), 30, 30, False, False))
        self.assertFalse(should_start_alert(float("inf"), 30, 30, False, False))

    def test_alert_helper_rejects_out_of_range_current_readings(self):
        self.assertFalse(should_start_alert(-1, 30, 30, False, False))
        self.assertFalse(should_start_alert(101, 30, 30, False, False))

    def test_invalid_previous_reading_is_treated_as_missing(self):
        for previous in (-1, 101, float("nan"), float("inf")):
            with self.subTest(previous=previous):
                self.assertTrue(
                    should_start_alert(20, previous, 30, False, False)
                )


    def test_parse_reading_accepts_only_finite_percentages(self):
        self.assertEqual(parse_reading("42.5"), 42.5)
        self.assertEqual(parse_reading(0), 0.0)
        self.assertEqual(parse_reading("100"), 100.0)
        for value in ("unknown", "", None, "nan", "inf", -1, 101):
            with self.subTest(value=value):
                self.assertIsNone(parse_reading(value))

    def test_notify_entities_keeps_unique_valid_entity_ids(self):
        self.assertEqual(
            normalize_notify_entities([
                "notify.phone",
                "notify.phone",
                "notify.",
                "notify.a.b",
                "notify. bad",
                "light.kitchen",
                None,
                "notify.tablet",
            ]),
            ["notify.phone", "notify.tablet"],
        )

    def test_notify_entities_accepts_single_string_and_rejects_other_types(self):
        self.assertEqual(normalize_notify_entities("notify.phone"), ["notify.phone"])
        self.assertEqual(normalize_notify_entities(""), [])
        self.assertEqual(normalize_notify_entities(42), [])


if __name__ == "__main__":
    unittest.main()
