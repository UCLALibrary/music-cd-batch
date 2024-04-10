import musicbrainzngs


class MusicbrainzClient:
    """Provide a wrapper around specific functionality for musicbrainzngs
    (https://pypi.org/project/python3-discogs-client/) to support
    UCLA's batch music CD cataloging project.
    """

    def __init__(self) -> None:
        # Client will be set on first use.
        self._client = None

    @property
    def client(self) -> musicbrainzngs:
        """Return configured client ready for use, on demand."""
        if self._client is None:
            # musicbrainzngs has no explicit "client" attribute like Discogs & Worldcat;
            # create one to make our custom classes similar.
            self._client = musicbrainzngs
            self._client.set_useragent(
                app="music-cd-batch",
                version="0.1",
                contact="https://github.com/UCLALibrary/music-cd-batch/",
            )
        return self._client

    def search_by_upc(self, upc: str) -> list:
        """Search MusicBrainz for releases by UPC. Returns a list of release dictionaries.
        To match both CDs and UPCs precisely, use strict=True
        MusicBrainz calls UPCs "barcode"s.
        """
        result = self.client.search_releases(barcode=upc, format="CD", strict=True)
        return result["release-list"]

    def parse_data(self, data: list) -> list:
        """Parse MusicBrainz list of releases to pull out data for future use.
        Each dictionary contains title, artist, publisher_number (if available),
        and full_json of the original response.
        """
        output_dict_list = []
        for release in data:
            release_dict = {
                "title": release["title"],
                "artist": release["artist-credit-phrase"],
                "full_json": release,
            }
            # Some releases have no label-info-list.
            if "label-info-list" in release:
                release_dict["publisher_number"] = self.get_first_catalog_number(
                    release["label-info-list"]
                )
            output_dict_list.append(release_dict)
        return output_dict_list

    def get_first_catalog_number(self, label_info_list: list) -> str:
        """Return first catalog number found. This is not always in
        the first element of label_info_list."""
        catalog_numbers = [
            label.get("catalog-number")
            for label in label_info_list
            if label.get("catalog-number") is not None
        ]
        if catalog_numbers:
            return catalog_numbers[0]
        else:
            return ""
