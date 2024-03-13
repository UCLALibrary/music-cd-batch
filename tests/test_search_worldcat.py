import json
import unittest
from api_keys import (
    WORLDCAT_METADATA_CLIENT_ID,
    WORLDCAT_METADATA_CLIENT_SECRET,
    WORLDCAT_PRINCIPAL_ID,
    WORLDCAT_PRINCIPAL_IDNS,
)
from searchers.worldcat import WorldcatClient


class TestSearchWorldcat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create client for testing
        cls.worldcat_client = WorldcatClient(
            WORLDCAT_METADATA_CLIENT_ID,
            WORLDCAT_METADATA_CLIENT_SECRET,
            WORLDCAT_PRINCIPAL_ID,
            WORLDCAT_PRINCIPAL_IDNS,
        )
        # Load sample data for use by all tests.
        # Dict of dicts, keyed on UPC code, with real (as of 2024-03-12) response data.
        with open("tests/sample_data/worldcat_search_results.data") as f:
            cls.data = json.load(f)

    def test_get_oclc_numbers_no_results(self):
        response = self.data["790168505522"]
        oclc_numbers = self.worldcat_client.get_oclc_numbers(response)
        self.assertEqual(len(oclc_numbers), 0)

    def test_get_oclc_numbers_results(self):
        response = self.data["881626300329"]
        oclc_numbers = self.worldcat_client.get_oclc_numbers(response)
        self.assertEqual(len(oclc_numbers), 2)


class TestMarcXmlConversion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create client for testing
        cls.worldcat_client = WorldcatClient(
            WORLDCAT_METADATA_CLIENT_ID,
            WORLDCAT_METADATA_CLIENT_SECRET,
            WORLDCAT_PRINCIPAL_ID,
            WORLDCAT_PRINCIPAL_IDNS,
        )

    def test_xml_to_binary_marc(self):
        # Read sample MARC XML saved from Worldcat.
        with open("tests/sample_data/1011080915.xml", "rb") as f:
            xml = f.read()
        record = self.worldcat_client.convert_xml_to_marc(xml)
        # Basic access to MARC data via pymarc is enough
        self.assertEqual(record.title, "Pretty hate machine /")
