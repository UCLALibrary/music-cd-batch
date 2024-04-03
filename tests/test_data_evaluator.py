import unittest

from pymarc import Field, Record
from data_evaluator import (
    cataloging_language_is_ok,
    form_of_item_is_ok,
    get_encoding_level_score,
    normalize,
    normalize_title,
    record_type_is_ok,
    strip_punctuation,
)
from create_marc_record import create_base_record


class NormalizationTests(unittest.TestCase):
    def test_normalize_title(self):
        input = "Main title: subtitle!"
        normalized_input = normalize_title(input)
        self.assertEqual(normalized_input, "Main Title Subtitle")

    def test_normalize_general(self):
        input = "Main title: subtitle!"
        normalized_input = normalize(input)
        self.assertEqual(normalized_input, "MAINTITLESUBTITLE")

    def test_strip_punctuation(self):
        input = "Common punctuation: .,;:/-()#%&*$@!"
        normalized_input = strip_punctuation(input)
        self.assertEqual(normalized_input, "Common punctuation ")


class RecordQualityTests(unittest.TestCase):
    def get_base_record(self) -> Record:
        # Create base record for use in all tests in this class.
        # Not a class method, as some tests change the data.
        base_record = create_base_record()
        # Add a fake OCLC# which some methods expect for logging.
        base_record.add_field(Field(tag="001", data="fake_oclc_number"))
        return base_record

    def test_record_type_is_ok(self):
        base_record = self.get_base_record()
        # Default base record type is always OK;
        # change it to an unacceptable value.
        # Type (Leader/06) - a (Language material, like a book)
        base_record.leader.type_of_record = "a"
        self.assertFalse(record_type_is_ok(base_record))

    def test_form_of_item_is_ok(self):
        base_record = self.get_base_record()
        # Default base item form is always OK;
        # Change it to an unacceptable value: 008/23 = "o" (online)
        fld008 = base_record.get("008")
        # Hacky since Python doesn't have targeted index string replacement...
        fld008.data = fld008.data[0:23] + "o" + fld008.data[24:]
        self.assertFalse(form_of_item_is_ok(base_record))

    def test_cataloging_language_is_ok(self):
        base_record = self.get_base_record()
        # Default cataloging language is always OK;
        # Change it to an unacceptable value: 040 $b = "fre" (French)
        fld040 = base_record.get("040")
        fld040["b"] = "fre"
        self.assertFalse(cataloging_language_is_ok(base_record))

    def test_get_encoding_level_score(self):
        base_record = self.get_base_record()
        # Default encoding level is "3" (lowest score of 0)
        self.assertEqual(get_encoding_level_score(base_record), 0)
        # Change it to blank, which scores 8
        base_record.leader.encoding_level = " "
        self.assertEqual(get_encoding_level_score(base_record), 8)
        # Change it to unacceptable "z", which scores -1
        base_record.leader.encoding_level = "z"
        self.assertEqual(get_encoding_level_score(base_record), -1)
