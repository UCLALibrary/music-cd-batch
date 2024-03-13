import argparse
from csv import DictReader
from pymarc import Record
from api_keys import (
    WORLDCAT_METADATA_CLIENT_ID,
    WORLDCAT_METADATA_CLIENT_SECRET,
    WORLDCAT_PRINCIPAL_ID,
    WORLDCAT_PRINCIPAL_IDNS,
)
from searchers.worldcat import WorldcatClient

# from pprint import pprint


def get_dicts_from_tsv(filepath=str) -> list:
    with open(filepath, mode="r") as f:
        dict_reader = DictReader(f, delimiter="\t")
        full_dicts = list(dict_reader)
    return full_dicts


def get_worldcat_records(
    worldcat_client: WorldcatClient, search_term: str, search_index: str
) -> list[Record]:
    search_results = worldcat_client.search_worldcat(search_term, search_index)
    oclc_numbers = worldcat_client.get_oclc_numbers(search_results)
    # TEMPORARY
    for oclc_number in oclc_numbers:
        held_by_clu = worldcat_client.is_held_by(oclc_number)
        print(f"\t{oclc_number} held by CLU: {held_by_clu}")
    marc_records = worldcat_client.get_worldcat_records(oclc_numbers)
    return marc_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("music_data_file", help="Path to the TSV file of music data")
    args = parser.parse_args()
    music_data = get_dicts_from_tsv(args.music_data_file)

    worldcat_client = WorldcatClient(
        WORLDCAT_METADATA_CLIENT_ID,
        WORLDCAT_METADATA_CLIENT_SECRET,
        WORLDCAT_PRINCIPAL_ID,
        WORLDCAT_PRINCIPAL_IDNS,
    )

    # TEMPORARY
    print("TESTING TRUE: ", worldcat_client.is_held_by("28745774"))

    # TODO: Remove range, used to test small subset of batch_016_20240229.tsv
    for row in music_data[6:10]:
        upc_code = row["UPC"]
        official_title = row["title"]
        print(f"Searching for {upc_code} ({official_title})")
        # TODO: Error handling, probably best handled in main program
        marc_records = get_worldcat_records(
            worldcat_client=worldcat_client, search_term=upc_code, search_index="sn"
        )
        for record in marc_records:
            print(f"\t{record.title}")
        print("")


if __name__ == "__main__":
    main()
