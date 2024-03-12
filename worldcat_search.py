import argparse
from csv import DictReader
from bookops_worldcat import WorldcatAccessToken, MetadataSession
from api_keys import (
    WORLDCAT_METADATA_CLIENT_ID,
    WORLDCAT_METADATA_CLIENT_SECRET,
    WORLDCAT_PRINCIPAL_ID,
    WORLDCAT_PRINCIPAL_IDNS,
)
from pprint import pprint


def get_dicts_from_tsv(filepath=str) -> list:
    with open(filepath, mode="r") as f:
        dict_reader = DictReader(f, delimiter="\t")
        full_dicts = list(dict_reader)
    return full_dicts


def get_worldcat_token() -> str:
    token = WorldcatAccessToken(
        key=WORLDCAT_METADATA_CLIENT_ID,
        secret=WORLDCAT_METADATA_CLIENT_SECRET,
        principal_id=WORLDCAT_PRINCIPAL_ID,
        principal_idns=WORLDCAT_PRINCIPAL_IDNS,
        scopes=["WorldCatMetadataAPI"],
    )
    return token


def search_worldcat(token: str, upc: str) -> dict:
    with MetadataSession(authorization=token) as session:
        results = session.search_brief_bibs(q=f"sn:{upc}")
        return results.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("music_data_file", help="Path to the TSV file of music data")
    args = parser.parse_args()
    music_data = get_dicts_from_tsv(args.music_data_file)

    token = get_worldcat_token()
    for row in music_data[0:10]:
        upc_code = row["UPC"]
        title = row["title"]
        worldcat_data = search_worldcat(token, upc_code)
        hits = worldcat_data.get("numberOfRecords")
        print(f"Searching for {upc_code} ({title})")
        print(f"\tHits: {hits}")
        if hits > 0:
            pprint(worldcat_data, width=132)


if __name__ == "__main__":
    main()
