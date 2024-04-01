from pymarc import Record, Field, Subfield


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
    record.add_field(Field(tag="008", data="YYMMDDs||||    xx ||nn          n ||| d"))

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

    # 049 ## $a CLUV $l BARCODE
    subfields_049 = [Subfield("a", "CLUV"), Subfield("l", "BARCODE")]
    field_049 = Field(tag="049", indicators=[" ", " "], subfields=subfields_049)
    record.add_field(field_049)

    # 099 ## $a CDA #
    subfields_099 = [Subfield("a", "CDA #")]
    field_099 = Field(tag="099", indicators=[" ", " "], subfields=subfields_099)
    record.add_field(field_099)

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

    # 962 ## $a cmc $b meherbatch $c YYYYMMDD $d 3 $k meherorig $9 LOCAL
    subfields_962 = [
        Subfield("a", "cmc"),
        Subfield("b", "meherbatch"),
        Subfield("c", "YYYYMMDD"),
        Subfield("d", "3"),
        Subfield("k", "meherorig"),
        Subfield("9", "LOCAL"),
    ]
    field_962 = Field(tag="962", indicators=[" ", " "], subfields=subfields_962)
    record.add_field(field_962)

    # 966 ## $a MEHER $b Donovan Meher Collection $9 LOCAL
    subfields_966 = [
        Subfield("a", "MEHER"),
        Subfield("b", "Donovan Meher Collection"),
        Subfield("9", "LOCAL"),
    ]
    field_966 = Field(tag="966", indicators=[" ", " "], subfields=subfields_966)
    record.add_field(field_966)

    return record
