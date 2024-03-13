import argparse
from csv import DictReader

# from pymarc import Record
from api_keys import (
    WORLDCAT_METADATA_CLIENT_ID,
    WORLDCAT_METADATA_CLIENT_SECRET,
    WORLDCAT_PRINCIPAL_ID,
    WORLDCAT_PRINCIPAL_IDNS,
)
from searchers.worldcat import Worldcat

# from pprint import pprint


def get_dicts_from_tsv(filepath=str) -> list:
    with open(filepath, mode="r") as f:
        dict_reader = DictReader(f, delimiter="\t")
        full_dicts = list(dict_reader)
    return full_dicts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("music_data_file", help="Path to the TSV file of music data")
    args = parser.parse_args()
    music_data = get_dicts_from_tsv(args.music_data_file)

    worldcat_client = Worldcat(
        WORLDCAT_METADATA_CLIENT_ID,
        WORLDCAT_METADATA_CLIENT_SECRET,
        WORLDCAT_PRINCIPAL_ID,
        WORLDCAT_PRINCIPAL_IDNS,
    )

    # TODO: Remove range when done testing
    for row in music_data[0:10]:
        upc_code = row["UPC"]
        official_title = row["title"]
        oclc_numbers = worldcat_client.search_worldcat(upc_code, "sn")
        print(f"Searching for {upc_code} ({official_title})")
        print(oclc_numbers)
        marc_records = worldcat_client.get_worldcat_records(oclc_numbers)
        for record in marc_records:
            print(f"\t{record.title}")
        print("")


if __name__ == "__main__":
    main()
