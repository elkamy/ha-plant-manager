"""Unit tests for watering detection and the next-watering estimate."""

import importlib.util
import sys
import unittest
from pathlib import Path


PATH = Path(__file__).parents[1] / "custom_components" / "plant_manager" / "watering.py"
SPEC = importlib.util.spec_from_file_location("plant_manager_watering", PATH)
WATERING = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = WATERING
SPEC.loader.exec_module(WATERING)
WateringTracker = WATERING.WateringTracker

HOUR = 3600
DAY = 24 * HOUR


def feed(tracker, values, start=0, step=HOUR):
    """Add hourly readings and return the times of the confirmed waterings."""
    confirmed = []
    for index, value in enumerate(values):
        time = start + index * step
        if tracker.add(time, value):
            confirmed.append(tracker.last_watered)
    return confirmed


class DetectionTests(unittest.TestCase):
    def test_a_lasting_rise_is_a_watering_dated_at_the_rise(self):
        tracker = WateringTracker()
        self.assertEqual(feed(tracker, [32, 31, 30, 62, 61, 60]), [3 * HOUR])

    def test_a_lone_glitch_is_not_a_watering(self):
        # Real case: a soil sensor reported 100 → 20 → 100 %, and the reverse.
        tracker = WateringTracker()
        self.assertEqual(feed(tracker, [30, 30, 90, 30, 30]), [])
        self.assertIsNone(tracker.last_watered)

    def test_a_small_rise_is_not_a_watering(self):
        self.assertEqual(feed(WateringTracker(), [30, 31, 40, 42, 41]), [])

    def test_a_watering_is_counted_once(self):
        tracker = WateringTracker()
        self.assertEqual(len(feed(tracker, [30, 30, 65, 66, 65, 64, 64, 63])), 1)

    def test_two_waterings_days_apart(self):
        values = [30, 30, 65, 64] + [64 - i for i in range(1, 40)] + [70, 69]
        self.assertEqual(len(feed(WateringTracker(), values)), 2)

    def test_manual_watering(self):
        tracker = WateringTracker()
        tracker.mark_watered(5 * HOUR)
        self.assertEqual(tracker.last_watered, 5 * HOUR)

    def test_out_of_order_readings_are_ignored(self):
        tracker = WateringTracker()
        feed(tracker, [30, 30])
        self.assertFalse(tracker.add(0, 80))
        self.assertEqual(tracker.readings[-1], (HOUR, 30))

    def test_frequent_readings_are_thinned_and_history_is_bounded(self):
        tracker = WateringTracker()
        for minute in range(0, 60, 5):
            tracker.add(minute * 60, 50)
        self.assertLessEqual(len(tracker.readings), 5)
        tracker.add(30 * DAY, 40)
        self.assertEqual(tracker.readings, [(30 * DAY, 40)])


class EstimateTests(unittest.TestCase):
    def tracker_drying(self, per_hour=0.5, hours=24, start_value=70):
        tracker = WateringTracker()
        feed(tracker, [start_value - per_hour * i for i in range(hours + 1)])
        return tracker, hours * HOUR, start_value - per_hour * hours

    def test_drying_rate_from_a_steady_decrease(self):
        tracker, now, _ = self.tracker_drying(per_hour=0.5)
        self.assertAlmostEqual(tracker.drying_rate(now), 0.5)

    def test_next_watering_when_the_threshold_is_reached(self):
        tracker, now, current = self.tracker_drying(per_hour=0.5)  # 58 % now
        self.assertAlmostEqual(tracker.next_watering(now, current, 30), now + 56 * HOUR)

    def test_already_dry_needs_water_now(self):
        tracker, now, _ = self.tracker_drying()
        self.assertEqual(tracker.next_watering(now, 25, 30), now)

    def test_no_estimate_without_enough_data_or_drying(self):
        tracker = WateringTracker()
        feed(tracker, [60, 59])
        self.assertIsNone(tracker.next_watering(HOUR, 59, 30))
        steady = WateringTracker()
        feed(steady, [60] * 24)
        self.assertIsNone(steady.next_watering(23 * HOUR, 60, 30))
        self.assertIsNone(steady.next_watering(23 * HOUR, None, 30))

    def test_no_estimate_beyond_two_months(self):
        # 97 % losing 0.06 point an hour reaches 0 % in about 67 days.
        tracker, now, current = self.tracker_drying(per_hour=0.06, hours=48, start_value=100)
        self.assertIsNone(tracker.next_watering(now, current, 0))

    def test_rate_ignores_the_time_before_the_last_watering_and_glitches(self):
        tracker = WateringTracker()
        values = [30, 30, 80, 80, 80] + [80 - i for i in range(1, 20)]
        values[12] = 20  # a lone glitch while drying
        feed(tracker, values)
        now = (len(values) - 1) * HOUR
        self.assertAlmostEqual(tracker.drying_rate(now), 1.0, places=1)


class PersistenceTests(unittest.TestCase):
    def test_round_trip(self):
        tracker = WateringTracker()
        feed(tracker, [30, 30, 65, 64])
        restored = WateringTracker.from_dict(tracker.as_dict())
        self.assertEqual(restored.last_watered, tracker.last_watered)
        self.assertEqual(restored.readings, tracker.readings)

    def test_tolerates_missing_or_corrupt_data(self):
        self.assertIsNone(WateringTracker.from_dict(None).last_watered)
        tracker = WateringTracker.from_dict({"readings": [["x", 1], [1, 2]], "last_watered": "bad"})
        self.assertEqual(tracker.readings, [(1.0, 2.0)])
        self.assertIsNone(tracker.last_watered)


if __name__ == "__main__":
    unittest.main()
