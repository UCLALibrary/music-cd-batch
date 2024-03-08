from search_musicbrainz import search_musicbrainz_by_upc
import unittest


class TestSearchMusicbrainz(unittest.TestCase):
    def test_search_musicbrainz_by_upc_one_result(self):
        result = search_musicbrainz_by_upc("018777260022")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Lincoln")
        self.assertEqual(result[0]["artist"], "They Might Be Giants")
        self.assertEqual(result[0]["publisher_number"], "7 72600-2")

    def test_search_musicbrainz_by_upc_no_result(self):
        result = search_musicbrainz_by_upc("ZZZZZZZZZZZZZ")
        self.assertEqual(len(result), 0)

    def test_search_musicbrainz_by_upc_split_release(self):
        result = search_musicbrainz_by_upc("020282009621")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "BYO Split Series, Volume V")
        # split release has two artists, and artist credit phrase is a concatenation of both
        self.assertEqual(result[0]["artist"], "Alkaline Trio / One Man Army")
        self.assertEqual(result[0]["publisher_number"], "BYO 096")

    def test_search_musicbrainz_by_upc_multiple_results(self):
        result = search_musicbrainz_by_upc("075596090728")
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0]["title"], "Flood")
        self.assertEqual(result[0]["artist"], "They Might Be Giants")
        self.assertEqual(result[0]["publisher_number"], "7559-60907-2")
        self.assertEqual(result[4]["title"], "Flood")
        self.assertEqual(result[4]["artist"], "They Might Be Giants")
        self.assertEqual(result[4]["publisher_number"], "E2 60907")
