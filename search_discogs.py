import discogs_client
from api_keys import DISCOGS_USER_TOKEN


def get_discogs_ids_by_upc(upc: str) -> list:
    """Search Discogs for releases by UPC. Returns a list of IDs to use to get full release data."""
    user_token = DISCOGS_USER_TOKEN
    discogs = discogs_client.Client(
        "music-cd-batch/0.1 +https://github.com/UCLALibrary/music-cd-batch",
        user_token=user_token,
    )
    search_results = discogs.search(upc, type="release", format="CD")
    release_ids = [result.id for result in search_results]
    return release_ids


def get_full_discogs_releases(release_ids: list) -> list:
    """Get full release data from Discogs by release ID."""
    output_list = []
    user_token = DISCOGS_USER_TOKEN
    discogs = discogs_client.Client(
        "music-cd-batch/0.1 +https://github.com/UCLALibrary/music-cd-batch",
        user_token=user_token,
    )
    for release_id in release_ids:
        release = discogs.release(release_id)
        output_list.append(release)
    return output_list


def parse_discogs_data(release_list: list) -> list:
    """Parse Discogs list of releases to pull out data for future use.
    Each dictionary contains title, artist, publisher_number, and full_json of the
    original response.
    """
    output_dict_list = []
    for release in release_list:
        title = release.title
        publisher_number = release.labels[0].catno
        artist = " , ".join([artist.name for artist in release.artists])

        release_dict = {
            "title": title,
            "artist": artist,
            "publisher_number": publisher_number,
            "full_json": release.data,
        }

        output_dict_list.append(release_dict)
    return output_dict_list
