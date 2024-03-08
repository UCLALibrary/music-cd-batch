import musicbrainzngs


musicbrainzngs.set_useragent(
    "music-cd-batch",
    "0.1",
    "https://github.com/UCLALibrary/music-cd-batch/",
)


def search_musicbrainz_by_upc(upc: str) -> dict:
    """Search MusicBrainz for releases by UPC. Returns a list of release dictionaries.
    Each dictionary contains title, artist, publisher_number, and full_json."""
    # MusicBrainz calls UPCs "barcodes"s
    # To match both CDs and UPCs precisely, use strict=True
    result = musicbrainzngs.search_releases(barcode=upc, format="CD", strict=True)
    output_dict_list = []
    for release in result["release-list"]:
        release_dict = {
            "title": release["title"],
            "artist": release["artist-credit-phrase"],
            "publisher_number": release["label-info-list"][0]["catalog-number"],
            "full_json": release,
        }
        output_dict_list.append(release_dict)
    return output_dict_list
