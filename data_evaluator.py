"""A collection of routines to evaluate data from several sources
and determine which to use for generating MARC records.
"""

import logging
import string
from strsimpy import NormalizedLevenshtein
from pymarc import Record
from searchers.discogs import DiscogsClient
from searchers.musicbrainz import MusicbrainzClient
from searchers.worldcat import WorldcatClient

logger = logging.getLogger()


def get_usable_worldcat_records(
    client: WorldcatClient,
    search_terms: str | list,
    search_index: str,
    unique_titles: set,
) -> list[Record]:
    """Convenience method which calls other methods to search Worldcat
    and evaluate those records. This gets called multiple times with
    different parameters.
    Returns a list of MARC records.
    """
    marc_records = get_worldcat_records(client, search_terms, search_index)
    usable_records = get_usable_records(marc_records, unique_titles)
    return usable_records


def get_worldcat_records(
    client: WorldcatClient, search_terms: str | list, search_index: str
) -> list[Record]:
    """Search Worldcat, returning a list of MARC records matching the search term(s)."""
    # Convert single search string into a 1-long list, for consistency
    if isinstance(search_terms, str):
        search_terms = [search_terms]
    all_records = []
    for search_term in search_terms:
        search_results = client.search(search_term, search_index)
        oclc_numbers = client.get_oclc_numbers(search_results)
        marc_records = client.get_records(oclc_numbers)
        all_records.extend(marc_records)
    logger.info(f"\tFound {len(all_records)} Worldcat records")
    return all_records


def get_discogs_records(client: DiscogsClient, search_term: str) -> list:
    """Search Discogs, returning a list of data matching the search term."""
    search_results = client.get_ids_by_upc(search_term)
    releases = client.get_full_releases(search_results)
    data = client.parse_data(releases)
    return data


def get_musicbrainz_records(client: MusicbrainzClient, search_term: str) -> list:
    """Search MusicBrainz, returning a list of data matching the search term."""
    search_results = client.search_by_upc(search_term)
    data = client.parse_data(search_results)
    return data


def any_record_has_clu(client: WorldcatClient, records: list[Record]) -> bool:
    """Check a list of MARC records against Worldcat to determine
    whether any is held by CLU (UCLA).
    """
    for record in records:
        oclc_number = get_oclc_number(record)
        if client.is_held_by_us(oclc_number):
            logger.info(f"\tREJECTING ALL RECORDS: OCLC {oclc_number} is held by CLU")
            logger.info(f"\tWorldcat Title -> {record.title}")
            return True
    # If we made it to here, no records are held by CLU.
    return False


def get_usable_records(records: list[Record], unique_titles: set) -> list[Record]:
    """Given a list of MARC records and a set of title strings,
    return a list containing only those records which have sufficient quality
    and a title similar enough to those from all sources."""
    records_to_keep = []
    for record in records:
        # For debugging
        oclc_number = get_oclc_number(record)
        logger.info(f"\t\tChecking OCLC# {oclc_number} -> {record.title}")
        if record_is_usable(record) and title_is_close_enough(record, unique_titles):
            records_to_keep.append(record)

    logger.info(f"\tFound {len(records_to_keep)} usable Worldcat records")
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
    titles = set()
    titles.add(official_title)
    discogs_titles = [record["title"] for record in discogs_records]
    musicbrainz_titles = [record["title"] for record in musicbrainz_records]
    titles.update(discogs_titles)
    titles.update(musicbrainz_titles)
    return titles


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
        logger.info(f"\t\t{score:.2f}: {full_title=} -> {title=}")
        # This threshold was used in previous phase.
        if score < 0.4:
            # Full title might not match, but primary (245 $a) title might.
            short_title = get_marc_short_title(record)
            if short_title != full_title:
                score = get_title_similarity_score(short_title, title)
                logger.info(f"\t\t{score:.2f}: {short_title=} -> {title=}")
                # Still too different?
                if score < 0.4:
                    logger.info(f"\tWarning: Titles are too different: {score:.2f}")
                    logger.info(f"\t\tMARC Title : {full_title} ({oclc_number})")
                    logger.info(f"\t\tOther Title: {title}")
        total_score += score
    if len(titles) > 0:
        average_score = total_score / len(titles)
    else:
        # No titles, no comparison, no reason to reject
        average_score = 1.0
    # This threshold was used in previous phase.
    if average_score < 0.37:
        logger.info(
            f"\t\tREJECTED OCLC {oclc_number}: Titles are too different: {average_score:.2f}"
        )
        return False
    else:
        # Titles are close enough
        logger.info(f"\tAVERAGE SCORE: {average_score:.2f}")
        return True


