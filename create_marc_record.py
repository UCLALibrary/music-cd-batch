from datetime import datetime
from pymarc import MARCWriter, Record, Field, Subfield


def create_base_record() -> Record:
    """Create a base MARC record, to which metadata from an external
    source will be added."""
    record = Record()

    # Leader fixed field.
    # Type (Leader/06) - j (Musical sound recording)
    record.leader.type_of_record = "j"
    # BLvl (Leader/07) - m (Monographic/Item)
    record.leader.bibliographic_level = "m"
    # Ctrl (Leader/08) - # (No specified type)
    record.leader.type_of_control = " "
    # ELvl (Leader/17) - 3 (Abbreviated level)
    record.leader.encoding_level = "3"
    # Desc (Leader/18) - i (ISBD punctuation included)
    record.leader.cataloging_form = "i"

    # 007 - physical description fixed field
    # 007 ## $a s $b d $d f $e u $f n $g g $h n $i n $m e $n u
    # translated to fixed field:
    record.add_field(Field(tag="007", data="sd fungnn|||eu"))

    # 008 - general information fixed field
    # DtSt (008/06) - s (Single known date/probable date)
    # Ctry (008/15-17) - xx# (No place, unknown, or undetermined)
    # Comp (008/18-19) - ##
    # FMus (008/20) - n (Not applicable)
    # Part (008/21) - n (Not applicable)
    # Audn (008/22) - # (Unknown or unspecified)
    # Form (008/23) - # (None of the following)
    # AccM (008/24-29) - # (No accompanying matter)
    # LTxt (008/30-31) - # (Item is a music sound recording)
    # TrAr (008/33) - n Not arrangement or transposition or not specified
    # MRec (008/38) - # (Not modified)
    # Srce (008/39) - d (Other)
    yymmdd = get_yymmdd()
    record.add_field(
        Field(tag="008", data=f"{yymmdd}s||||    xx ||nn           n ||| d")
    )

    # 040 ## $a CLU $b eng $c CLU
    # add_subfield method doesn't appear to work with newly created fields,
    # so we'll create the subfields first and use them to create the field
    subfields_040 = [
        Subfield("a", "CLU"),
        Subfield("b", "eng"),
        Subfield("c", "CLU"),
    ]
    field_040 = Field(tag="040", indicators=[" ", " "], subfields=subfields_040)
    record.add_field(field_040)

    # 336 ## $a performed music $b prm $2 rdacontent
    subfields_336 = [
        Subfield("a", "performed music"),
        Subfield("b", "prm"),
        Subfield("2", "rdacontent"),
    ]
    field_336 = Field(tag="336", indicators=[" ", " "], subfields=subfields_336)
    record.add_field(field_336)

    # 337 ## $a audio $b s $2 rdamedia
    subfields_337 = [
        Subfield("a", "audio"),
        Subfield("b", "s"),
        Subfield("2", "rdamedia"),
    ]
    field_337 = Field(tag="337", indicators=[" ", " "], subfields=subfields_337)
    record.add_field(field_337)

    # 338 ## $a audio disc $b sd $2 rdacarrier
    subfields_338 = [
        Subfield("a", "audio disc"),
        Subfield("b", "sd"),
        Subfield("2", "rdacarrier"),
    ]
    field_338 = Field(tag="338", indicators=[" ", " "], subfields=subfields_338)
    record.add_field(field_338)
    field_338 = Field(tag="338")

    # 340 ## $b 4 3/4 in.
    subfields_340 = [Subfield("b", "4 3/4 in.")]
    field_340 = Field(tag="340", indicators=[" ", " "], subfields=subfields_340)
    record.add_field(field_340)

    # 344 ## $a digital $2 rdatr
    subfields_344_1 = [Subfield("a", "digital"), Subfield("2", "rdatr")]
    field_344_1 = Field(tag="344", indicators=[" ", " "], subfields=subfields_344_1)
    record.add_field(field_344_1)

    # 344 ## $b optical $2 rdarm
    subfields_344_2 = [Subfield("b", "optical"), Subfield("2", "rdarm")]
    field_344_2 = Field(tag="344", indicators=[" ", " "], subfields=subfields_344_2)
    record.add_field(field_344_2)

    # 347 ## $a audio file $2 rdaft
    subfields_347_1 = [Subfield("a", "audio file"), Subfield("2", "rdaft")]
    field_347_1 = Field(tag="347", indicators=[" ", " "], subfields=subfields_347_1)
    record.add_field(field_347_1)

    # 347 ## $b CD audio
    subfields_347_2 = [Subfield("b", "CD audio")]
    field_347_2 = Field(tag="347", indicators=[" ", " "], subfields=subfields_347_2)
    record.add_field(field_347_2)

    return record


