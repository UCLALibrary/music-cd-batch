from search_discogs import parse_discogs_data
from unittest import mock, TestCase


class TestSearchDiscogs(TestCase):

    def test_parse_discogs_data_one_result(self):
        mock_release_data = mock.MagicMock()
        # artist is a list of artist objects
        mock_release_artists = mock.MagicMock()
        mock_release_artists.name = "Artist Name"
        mock_release_data.artists = [mock_release_artists]
        # labels is a list of label objects
        mock_release_labels = mock.MagicMock()
        mock_release_labels.catno = "123456789-0"
        mock_release_data.labels = [mock_release_labels]
        # title is a string
        mock_release_data.title = "Release Title"
        # small fake JSON data instead of full response
        mock_release_data.data = {"key": "value"}

        result = parse_discogs_data([mock_release_data])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Release Title")
        self.assertEqual(result[0]["artist"], "Artist Name")
        self.assertEqual(result[0]["publisher_number"], "123456789-0")
        self.assertEqual(result[0]["full_json"], {"key": "value"})

    def test_parse_discogs_data_no_result(self):
        # get_full_discogs_releases returns an empty list if no results
        result = parse_discogs_data([])
        self.assertEqual(result, [])

    def test_parse_discogs_data_multiple_results(self):
        mock_release_1 = mock.MagicMock()
        mock_release_1.title = "Title 1"
        mock_release_1_artists = mock.MagicMock()
        mock_release_1_artists.name = "Artist 1"
        mock_release_1.artists = [mock_release_1_artists]
        mock_release_1_labels = mock.MagicMock()
        mock_release_1_labels.catno = "11111 1"
        mock_release_1.labels = [mock_release_1_labels]
        mock_release_1.data = {"key1": "value1"}

        mock_release_2 = mock.MagicMock()
        mock_release_2.title = "Title 2"
        mock_release_2_artists = mock.MagicMock()
        mock_release_2_artists.name = "Artist 2"
        mock_release_2.artists = [mock_release_2_artists]
        mock_release_2_labels = mock.MagicMock()
        mock_release_2_labels.catno = "22222 2"
        mock_release_2.labels = [mock_release_2_labels]
        mock_release_2.data = {"key2": "value2"}

        result = parse_discogs_data([mock_release_1, mock_release_2])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "Title 1")
        self.assertEqual(result[0]["artist"], "Artist 1")
        self.assertEqual(result[0]["publisher_number"], "11111 1")
        self.assertEqual(result[0]["full_json"], {"key1": "value1"})
        self.assertEqual(result[1]["title"], "Title 2")
        self.assertEqual(result[1]["artist"], "Artist 2")
        self.assertEqual(result[1]["publisher_number"], "22222 2")
        self.assertEqual(result[1]["full_json"], {"key2": "value2"})
