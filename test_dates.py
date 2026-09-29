import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from preprocessor import DataPreprocessor


class DateParsingTests(unittest.TestCase):
    def setUp(self):
        self.parser = DataPreprocessor()

    def test_zero_dates_use_display_and_visual_year(self):
        source = {
            "ad_year": "0000",
            "ad_mainvisual": "https://example.test/data/ad/202609/image.jpg",
            "start_date": "0000-00-00",
            "end_date": "0000-00-00",
        }
        result = self.parser.parse_dates("10월 17일(토) ~ 10월 18일(일)", source)
        self.assertEqual((result["start_date"], result["end_date"]),
                         ("2026-10-17", "2026-10-18"))

    def test_valid_api_dates_take_priority(self):
        result = self.parser.parse_dates("10월 17일 ~ 18일", {
            "start_date": "2027-10-17", "end_date": "2027-10-18"})
        self.assertEqual(result["start_date"], "2027-10-17")
        self.assertEqual(result["end_date"], "2027-10-18")

    def test_cross_year_range(self):
        result = self.parser.parse_dates("12월 31일 ~ 1월 1일", {"ad_year": "2026"})
        self.assertEqual(result["start_date"], "2026-12-31")
        self.assertEqual(result["end_date"], "2027-01-01")

    def test_invalid_calendar_day_is_not_emitted(self):
        result = self.parser.parse_dates("2월 30일", {
            "ad_year": "2026", "start_date": "0000-00-00"})
        self.assertIsNone(result["start_date"])
        self.assertIsNone(result["end_date"])


if __name__ == "__main__":
    unittest.main()