def add_local_fields(record: Record, barcode: str, call_number: str) -> Record:
    """Add local fields (0x9, 9xx) to a MARC record. These are added to all
    records, regardless of source.
    """

    # Records obtained via Worldcat Metadata API already have 049 $a CLUM... remove that.
    # This is safe if 049 does not exist.
    record.remove_fields("049")

    # 049 ## $a CLUV $l BARCODE
    subfields_049 = [Subfield("a", "CLUV"), Subfield("l", barcode)]
    field_049 = Field(tag="049", indicators=[" ", " "], subfields=subfields_049)
    record.add_ordered_field(field_049)

    # 099 ## $a CDA #
    subfields_099 = [Subfield("a", call_number)]
    field_099 = Field(tag="099", indicators=[" ", " "], subfields=subfields_099)
    record.add_ordered_field(field_099)

    # 962 ## $a cmc $b meherbatch $c YYYYMMDD $d 3 $k meherorig $9 LOCAL
    yyyymmdd = datetime.today().strftime("%Y%m%d")
    subfields_962 = [
        Subfield("a", "cmc"),
        Subfield("b", "meherbatch"),
        Subfield("c", yyyymmdd),
        Subfield("d", "3"),
        Subfield("k", "meherorig"),
        Subfield("9", "LOCAL"),
    ]
    field_962 = Field(tag="962", indicators=[" ", " "], subfields=subfields_962)
    record.add_ordered_field(field_962)

    # 966 ## $a MEHER $b Donovan Meher Collection $9 LOCAL
    subfields_966 = [
        Subfield("a", "MEHER"),
        Subfield("b", "Donovan Meher Collection"),
        Subfield("9", "LOCAL"),
    ]
    field_966 = Field(tag="966", indicators=[" ", " "], subfields=subfields_966)
    record.add_ordered_field(field_966)

    return record


