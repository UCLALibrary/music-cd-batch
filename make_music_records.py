import api_keys
import argparse
from csv import DictReader
from data_evaluator import (
    any_record_has_clu,
    get_all_publisher_numbers,
    get_best_worldcat_record,
    get_discogs_records,
    get_musicbrainz_records,
    get_oclc_number,
    get_unique_titles,
    get_usable_worldcat_records,
)
from searchers.discogs import DiscogsClient
from searchers.musicbrainz import MusicbrainzClient
from searchers.worldcat import WorldcatClient
from time import sleep


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("music_data_file", help="Path to the TSV file of music data")
    parser.add_argument(
        "-s",
        "--start-index",
        type=int,
        default=0,
        help="Starting row of data to process (0-based)",
    )
    parser.add_argument(
        "-e",
        "--end-index",
        type=int,
        help="Ending row of data to process (0-based)",
    )
    args = parser.parse_args()

    # Get the set of data provided by Music library to use for this process.
    music_data = get_dicts_from_tsv(args.music_data_file)

    # Initialize the clients used for searching various data sources.
    worldcat_client, discogs_client, musicbrainz_client = get_clients()

    for idx, row in enumerate(
        music_data[args.start_index : args.end_index], start=args.start_index
    ):
        print(f"Starting row {idx}")
        upc_code, call_number, barcode, official_title = get_next_data_row(row)
        print(f"{call_number}: Searching for {upc_code} ({official_title})")

        # First, search Discogs and MusicBrainz for the given term.
        # Among other data, collect music publisher number(s) from those sources.
        discogs_records = get_discogs_records(discogs_client, search_term=upc_code)
        print(f"\tFound {len(discogs_records)} Discogs records")
        musicbrainz_records = get_musicbrainz_records(
            musicbrainz_client, search_term=upc_code
        )
        print(f"\tFound {len(musicbrainz_records)} MusicBrainz records")

        unique_titles = get_unique_titles(
            discogs_records=discogs_records,
            musicbrainz_records=musicbrainz_records,
            official_title=official_title,
        )

        usable_records = get_usable_worldcat_records(
            worldcat_client,
            search_terms=upc_code,
            search_index="sn",
            unique_titles=unique_titles,
        )

        if not usable_records:
            # If initial search on UPC didn't find anything, try searching for
            # the music publisher numbers from Discogs/MusicBrainz.
            publisher_numbers = get_all_publisher_numbers(
                discogs_records, musicbrainz_records
            )
            print(
                f"\tSearching Worldcat again for music publisher numbers: {publisher_numbers}"
            )
            usable_records = get_usable_worldcat_records(
                worldcat_client,
                search_terms=publisher_numbers,
                search_index="mn",
                unique_titles=unique_titles,
            )

        # If ANY WorldCat record we found is held by CLU, reject the whole set
        # and exit this iteration: we don't want to add any dup, from any source.
        if any_record_has_clu(worldcat_client, usable_records):
            # Detailed message was printed in routine; add broader info here.
            print(
                f"\tPull CD for review [held by CLU]: {call_number} ({official_title})"
            )
            print(f"Finished row {idx}\n")
            continue

        marc_record = get_best_worldcat_record(usable_records)
        if marc_record:
            print(f"\tWinner: OCLC# {get_oclc_number(marc_record)}")
            # TODO: Enhance marc_record with local fields
        else:
            # TODO: Create minimal MARC record from Discogs/Musicbrainz data
            pass

        print(f"Finished row {idx}\n")

        # Some APIs have rate limits
        sleep(1)


def get_dicts_from_tsv(filepath: str) -> list:
    """Read tab-separated values file, with column names in first row.
    Return a list of dicts keyed on those column names, one dict for
    each row of data.
    """
    with open(filepath, mode="r") as f:
        dict_reader = DictReader(f, delimiter="\t")
        full_dicts = list(dict_reader)
    return full_dicts


def get_clients() -> tuple[WorldcatClient, DiscogsClient, MusicbrainzClient]:
    """Convenience method to initialize and return all needed clients
    for searching the required data sources.
    """
    worldcat_client = WorldcatClient(
        api_keys.WORLDCAT_METADATA_CLIENT_ID,
        api_keys.WORLDCAT_METADATA_CLIENT_SECRET,
    )
    discogs_client = DiscogsClient(api_keys.DISCOGS_USER_TOKEN)
    musicbrainz_client = MusicbrainzClient()
    return worldcat_client, discogs_client, musicbrainz_client


def get_next_data_row(row: dict) -> tuple[str, str, str, str]:
    """Clean up source data for consistency.
    Return as individual values instead of dict.
    """
    upc_code = row["UPC"].strip()
    call_number = row["call number"].strip()
    # Barcodes should always be uppercase.
    barcode = row["barcode"].strip().upper()
    official_title = row["title"].strip()
    return upc_code, call_number, barcode, official_title


if __name__ == "__main__":
    main()
