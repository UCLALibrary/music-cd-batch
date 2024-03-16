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
    for row in music_data[6:8]:
        upc_code = row["UPC"]
        official_title = row["title"]
        print(f"Searching for {upc_code} ({official_title})")
        marc_records = get_worldcat_records(search_term=upc_code, search_index="sn")
        print(f"\tFound {len(marc_records)} Worldcat records")
        discogs_records = get_discogs_records(upc_code)
        print(f"\tFound {len(discogs_records)} Discogs records")
        musicbrainz_records = get_musicbrainz_records(upc_code)
        print(f"\tFound {len(musicbrainz_records)} MusicBrainz records")
        print("****")
        for record in marc_records:
            print("\t", record_is_usable(record))


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


def get_oclc_number(record: Record) -> str:
    """Return the OCLC number from the MARC record's 001 field, with
    alpha prefix removed.  Assumes the MARC record came from OCLC,
    which is safe for this project, so will always have an 001 with OCLC#.
    """
    oclc_number = record.get("001")
    return "".join(d for d in oclc_number if d.isdigit())


def record_is_usable(record: Record) -> bool:
    """Determine whether MARC record from Worldcat is usable for this project,
    by checking several characteristics. If any check fails, record is rejected."""
    return (
        record_type_is_ok(record)
        & form_of_item_is_ok(record)
        & cataloging_language_is_ok(record)
    )


def record_type_is_ok(record: Record) -> bool:
    # Reject records with LDR/06 (record type) other than 'i' or 'j'
    # (sound recordings).
    # https://www.loc.gov/marc/bibliographic/bdleader.html

    # Get OCLC number from 001, for logs.
    oclc_number = get_oclc_number(record)
    record_type = record.leader[6]
    if record_type not in "ij":
        print(f"\tREJECTED OCLC {oclc_number}: bad record type '{record_type}'")
        return False
    else:
        return True


def form_of_item_is_ok(record: Record) -> bool:
    # Reject records with 008/23 (form of item) = 'o' (Online).
    # https://www.loc.gov/marc/bibliographic/bd008m.html

    # Get OCLC number from 001, for logs.
    oclc_number = get_oclc_number(record)
    form_of_item = record.get("008").data[23]
    if form_of_item == "o":
        print(
            f"\tREJECTED OCLC {oclc_number}: bad 008/23 (form of item) '{form_of_item}'"
        )
        return False
    else:
        return True


def cataloging_language_is_ok(record: Record) -> bool:
    # Reject records with 040 $b (language of cataloging) other than 'eng'.
    # https://www.loc.gov/marc/bibliographic/bd040.html
    # 040 and $b are both non-repeatable, so safe to check just the first.

    is_ok = True
    # Get OCLC number from 001, for logs.
    oclc_number = get_oclc_number(record)

    f040 = record.get("040")
    if f040:
        cat_lang = f040.get("b")
        if cat_lang != "eng":
            print(f"\tREJECTED OCLC {oclc_number}: cataloging language '{cat_lang}'")
            is_ok = False
    else:
        print(
            f"\tREJECTED OCLC {oclc_number}: no 040 field to check cataloging language"
        )
        is_ok = False
    return is_ok


def remove_unsuitable_records():
    pass


if __name__ == "__main__":
    main()
