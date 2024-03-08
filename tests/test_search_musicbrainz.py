from search_musicbrainz import parse_musicbrainz_data
import json
import unittest


class TestSearchMusicbrainz(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load sample data for use by all tests
        with open("tests/sample_data/musicbrainz_samples.data") as f:
            cls.data = json.load(f)

    def test_parse_musicbrainz_data_one_result(self):
        result = parse_musicbrainz_data(self.data["018777260022"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Lincoln")
        self.assertEqual(result[0]["artist"], "They Might Be Giants")
        self.assertEqual(result[0]["publisher_number"], "7 72600-2")

    def test_parse_musicbrainz_data_no_result(self):
        result = parse_musicbrainz_data(self.data["ZZZZZZZZZZZZZ"])
        self.assertEqual(len(result), 0)

    def test_parse_musicbrainz_data_split_release(self):
        result = parse_musicbrainz_data(self.data["020282009621"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "BYO Split Series, Volume V")
        # split release has two artists, and artist credit phrase is a concatenation of both
        self.assertEqual(result[0]["artist"], "Alkaline Trio / One Man Army")
        self.assertEqual(result[0]["publisher_number"], "BYO 096")

    def test_parse_musicbrainz_data_multiple_results(self):
        result = parse_musicbrainz_data(self.data["075596090728"])
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0]["title"], "Flood")
        self.assertEqual(result[0]["artist"], "They Might Be Giants")
        self.assertEqual(result[0]["publisher_number"], "7559-60907-2")
        self.assertEqual(result[4]["title"], "Flood")
        self.assertEqual(result[4]["artist"], "They Might Be Giants")
        self.assertEqual(result[4]["publisher_number"], "E2 60907")
