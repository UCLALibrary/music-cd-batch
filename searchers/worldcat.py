from io import BytesIO
from bookops_worldcat import WorldcatAccessToken, MetadataSession
from pymarc import parse_xml_to_array, Record


class WorldcatClient:
    def __init__(
        self,
        key: str,
        secret: str,
        scopes: str = "WorldCatMetadataAPI",
    ) -> None:
        self._KEY = key
        self._SECRET = secret
        self._SCOPES = scopes
        # Token will be set on first use.
        self._token = None

    def _set_authentication_token(self):
        """Initialize authorization token needed for all Worldcat interactions."""
        # TODO: What if this API call fails, leaving invalid / no token?
        self._token = WorldcatAccessToken(
            key=self._KEY,
            secret=self._SECRET,
            scopes=self._SCOPES,
        )

    @property
    def token(self) -> str:
        """Return existing token if set and still valid;
        otherwise, obtain and set new token.
        """
        if (self._token is not None) and (not self._token.is_expired()):
            # Do nothing, return at end
            pass
        else:
            self._set_authentication_token()
        return self._token

    def search(self, search_term: str, search_index: str) -> dict:
        """Search Worldcat via Bookops implementation of OCLC's Metadata API /search/brief-bibs.

        Return dict with search results.
        """
        query = f"{search_index}:{search_term}"
        with MetadataSession(authorization=self.token) as session:
            response = session.brief_bibs_search(q=query)
            # TODO: Handle failures / errors
            return response.json()

    def get_oclc_numbers(self, search_results: dict) -> list:
        """Return list of OCLC numbers matching the search, or empty list if no records found."""
        if search_results.get("numberOfRecords") == 0:
            oclc_numbers = []
        else:
            # Actual data is in list of dictionaries in briefRecords
            oclc_numbers = [
                record.get("oclcNumber")
                for record in search_results.get("briefRecords")
            ]
        return oclc_numbers

    def get_xml(self, oclc_number: str) -> bytes:
        """Retrieve full MARC XML record from Worldcat, using Bookops implementation of OCLC's
        Metadata (1.0) API /bib/data.

        Return bytes (containing XML) as that's what the API returns
        """
        with MetadataSession(authorization=self.token) as session:
            response = session.bib_get(oclc_number)
            # TEMPORARY: Dump XML to file for manual review.
            # with open(f"{oclc_number}.xml", "wb") as f:
            #     f.write(response.content)
            return response.content

    def convert_xml_to_marc(self, xml: bytes) -> Record:
        """Convert MARC XML from Worldcat to a pymarc Record object.

        Return pymarc.Record
        """
        # Convert bytes to file-like object for pymarc's parse_xml_to_array
        data = BytesIO(xml)
        # pymarc.parse_xml_to_array can handle XML with multiple records, so it returns a list;
        # return only the first record, though there should only be one from Worldcat anyhow.
        return parse_xml_to_array(data)[0]

    def get_records(self, oclc_numbers: list) -> list[Record]:
        """Retrieve full MARC records from Worldcat, using Bookops implementation of OCLC's
        Metadata (1.0) API /bib/data and pymarc's XML -> MARC conversion.

        Return list of MARC records, or empty list if no records found.
        """
        records = []
        for oclc_number in oclc_numbers:
            xml = self.get_xml(oclc_number)
            bib = self.convert_xml_to_marc(xml)
            # TEMPORARY: Dump binary marc record to file for manual review.
            # with open(f"{oclc_number}.mrc", "wb") as f:
            #     f.write(bib.as_marc21())
            records.append(bib)
        return records

    def is_held_by_us(self, oclc_number: str) -> bool:
        """Determine whether the given OCLC number is held by the institution(s)
        associated with the authorization token.
        """
        with MetadataSession(authorization=self.token) as session:
            response = session.holdings_get_current(oclc_number)
            data = response.json().get("holdings")
            # This is a list of dictionaries - 1 per requestedControlNumber?
            # [{'requestedControlNumber': '56713778', 'currentControlNumber': '56713778',
            # 'institutionSymbol': 'CLU', 'holdingSet': False}]
            for entry in data:
                if entry["requestedControlNumber"] == oclc_number:
                    return entry["holdingSet"]
