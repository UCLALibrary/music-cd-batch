import unittest
import json

from pymarc import Subfield, Record
from create_marc_record import (
    add_local_fields,
    create_base_record,
    add_discogs_data,
    add_musicbrainz_data,
    get_yymmdd,
)


class TestBaseRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create base record for use in all tests in this class.
        cls.base_record = create_base_record()

    def test_fld007_length(self):
        fld007 = self.base_record.get("007")
        self.assertEqual(len(fld007.data), 14)

    def test_fld008_length(self):
        fld008 = self.base_record.get("008")
        self.assertEqual(len(fld008.data), 40)

    def test_fld344_repeated(self):
        fld344s = self.base_record.get_fields("344")
        self.assertEqual(len(fld344s), 2)


class TestLocalFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create simulated record for use in all tests in this class.
        base_record = create_base_record()
        cls.record = add_local_fields(
            base_record, barcode="FAKE BARCODE", call_number="FAKE CALL NUMBER"
        )

    def test_barcode_is_added(self):
        fld049 = self.record.get("049")
        expected_subfields = [
            Subfield(code="a", value="CLUV"),
            Subfield(code="l", value="FAKE BARCODE"),
        ]
        self.assertEqual(fld049.subfields, expected_subfields)

    def test_call_number_is_added(self):
        fld049 = self.record.get("099")
        expected_subfields = [
            Subfield(code="a", value="FAKE CALL NUMBER"),
        ]
        self.assertEqual(fld049.subfields, expected_subfields)

    def test_590_with_cases(self):
        # default test case is with cases, so we should not have a 590 field
        fld590 = self.record.get("590")
        self.assertEqual(fld590, None)

    def test_590_without_cases(self):
        base_record = create_base_record()
        record = add_local_fields(
            base_record,
            barcode="FAKE BARCODE",
            call_number="FAKE CALL NUMBER",
            no_cases=True,
        )
        fld590 = record.get("590")
        self.assertEqual(fld590.subfields[0].code, "a")
        self.assertEqual(
            fld590.subfields[0].value, "UCLA Music Library copy lacks container insert."
        )


class TestDiscogsFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create simulated record for use in all tests in this class.
        base_record = create_base_record()
        cls.record = add_local_fields(
            base_record, barcode="FAKE BARCODE", call_number="FAKE CALL NUMBER"
        )
        with open("tests/sample_data/formatted_discogs_sample.data") as f:
            data = json.load(f)
        cls.record = add_discogs_data(cls.record, data)

    def create_fake_record(self) -> Record:
        # Create minimal fake record with specific data for some tests.
        fake_discogs_data = {
            "title": "FAKE TITLE",
            "artist": "FAKE ARTIST",
            "publisher_number": "FAKE PUBNUM",
            "full_json": {
                "id": 999999,
                "year": 0,
                "artists_sort": "FAKE ARTIST",
                "labels": [
                    {"catno": "FAKE001", "name": "FAKE PUB 01"},
                    {"catno": "FAKE001", "name": "FAKE PUB 02"},
                    {"catno": "FAKE001", "name": "FAKE PUB 02"},
                ],
                "identifiers": [
                    {
                        "type": "Barcode",
                        "value": "Unused",
                        "description": "Text",
                    },
                    {
                        "type": "Barcode",
                        "value": "FAKEBARCODE001",
                        "description": "Valid",
                    },
                    {
                        "type": "Barcode",
                        "value": "FAKEBARCODE001",
                        "description": "Duplicate",
                    },
                ],
            },
        }
        base_record = create_base_record()
        fake_record = add_local_fields(
            base_record, barcode="FAKE BARCODE", call_number="FAKE CALL NUMBER"
        )
        fake_record = add_discogs_data(fake_record, fake_discogs_data)
        return fake_record

    def test_field_008(self):
        fld008 = self.record.get("008")
        today_yymmdd = get_yymmdd()
        expected_data = today_yymmdd + "s2003    xx ||nn           n zxx d"
        self.assertEqual(fld008.data, expected_data)

    def test_field_008_no_year(self):
        fake_record = self.create_fake_record()
        fld008 = fake_record.get("008")
        today_yymmdd = get_yymmdd()
        expected_data = today_yymmdd + "suuuu    xx ||nn           n zxx d"
        self.assertEqual(fld008.data, expected_data)

    def test_field_024(self):
        fld024 = self.record.get("024")
        # one barcode in the sample data
        expected_subfields = [
            Subfield(code="a", value="5021958414720"),
        ]
        self.assertEqual(fld024.subfields, expected_subfields)

    def test_field_024_duplicate_barcodes_are_ignored(self):
        fake_record = self.create_fake_record()
        # Data for fake record has 3 barcode identifiers:
        # 1 invalid, 2 valid but identical
        fld024s = fake_record.get_fields("024")
        self.assertEqual(len(fld024s), 1)

    def test_field_028(self):
        fld028 = self.record.get("028")
        self.assertEqual(fld028.subfields[0].code, "a")
        self.assertEqual(fld028.subfields[0].value, "UDX 092")
        self.assertEqual(fld028.subfields[1].code, "b")
        self.assertEqual(fld028.subfields[1].value, "United Dairies")

    def test_field_028_catnos_are_deduped(self):
        fake_record = self.create_fake_record()
        # Data for fake record has 3 catno labels:
        # all catnos are identical, but 2 different names,
        # so 2 028 fields should be created.
        fld028s = fake_record.get_fields("028")
        self.assertEqual(len(fld028s), 2)

    def test_field_245(self):
        fld245 = self.record.get("245")
        self.assertEqual(fld245.subfields[0].code, "a")
        self.assertEqual(fld245.subfields[0].value, "Soliloquy For Lilith /")
        self.assertEqual(fld245.subfields[1].code, "c")
        self.assertEqual(fld245.subfields[1].value, "Nurse With Wound.")
        self.assertEqual(fld245.indicators, ["0", "0"])

    def test_field_264(self):
        fld264 = self.record.get("264")
        self.assertEqual(fld264.subfields[0].code, "a")
        self.assertEqual(
            fld264.subfields[0].value, "[Place of publication not identified] :"
        )
        self.assertEqual(fld264.subfields[1].code, "b")
        self.assertEqual(fld264.subfields[1].value, "United Dairies,")
        self.assertEqual(fld264.subfields[2].value, "[2003]")

    def test_field_300(self):
        fld300 = self.record.get("300")
        self.assertEqual(fld300.subfields[0].code, "a")
        self.assertEqual(fld300.subfields[0].value, "3 audio discs :")
        self.assertEqual(fld300.subfields[1].code, "b")
        self.assertEqual(fld300.subfields[1].value, "digital ;")
        self.assertEqual(fld300.subfields[2].value, "4 3/4 in.")

    def test_field_500(self):
        fld500 = self.record.get("500")
        self.assertEqual(fld500.subfields[0].code, "a")
        self.assertEqual(
            fld500.subfields[0].value,
            "Record generated from Discogs database.",
        )

    def test_field_505(self):
        fld505 = self.record.get("505")
        # All track lists go into one big 505 $a.
        self.assertEqual(len(fld505.subfields), 1)
        self.assertEqual(fld505.subfields[0].code, "a")
        # The sample record has 8 tracks, separated by " -- ".
        tracks = fld505.subfields[0].value.split(" -- ")
        self.assertEqual(len(tracks), 8)

    def test_field_653(self):
        fld653 = self.record.get("653")
        self.assertEqual(fld653.subfields[0].code, "a")
        self.assertEqual(fld653.subfields[0].value, "Electronic")

    def test_field_720(self):
        fld720 = self.record.get("720")
        self.assertEqual(fld720.subfields[0].code, "a")
        self.assertEqual(fld720.subfields[0].value, "Nurse With Wound.")


class TestMusicBrainzFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create simulated record for use in all tests in this class.
        base_record = create_base_record()
        cls.record = add_local_fields(
            base_record, barcode="FAKE BARCODE", call_number="FAKE CALL NUMBER"
        )
        with open("tests/sample_data/formatted_musicbrainz_sample.data") as f:
            data = json.load(f)
        cls.record = add_musicbrainz_data(cls.record, data)

    def create_fake_record(self) -> Record:
        # Create minimal fake record with specific data for some tests.
        fake_musicbrainz_data = {
            "title": "FAKE TITLE",
            "artist": "FAKE ARTIST",
            "publisher_number": "FAKE PUBNUM",
            "full_json": {
                "id": 999999,
                "date": "0",
                "artist-credit": [
                    {
                        "name": "FAKE ARTIST",
                        "artist": {
                            "id": "FAKEID",
                            "name": "FAKE ARTIST",
                            "sort-name": "FAKE ARTIST",
                        },
                    }
                ],
                "text-representation": {"language": "eng", "script": "Latn"},
                "barcode": "FAKEBARCODE01",
                "medium-count": 1,
                "tag-list": [],
                "label-info-list": [
                    {
                        "catalog-number": "FAKE001",
                        "label": {
                            "name": "FAKE PUB 01",
                        },
                    },
                    {
                        "catalog-number": "FAKE001",
                        "label": {
                            "name": "FAKE PUB 02",
                        },
                    },
                    {
                        "catalog-number": "FAKE001",
                        "label": {
                            "name": "FAKE PUB 02",
                        },
                    },
                ],
            },
        }
        base_record = create_base_record()
        fake_record = add_local_fields(
            base_record, barcode="FAKE BARCODE", call_number="FAKE CALL NUMBER"
        )
        fake_record = add_musicbrainz_data(fake_record, fake_musicbrainz_data)
        return fake_record

    def test_field_024(self):
        fld024 = self.record.get("024")
        # one barcode in the sample data
        expected_subfields = [
            Subfield(code="a", value="5021958414720"),
        ]
        self.assertEqual(fld024.subfields, expected_subfields)

    def test_field_028(self):
        fld028 = self.record.get("028")
        self.assertEqual(fld028.subfields[0].code, "a")
        self.assertEqual(fld028.subfields[0].value, "UD092")
        self.assertEqual(fld028.subfields[1].code, "b")
        self.assertEqual(fld028.subfields[1].value, "United Dairies")

    def test_field_028_catnos_are_deduped(self):
        fake_record = self.create_fake_record()
        # Data for fake record has 3 catno labels:
        # all catnos are identical, but 2 different names,
        # so 2 028 fields should be created.
        fld028s = fake_record.get_fields("028")
        self.assertEqual(len(fld028s), 2)

    def test_field_245(self):
        fld245 = self.record.get("245")
        self.assertEqual(fld245.subfields[0].code, "a")
        # musicbrainz data has different capitalization than discogs
        self.assertEqual(fld245.subfields[0].value, "Soliloquy for Lilith /")
        self.assertEqual(fld245.subfields[1].code, "c")
        self.assertEqual(fld245.subfields[1].value, "Nurse With Wound.")
        self.assertEqual(fld245.indicators, ["0", "0"])

    def test_field_264(self):
        fld264 = self.record.get("264")
        self.assertEqual(fld264.subfields[0].code, "a")
        self.assertEqual(
            fld264.subfields[0].value, "[Place of publication not identified] :"
        )
        self.assertEqual(fld264.subfields[1].code, "b")
        self.assertEqual(fld264.subfields[1].value, "United Dairies,")
        self.assertEqual(fld264.subfields[2].value, "[2003]")

    def test_field_300(self):
        fld300 = self.record.get("300")
        self.assertEqual(fld300.subfields[0].code, "a")
        self.assertEqual(fld300.subfields[0].value, "3 audio discs :")
        self.assertEqual(fld300.subfields[1].code, "b")
        self.assertEqual(fld300.subfields[1].value, "digital ;")
        self.assertEqual(fld300.subfields[2].value, "4 3/4 in.")

    def test_field_500(self):
        fld500 = self.record.get("500")
        self.assertEqual(fld500.subfields[0].code, "a")
        self.assertEqual(
            fld500.subfields[0].value,
            "Record generated from MusicBrainz database.",
        )

    def test_field_653(self):
        fld653 = self.record.get("653")
        # MusicBrainz record doesn't have genre information
        self.assertEqual(fld653, None)

    def test_field_720(self):
        fld720 = self.record.get("720")
        self.assertEqual(fld720.subfields[0].code, "a")
        self.assertEqual(fld720.subfields[0].value, "Nurse With Wound.")
