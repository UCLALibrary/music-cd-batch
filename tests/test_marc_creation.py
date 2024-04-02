import unittest
from create_marc_record import create_base_record


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
