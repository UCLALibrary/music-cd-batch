import argparse
import string
from csv import DictReader
from time import sleep
from jellyfish import jaro_winkler_similarity
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
    for idx, row in enumerate(music_data[40:43], start=1):
        print(f"Starting row {idx}")
        upc_code, call_number, barcode, official_title = get_next_data_row(row)
        print(f"{call_number}: Searching for {upc_code} ({official_title})")

        # First, search Discogs and MusicBrainz for the given term.
        # Among other data, collect music publisher number(s) from those sources.
        discogs_records = get_discogs_records(upc_code)
        print(f"\tFound {len(discogs_records)} Discogs records")
        musicbrainz_records = get_musicbrainz_records(upc_code)
        print(f"\tFound {len(musicbrainz_records)} MusicBrainz records")

        unique_titles = get_unique_titles(
            discogs_records=discogs_records,
            musicbrainz_records=musicbrainz_records,
            official_title=official_title,
        )

        marc_records = get_worldcat_records(search_terms=upc_code, search_index="sn")
        usable_records = get_usable_records(marc_records, unique_titles)

        if usable_records:
            # Do something with them
            pass
        else:
            publisher_numbers = get_all_publisher_numbers(
                discogs_records, musicbrainz_records
            )
            print(
                f"\tSearching Worldcat again for music publisher numbers: {publisher_numbers}"
            )
            # TODO: Refactor duplicate code
            marc_records = get_worldcat_records(
                search_terms=publisher_numbers, search_index="mn"
            )
            usable_records = get_usable_records(marc_records, unique_titles)
        print(f"Finished row {idx}\n")

        # Some APIs have rate limits
        sleep(1)


def get_dicts_from_tsv(filepath: str) -> list:
    with open(filepath, mode="r") as f:
        dict_reader = DictReader(f, delimiter="\t")
        full_dicts = list(dict_reader)
    return full_dicts


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


def get_worldcat_records(search_terms: str | list, search_index: str) -> list[Record]:
    worldcat_client = WorldcatClient(
        api_keys.WORLDCAT_METADATA_CLIENT_ID,
        api_keys.WORLDCAT_METADATA_CLIENT_SECRET,
        api_keys.WORLDCAT_PRINCIPAL_ID,
        api_keys.WORLDCAT_PRINCIPAL_IDNS,
    )
    if isinstance(search_terms, str):
        search_terms = [search_terms]
    all_records = []
    for search_term in search_terms:
        search_results = worldcat_client.search(search_term, search_index)
        oclc_numbers = worldcat_client.get_oclc_numbers(search_results)
        # TEMPORARY
        # for oclc_number in oclc_numbers:
        #     held_by_clu = worldcat_client.is_held_by(oclc_number)
        #     print(f"\t{oclc_number} held by CLU: {held_by_clu}")
        marc_records = worldcat_client.get_records(oclc_numbers)
        all_records.extend(marc_records)
    print(f"\tFound {len(all_records)} Worldcat records")
    return all_records


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


def get_usable_records(records: list[Record], unique_titles: set) -> list[Record]:
    """Given a list of MARC records and a set of title strings,
    return a list containing only those records which have sufficient quality
    and a title similar enough to those from all sources."""
    records_to_keep = []
    for record in records:
        # For debugging
        oclc_number = get_oclc_number(record)
        print(f"\t\tChecking: {oclc_number} : {record.title}")
        if record_is_usable(record) and title_is_close_enough(record, unique_titles):
            records_to_keep.append(record)

    print(f"\tFound {len(records_to_keep)} usable Worldcat records")
    return records_to_keep


def get_all_publisher_numbers(discogs_records: list, musicbrainz_records: list) -> set:
    """Return all music publisher numbers from the given lists, combined into
    a set for uniqueness.
    """
    all_pub_numbers = set()
    dc_pub_numbers = {normalize(r["publisher_number"]) for r in discogs_records}
    mb_pub_numbers = {normalize(r["publisher_number"]) for r in musicbrainz_records}
    all_pub_numbers.update(dc_pub_numbers)
    all_pub_numbers.update(mb_pub_numbers)
    return all_pub_numbers


