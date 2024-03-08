import musicbrainzngs


musicbrainzngs.set_useragent(
    "music-cd-batch",
    "0.1",
    "https://github.com/UCLALibrary/music-cd-batch/",
)


def search_musicbrainz_by_upc(upc: str) -> list:
    """Search MusicBrainz for releases by UPC. Returns a list of release dictionaries.
    To match both CDs and UPCs precisely, use strict=True
    MusicBrainz calls UPCs "barcode"s.
    """
    result = musicbrainzngs.search_releases(barcode=upc, format="CD", strict=True)
    return result["release-list"]


def parse_musicbrainz_data(data: list) -> list:
    """Parse MusicBrainz list of releases to pull out data for future use.
    Each dictionary contains title, artist, publisher_number, and full_json of the
    original response.
    """
    output_dict_list = []
    for release in data:
        release_dict = {
            "title": release["title"],
            "artist": release["artist-credit-phrase"],
            "publisher_number": release["label-info-list"][0]["catalog-number"],
            "full_json": release,
        }
        output_dict_list.append(release_dict)
    return output_dict_list
