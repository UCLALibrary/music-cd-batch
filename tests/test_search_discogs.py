from search_discogs import parse_discogs_data
import json
import unittest


class TestSearchDiscogs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Load sample data for use by all tests
        with open("tests/sample_data/discogs_samples.data") as f:
            cls.data = json.load(f)

    def test_parse_discogs_data_one_result(self):
        result = parse_discogs_data([self.data])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Lincoln")
        self.assertEqual(result[0]["artist"], "They Might Be Giants")
        self.assertEqual(result[0]["publisher_number"], "7 72600-2")
        self.assertEqual(result[0]["full_json"], self.data)

    def test_parse_discogs_data_no_result(self):
        # get_full_discogs_releases returns an empty list if no results
        result = parse_discogs_data([])
        self.assertEqual(result, [])
