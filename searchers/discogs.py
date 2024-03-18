from discogs_client import Client
from discogs_client.exceptions import HTTPError


class DiscogsClient:
    """Provide a wrapper around specific functionality for discogs_client
    (https://pypi.org/project/python3-discogs-client/) to support
    UCLA's batch music CD cataloging project.
    """

    def __init__(self, user_token: str) -> None:
        # user_token is required for many API requests.
        self._token = user_token
        # user_agent is defined locally, to identify our application.
        self._user_agent = (
            "music-cd-batch/0.1 +https://github.com/UCLALibrary/music-cd-batch"
        )
        # Client will be set on first use.
        self._client = None

    @property
    def client(self) -> Client:
        """Return configured Client ready for use, on demand."""
        if self._client is None:
            self._client = Client(user_agent=self._user_agent, user_token=self._token)
        return self._client

    def get_ids_by_upc(self, upc: str) -> list:
        """Search Discogs for releases by UPC.
        Returns a list of IDs to use to get full release data.
        """
        search_results = self.client.search(upc, type="release", format="CD")
        release_ids = [result.id for result in search_results]
        return release_ids

    def get_full_releases(self, release_ids: list) -> list:
        """Get full release data from Discogs by release ID."""
        output_list = []
        for release_id in release_ids:
            # Some release_id values return 404 "Release not found",
            # even though they were just "found" by search.
            # Example: release_id 8418329 from upc 4988006789890.
            try:
                release = self.client.release(release_id)
                # force the release to refresh to get full data
                release.refresh()
                output_list.append(release.data)
            except HTTPError:
                # We don't care...
                pass

        return output_list

    def parse_data(self, release_list: list) -> list:
        """Parse Discogs list of releases to pull out data for future use.
        Each dictionary contains title, artist, publisher_number, and full_json of the
        original response.
        """
        output_dict_list = []
        for release in release_list:
            title = release["title"]
            publisher_number = release["labels"][0]["catno"]
            artist = ", ".join([artist["name"] for artist in release["artists"]])

            release_dict = {
                "title": title,
                "artist": artist,
                "publisher_number": publisher_number,
                "full_json": release,
            }

            output_dict_list.append(release_dict)
        return output_dict_list
