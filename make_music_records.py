import argparse
from csv import DictReader

from pymarc import Record

from searchers.discogs import DiscogsClient
from searchers.musicbrainz import MusicbrainzClient
from searchers.worldcat import WorldcatClient
import api_keys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("music_data_file", help="Path to the TSV file of music data")
    args = parser.parse_args()
    music_data = get_dicts_from_tsv(args.music_data_file)

    # TODO: Remove range, used to test small subset of batch_016_20240229.tsv
    for row in music_data[6:10]:
        upc_code = row["UPC"]
        official_title = row["title"]
        print(f"Searching for {upc_code} ({official_title})")
        marc_records = get_worldcat_records(search_term=upc_code, search_index="sn")
        print(f"\tFound {len(marc_records)} Worldcat records")
        discogs_records = get_discogs_records(upc_code)
        print(f"\tFound {len(discogs_records)} Discogs records")
        musicbrainz_records = get_musicbrainz_records(upc_code)
        print(f"\tFound {len(musicbrainz_records)} MusicBrainz records")


def get_dicts_from_tsv(filepath=str) -> list:
    with open(filepath, mode="r") as f:
        dict_reader = DictReader(f, delimiter="\t")
        full_dicts = list(dict_reader)
    return full_dicts


def get_worldcat_records(search_term: str, search_index: str) -> list[Record]:
    worldcat_client = WorldcatClient(
        api_keys.WORLDCAT_METADATA_CLIENT_ID,
        api_keys.WORLDCAT_METADATA_CLIENT_SECRET,
        api_keys.WORLDCAT_PRINCIPAL_ID,
        api_keys.WORLDCAT_PRINCIPAL_IDNS,
    )
    search_results = worldcat_client.search(search_term, search_index)
    oclc_numbers = worldcat_client.get_oclc_numbers(search_results)
    # TEMPORARY
    for oclc_number in oclc_numbers:
        held_by_clu = worldcat_client.is_held_by(oclc_number)
        print(f"\t{oclc_number} held by CLU: {held_by_clu}")
    marc_records = worldcat_client.get_records(oclc_numbers)
    return marc_records


def get_discogs_records(search_term: str) -> list:
    discogs_client = DiscogsClient(api_keys.DISCOGS_USER_TOKEN)
    search_results = discogs_client.get_ids_by_upc(search_term)
    releases = discogs_client.get_full_releases(search_results)
    data = discogs_client.parse_data(releases)
    return data


def get_musicbrainz_records(search_term: str) -> list:
    musicbrainz_client = MusicbrainzClient()
    search_results = musicbrainz_client.search_by_upc(search_term)
    data = musicbrainz_client.parse_data(search_results)
    return data


if __name__ == "__main__":
    main()
