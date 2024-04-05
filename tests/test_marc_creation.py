import unittest

from pymarc import Subfield
from create_marc_record import add_local_fields, create_base_record


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