def get_title_similarity_score(title_1: str, title_2: str) -> float:
    """Return similarity score for two titles.
    Similarity score ranges from 0.0 (completely different) to 1.0 (identical).
    """
    comparator = NormalizedLevenshtein()
    return comparator.similarity(normalize(title_1), normalize(title_2))


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
        logger.info(f"\tREJECTED OCLC {oclc_number}: bad record type '{record_type}'")
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
        logger.info(
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
            logger.info(
                f"\tREJECTED OCLC {oclc_number}: cataloging language '{cat_lang}'"
            )
            is_ok = False
    else:
        logger.info(
            f"\tREJECTED OCLC {oclc_number}: no 040 field to check cataloging language"
        )
        is_ok = False
    return is_ok


def get_best_worldcat_record(records: list[Record]) -> Record | None:
    """Given a list of MARC records, compare them on various criteria
    and return the 'best' one according to those criteria.
    """
    # If records is empty, return None.
    if not records:
        return None
    # If only one record, it's the best! - return it.
    if len(records) == 1:
        return records[0]
    # More than one record:
    # Start with the first, iterate over the other records and compare:
    # Winner of [0,1] meets record 2; winner of that meets 3, etc.
    best_record = records[0]
    for challenger in records[1:]:
        best_record = compare_records(best_record, challenger)
    return best_record


def compare_records(record1: Record, record2: Record) -> Record:
    """Compare attributes of 2 records and return the 'best' one."""
    # First, compare encoding levels; best wins 5 points.
    record1_elvl_score = get_encoding_level_score(record1)
    record2_elvl_score = get_encoding_level_score(record2)
    # In the past, we used the number of Worldcat holdings to break ties
    # between records with the same encoding levels.
    # The bookops package, and Worldcat Metadata API in general, don't support
    # getting number of holdings - only the Search API does that.
    # Confirmed we can live without this tiebreaker.

    # For now, return the record with the best encoding level score;
    # if record1 and record2 tie on this, return record1.
    if record1_elvl_score >= record2_elvl_score:
        logger.debug(
            (
                f"\t\t{get_oclc_number(record1)} ({record1_elvl_score}) beats "
                f"{get_oclc_number(record2)} ({record2_elvl_score})"
            )
        )
        return record1
    else:
        logger.debug(
            (
                f"\t\t{get_oclc_number(record2)} ({record1_elvl_score}) beats "
                f"{get_oclc_number(record1)} ({record1_elvl_score})"
            )
        )
        return record2


def get_encoding_level_score(record: Record) -> int:
    """Return a numerical score to represent the quality of a MARC record's
    encoding level (LDR/17).
    """
    # First, compare encoding levels: (best to worst): Blank, 4, I, 1, 7, K, M, L, 3
    # Convert blank to '#' for readability.
    encoding_level = record.leader[17].replace(" ", "#")
    # str.find() returns an integer position if found, or -1 if not.
    elvl_values = "3LMK71I4#"
    return elvl_values.find(encoding_level)


def get_marc_problems(record: Record) -> list[str]:
    """Capture problems with MARC record we're keeping,
    for later review / cleanup.

    Returns a list of messages for use by caller.
    """
    messages = []
    # Check for specific individual fields first, reporting on each.
    for tag in ["007", "300", "650"]:
        if not record.get_fields(tag):
            messages.append(f"No {tag} field")

    # Check for groups of related field, reporting on each group.
    for tag_group in ["100/110/700/710", "260/264", "500/505/511/518"]:
        tags = tag_group.split("/")
        # get_fields() needs list of tags unpacked into positional args.
        if not record.get_fields(*tags):
            messages.append(f"No {tag_group} fields")

    # Check for 490 $v, meaning it's probably a multi-CD set.
    flds_490 = record.get_fields("490")
    for fld in flds_490:
        sfd_490v = fld.get_subfields("v")
        if sfd_490v:
            messages.append(f"490 $v found: {sfd_490v}")

    return messages