def add_discogs_data(base_record: Record, data: dict) -> Record:
    """Add metadata from a Discogs release to a MARC record. Discogs data dict
    must be in the format returned by the DiscogsClient.parse_data method."""
    # Dates (008/07-10) - release year
    year = str(data["full_json"]["year"])  # make a string for later concatenation
    current_008 = base_record.get_fields("008")[0].data
    year_008 = current_008[:7] + year + current_008[11:]

    # Lang (008/35-37) - zxx
    new_008 = year_008[:35] + "zxx" + year_008[38:]
    base_record.remove_fields("008")
    base_record.add_ordered_field(Field(tag="008", data=new_008))

    # 024 8# $a IDENTIFIERS\VALUE (only for type: Barcode)
    # If no barcode element, do not include field.
    if data["full_json"]["identifiers"]:
        for identifier in data["full_json"]["identifiers"]:
            # include only barcode elements without description: Text.
            if (
                identifier.get("type") == "Barcode"
                and identifier.get("description") != "Text"
            ):
                # Normalize by removing spaces from value
                value = identifier["value"].replace(" ", "")
                subfields_024 = [Subfield("a", value)]
                field_024 = Field(
                    tag="024", indicators=["8", " "], subfields=subfields_024
                )
                base_record.add_ordered_field(field_024)

    # 028 02 $a LABELS\CATNO $b LABELS\NAME
    # If no labels\catno element, do not include field.
    if data["full_json"]["labels"]:
        for label in data["full_json"]["labels"]:
            # If there are multiple labels\catno elements, create multiple 028 fields.
            # If no labels\name element, do not include $b.
            if "name" not in label:
                subfields_028 = [Subfield("a", label["catno"])]
            else:
                subfields_028 = [
                    Subfield("a", label["catno"]),
                    Subfield("b", label["name"]),
                ]
            field_028 = Field(tag="028", indicators=["0", "2"], subfields=subfields_028)
            base_record.add_ordered_field(field_028)

    # 245 00 $a TITLE / $c ARTISTS\NAME
    title_245 = data["title"]
    # first artist only
    if "artist" in data:
        artist_245 = data["artist"]
        # format: $a Title <space> <slash> $c Artists\name <period>
        subfields_245 = [
            Subfield("a", title_245 + " /"),
            Subfield("c", artist_245 + "."),
        ]
    else:
        # format: $a Title <period>
        subfields_245 = [Subfield("a", title_245 + ".")]
    # if the first word of the title=”the” then 2nd indicator=4.
    # if the first word of the title=”a” then 2nd indicator=2.
    if title_245.lower().startswith("the "):
        field_245 = Field(tag="245", indicators=["0", "4"], subfields=subfields_245)
    elif title_245.lower().startswith("a "):
        field_245 = Field(tag="245", indicators=["0", "2"], subfields=subfields_245)
    elif title_245.lower().startswith("an "):
        field_245 = Field(tag="245", indicators=["0", "3"], subfields=subfields_245)
    else:
        field_245 = Field(tag="245", indicators=["0", "0"], subfields=subfields_245)
    base_record.add_ordered_field(field_245)

    # 264 #1 $a [Place of publication not identified] : $b LABELS\NAME, $c [RELEASED]
    # For DATE - 1st 4 digits only
    # If no label-info\label\name element, fill in $b with “[publisher not identified]”
    # If there are multiple label-info\label\name elements, take only the first instance.
    # If no date element, fill in $c with “[date of publication not identified]”

    date_264 = str(data["full_json"]["year"])  # make a string for later concatenation
    if data["full_json"]["labels"]:
        label = data["full_json"]["labels"][0]
        if "name" in label:
            publisher = label["name"]
        else:
            publisher = "[publisher not identified]"
    else:
        publisher = "[publisher not identified]"

    # format: [Place of publication not identified] <space> <colon>$b  LABELS\NAME <comma>
    # $c <open square bracket>RELEASED<closed square bracket>
    subfields_264 = [
        Subfield("a", "[Place of publication not identified] :"),
        Subfield("b", publisher + ","),
        Subfield("c", "[" + date_264 + "]"),
    ]
    field_264 = Field(tag="264", indicators=[" ", "1"], subfields=subfields_264)
    base_record.add_ordered_field(field_264)

    # 300 ## $a FORMATS\QTY audio disc : $b digital ; $c 4 3/4 in.
    # IF FORMATS\QTY>1, THEN $a FORMATS\QTY audio discs : $b digital ; $c 4 3/4 in.
    # If no formats\qty element, or if formats\qty=0, fill in with “1.”

    if data["full_json"]["formats"]:
        qty = data["full_json"]["formats"][0]["qty"]
    if not qty or qty == "0":
        qty = "1"
    if int(qty) > 1:
        qty_text = qty + " audio discs :"
    else:
        qty_text = qty + " audio disc :"

    # format: $a FORMATS\QTY audio disc <space> <colon> $b digital <space> <semicolon> $c 4 3/4 in.
    subfields_300 = [
        Subfield("a", qty_text),
        Subfield("b", "digital ;"),
        Subfield("c", "4 3/4 in."),
    ]
    field_300 = Field(tag="300", indicators=[" ", " "], subfields=subfields_300)
    base_record.add_ordered_field(field_300)

    # 500 ## $a Title from Discogs database.
    # same as 245 $a
    subfields_500 = [Subfield("a", title_245)]
    field_500 = Field(tag="500", indicators=[" ", " "], subfields=subfields_500)
    base_record.add_ordered_field(field_500)

    # 505 0# $a TRACKLIST\TITLE -- TRACKLIST\TITLE -- TRACKLIST\TITLE […].
    # If no tracklist element, do not include field.
    if data["full_json"]["tracklist"]:
        # Grab all track titles.
        track_titles = [track["title"] for track in data["full_json"]["tracklist"]]
        # Format into one string, separated by " -- ", ending with period.
        contents = " -- ".join(track_titles) + "."
        subfields_505 = [Subfield("a", contents)]
        field_505 = Field(tag="505", indicators=["0", " "], subfields=subfields_505)
        base_record.add_ordered_field(field_505)

    # 653 #6 $a GENRES
    # include all genres in $a subfields
    if data["full_json"]["genres"]:
        subfields_653 = []
        for genre in data["full_json"]["genres"]:
            subfields_653.append(Subfield("a", genre))
            field_653 = Field(tag="653", indicators=[" ", "6"], subfields=subfields_653)
        base_record.add_ordered_field(field_653)

    # 720 ## $a ARTISTS_SORT.
    # single string fields with possible multiple artists
    artist_720 = data["full_json"]["artists_sort"]
    # format: $a ARTISTS_SORT.
    subfields_720 = [Subfield("a", artist_720 + ".")]
    field_720 = Field(tag="720", indicators=[" ", " "], subfields=subfields_720)
    base_record.add_ordered_field(field_720)

    return base_record