def get_oclc_number(record: Record) -> str:
    """Return the OCLC number from the MARC record's 001 field, with
    alpha prefix removed.  Assumes the MARC record came from OCLC,
    which is safe for this project, so will always have an 001 with OCLC#.
    """
    oclc_number = record.get("001").data
    return "".join(d for d in oclc_number if d.isdigit())


def get_unique_titles(
    discogs_records: list, musicbrainz_records: list, official_title: str
) -> set:
    """Return a set with all unique titles from various sources."""
    titles = [official_title]
    discogs_titles = [record["title"] for record in discogs_records]
    musicbrainz_titles = [record["title"] for record in musicbrainz_records]
    titles.extend(discogs_titles)
    titles.extend(musicbrainz_titles)
    # Apply normalization and de-dup using a set.
    unique_titles = {normalize(title) for title in titles}
    return unique_titles


def strip_punctuation(input: str) -> str:
    """Remove all punctuation from a string."""
    return input.translate(str.maketrans("", "", string.punctuation))


def normalize_title(input: str) -> str:
    """Applies basic normalization to a string by stripping punctuation
    and using title case for readability.
    """
    return strip_punctuation(input.title())


def normalize(input: str) -> str:
    """Fully normalize a string for comparison with other strings.
    Strip punctuation, remove spaces, and force to upper case.
    """
    new_string = input.translate(str.maketrans("", "", string.whitespace))
    return strip_punctuation(new_string.upper())


def title_is_close_enough(record: Record, titles: set) -> bool:
    """Compare MARC title with Discogs/MusicBrainz/official title(s).
    Return true if too different, beyond threshhold.
    """
    # For logging problems
    oclc_number = get_oclc_number(record)
    # record.title is just 245 $a $b; we want 245 $a $n $p $b.
    full_title = get_marc_full_title(record)

    total_score: float = 0.0
    for title in titles:
        # Similarity score ranges from 0.0 (completely different) to 1.0 (identical).
        score = get_title_similarity_score(full_title, title)
        print(f"\t\t{score}: {full_title=} -> {title=}")
        # This threshold was used in previous phase.
        if score < 0.4:
            # Full title might not match, but primary (245 $a) title might.
            short_title = get_marc_short_title(record)
            if short_title != full_title:
                score = get_title_similarity_score(short_title, title)
                print(f"\t\t{score}: {short_title=} -> {title=}")
                # Still too different?
                if score < 0.4:
                    print(f"\tWarning: Titles are too different: {score:.2f}")
                    print(f"\t\tMARC Title : {full_title} ({oclc_number})")
                    print(f"\t\tOther Title: {title}")
        total_score += score
    if len(titles) > 0:
        average_score = total_score / len(titles)
    else:
        # No titles, no comparison, no reason to reject
        average_score = 1.0
    # This threshold was used in previous phase.
    if average_score < 0.37:
        print(
            f"\t\tREJECTED OCLC {oclc_number}: Titles are too different: {average_score:.2f}"
        )
        return False
    else:
        # Titles are close enough
        return True


def get_title_similarity_score(title_1: str, title_2: str) -> float:
    """Return similarity score for two titles.
    Similarity score ranges from 0.0 (completely different) to 1.0 (identical).
    """
    return jaro_winkler_similarity(normalize(title_1), normalize(title_2))


def get_marc_full_title(record: Record) -> str:
    """Return full (non-default) title from MARC record.
    Default record.title is just 245 $a $b; we want 245 $a $n $p $b.
    We can count on these records all having 245 fields.
    """
    fld_245 = record.get("245")
    # It's OK if some of these subfields don't exist.
    sfd_list = fld_245.get_subfields("a", "n", "p", "b")
    return " ".join(sfd_list)


def get_marc_short_title(record: Record) -> str:
    """Return short (non-default) title from MARC record.
    Default record.title is just 245 $a $b; we want 245 $a.
    We can count on these records all having 245 fields.
    """
    fld_245 = record.get("245")
    # It's OK if some of these subfields don't exist.
    sfd_list = fld_245.get_subfields("a")
    return " ".join(sfd_list)


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


if __name__ == "__main__":
    main()
