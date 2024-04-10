from pathlib import Path
import api_keys
import argparse
import logging
from csv import DictReader
from data_evaluator import (
    any_record_has_clu,
    get_all_publisher_numbers,
    get_best_worldcat_record,
    get_discogs_records,
    get_marc_problems,
    get_musicbrainz_records,
    get_oclc_number,
    get_unique_titles,
    get_usable_worldcat_records,
)
from create_marc_record import (
    add_local_fields,
    create_discogs_record,
    create_musicbrainz_record,
    write_marc_record,
)
from searchers.discogs import DiscogsClient
from searchers.musicbrainz import MusicbrainzClient
from searchers.worldcat import WorldcatClient
from time import sleep

logger = logging.getLogger()


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
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    args = parser.parse_args()

    input_filename = args.music_data_file
    logging_filename = get_logging_filename(input_filename)
    logging.basicConfig(filename=logging_filename, level=args.log_level)
    # Suppress 3rd-party logs with lower level than WARNING
    logging.getLogger("musicbrainzngs").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Get the set of data provided by Music library to use for this process.
    music_data = get_dicts_from_tsv(input_filename)

    # Get the names of the files where MARC records will be written.
    worldcat_record_filename = get_marc_filename(input_filename, "oclc")
    original_record_filename = get_marc_filename(input_filename, "orig")

    # Initialize the clients used for searching various data sources.
    worldcat_client, discogs_client, musicbrainz_client = get_clients()

    for idx, row in enumerate(
        music_data[args.start_index : args.end_index], start=args.start_index
    ):
        logger.info(f"Starting row {idx}")
        upc_code, call_number, barcode, official_title = get_next_data_row(row)
        logger.info(f"{call_number}: Searching for {upc_code} ({official_title})")

        # First, search Discogs and MusicBrainz for the given term.
        # Among other data, collect music publisher number(s) from those sources.
        discogs_records = get_discogs_records(discogs_client, search_term=upc_code)
        logger.info(f"\tFound {len(discogs_records)} Discogs records")
        musicbrainz_records = get_musicbrainz_records(
            musicbrainz_client, search_term=upc_code
        )
        logger.info(f"\tFound {len(musicbrainz_records)} MusicBrainz records")

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
            logger.info(
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
            # Detailed message was logged in routine; add broader info here.
            logger.info(
                f"\tPull CD for review [held by CLU]: {call_number} ({official_title})"
            )
            logger.info(f"Finished row {idx}\n")
            continue

        # Select the best available Worldcat record.
        worldcat_record = get_best_worldcat_record(usable_records)

        # Update (or create) final MARC record where possible.
        # If there's a Worldcat record, use it;
        # otherwise, prefer Discogs data over MusicBrainz.
        if worldcat_record:
            logger.info(f"\tWinner: OCLC# {get_oclc_number(worldcat_record)}")
            # Report on problems with this Worldcat record, if any;
            # these may require cataloger review, but we'll still use the record.
            marc_problems = get_marc_problems(worldcat_record)
            for problem in marc_problems:
                logger.info(f"\t\tREVIEW: {problem}")

            marc_record = worldcat_record
            marc_filename = worldcat_record_filename
        elif discogs_records:
            marc_record = create_discogs_record(data=discogs_records[0])
            marc_filename = original_record_filename
            logger.info(
                f"\tPull CD for review [original record created]: {call_number} ({official_title})"
            )
        elif musicbrainz_records:
            marc_record = create_musicbrainz_record(data=musicbrainz_records[0])
            marc_filename = original_record_filename
            logger.info(
                f"\tPull CD for review [original record created]: {call_number} ({official_title})"
            )

        # Finally, add local fields and write the record to file, or log a message.
        if marc_record:
            marc_record = add_local_fields(marc_record, barcode, call_number)
            write_marc_record(marc_record, filename=marc_filename)
        else:
            # No suitable data at all.
            logger.info("MARC not created: no data available")
            logger.info(
                f"\tPull CD for review [no record created]: {call_number} ({official_title})"
            )

        # End of this row of data.
        logger.info(f"Finished row {idx}\n")

        # Some APIs have rate limits.
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


def get_marc_filename(input_filename: str, file_type: str) -> str:
    """Get the name of the file where MARC records of the given type
    will be written, based on the input filename.
    """
    base = Path(input_filename).stem
    return f"{base}_{file_type}.mrc"


def get_logging_filename(input_filename: str) -> str:
    """Get the name of the logfile to be used, based on the input filename."""
    base = Path(input_filename).stem
    return f"{base}.log"


if __name__ == "__main__":
    main()