def add_musicbrainz_data(base_record: Record, data: dict) -> Record:
    """Add metadata from a MusicBrainz release to a MARC record. MusicBrainz data dict
    must be in the format returned by the MusicBrainzClient.parse_data method"""

    # Dates (008/07-10) - DATE
    # If no date element, leave as is
    new_008 = base_record.get_fields("008")[0].data
    if data["full_json"]["date"]:
        date_008 = data["full_json"]["date"][0:4]
        current_008 = base_record.get_fields("008")[0].data
        new_008 = current_008[:7] + date_008 + current_008[11:]

    # Lang (008/35-37) - IF [text-representation\language]=eng, THEN eng
    # IF [text-representation\language]!=eng, THEN zxx
    if data["full_json"]["text-representation"]["language"] == "eng":
        new_008 = new_008[:35] + "eng" + new_008[38:]
    else:
        new_008 = new_008[:35] + "zxx" + new_008[38:]

    base_record.remove_fields("008")
    base_record.add_ordered_field(Field(tag="008", data=new_008))

    # 024 8# $a BARCODE
    # Normalize by removing spaces
    barcode = data["full_json"]["barcode"].replace(" ", "")
    subfields_024 = [Subfield("a", barcode)]
    field_024 = Field(tag="024", indicators=["8", " "], subfields=subfields_024)
    base_record.add_ordered_field(field_024)

    # 028 02 $a LABEL-INFO\CATALOG-NUMBER $b LABEL-INFO\LABEL\NAME
    # If no label-info\catalog-number element, do not include field.
    # If there are multiple label-info\catalog-number elements, create multiple 028 fields.
    for label_info in data["full_json"]["label-info-list"]:
        subfields_028 = []
        if label_info["catalog-number"]:
            subfields_028.append(Subfield("a", label_info["catalog-number"]))
            # If no label-info\label\name element, do not include $b.
            if label_info["label"]["name"]:
                subfields_028.append(Subfield("b", label_info["label"]["name"]))
        field_028 = Field(tag="028", indicators=["0", "2"], subfields=subfields_028)
        base_record.add_ordered_field(field_028)

    # 245 00 $a TITLE / $c ARTIST-CREDIT\ARTIST\NAME.
    title_245 = data["title"]
    # first artist only
    if "artist" in data:
        artist_245 = data["artist"]
        # $a Title <space> <slash> $c Artist-Credit\Artist\name <period>
        subfields_245 = [
            Subfield("a", title_245 + " /"),
            Subfield("c", artist_245 + "."),
        ]
    else:
        # $a Title <period>
        subfields_245 = [Subfield("a", title_245 + ".")]
    # if the first word of the title=”the” then 2nd indicator=4.
    # if the first word of the title=”a” then 2nd indicator=2.
    if title_245.lower().startswith("the "):
        field_245 = Field(tag="245", indicators=["0", "4"], subfields=subfields_245)
    elif title_245.lower().startswith("a "):
        field_245 = Field(tag="245", indicators=["0", "2"], subfields=subfields_245)
    elif title_245.lower().startswith("an "):
        field_245 = Field(tag="245", indicators=["0", "3"], subfields=subfields_245)
    else:
        field_245 = Field(tag="245", indicators=["0", "0"], subfields=subfields_245)
    base_record.add_ordered_field(field_245)

    # 264 #1 $a [Place of publication not identified] : $b LABEL-INFO\LABEL\NAME, $c [DATE]
    # For DATE - 1st 4 digits only
    # If no label-info\label\name element, fill in $b with “[publisher not identified]”
    # If there are multiple label-info\label\name elements, take only the first instance.
    # If no date element, fill in $c with “[date of publication not identified]”
    date_264 = data["full_json"]["date"][0:4]
    if data["full_json"]["label-info-list"]:
        label_info = data["full_json"]["label-info-list"][0]
        if label_info["label"]["name"]:
            publisher = label_info["label"]["name"]
        else:
            publisher = "[publisher not identified]"
    else:
        publisher = "[publisher not identified]"

    # format: [Place of publication not identified] <space> <colon>
    # $b  LABEL-INFO\LABEL\NAME <comma>
    # $c <open square bracket>DATE<close square bracket>
    subfields_264 = [
        Subfield("a", "[Place of publication not identified] :"),
        Subfield("b", publisher + ","),
        Subfield("c", "[" + date_264 + "]"),
    ]
    field_264 = Field(tag="264", indicators=[" ", "1"], subfields=subfields_264)
    base_record.add_ordered_field(field_264)

    # 300 ## $a MEDIA\DISC-COUNT audio disc : $b digital ; $c 4 3/4 in.
    # If no media\disc-count element, or if media\disc-count=0, fill in with “1.”
    if data["full_json"]["medium-count"]:
        qty = data["full_json"]["medium-count"]
    # this qty is an int
    if not qty or qty == 0:
        qty = 1
    if qty > 1:
        qty_text = str(qty) + " audio discs :"
    else:
        qty_text = "1 audio disc :"

    # format: $a MEDIA\DISC-COUNT audio disc <space> <colon>
    # $b digital <space> <semicolon> $c 4 3/4 in.
    subfields_300 = [
        Subfield("a", qty_text),
        Subfield("b", "digital ;"),
        Subfield("c", "4 3/4 in."),
    ]
    field_300 = Field(tag="300", indicators=[" ", " "], subfields=subfields_300)
    base_record.add_ordered_field(field_300)

    # 500 ## $a Title from MusicBrainz database.
    # same as 245 $a
    subfields_500 = [Subfield("a", title_245)]
    field_500 = Field(tag="500", indicators=[" ", " "], subfields=subfields_500)
    base_record.add_ordered_field(field_500)

    # 653 #6 $a TAGS\NAME
    # include all tags in $a subfields
    if data["full_json"]["tag-list"] != []:
        subfields_653 = []
        for tag in data["full_json"]["tag-list"]:
            subfields_653.append(Subfield("a", tag["name"]))
            field_653 = Field(tag="653", indicators=[" ", "6"], subfields=subfields_653)
        base_record.add_ordered_field(field_653)

    # 720 ## $a ARTIST\SORT-NAME.
    artist_720 = data["full_json"]["artist-credit"][0]["artist"]["sort-name"]
    # format: $a ARTIST\SORT-NAME.
    subfields_720 = [Subfield("a", artist_720 + ".")]
    field_720 = Field(tag="720", indicators=[" ", " "], subfields=subfields_720)
    base_record.add_ordered_field(field_720)

    return base_record


def create_discogs_record(data: dict) -> Record:
    """Convenience method to create MARC record from base record
    and Discogs data."""
    base_record = create_base_record()
    return add_discogs_data(base_record, data)


def create_musicbrainz_record(data: dict) -> Record:
    """Convenience method to create MARC record from base record
    and MusicBrainz data."""
    base_record = create_base_record()
    return add_musicbrainz_data(base_record, data)


def write_marc_record(record: Record, filename: str) -> None:
    """Write the record to a file in binary MARC format. Records are
    appended to the file.
    """
    with open(filename, "ab") as f:
        writer = MARCWriter(f)
        writer.write(record)


def get_yyyymmdd() -> str:
    """Get current date as YYYYMMDD (4-digit year)."""
    return datetime.today().strftime("%Y%m%d")


def get_yymmdd() -> str:
    """Get current date as YYMMDD (2-digit year only)."""
    return datetime.today().strftime("%y%m%d")
