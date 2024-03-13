from io import BytesIO
from bookops_worldcat import WorldcatAccessToken, MetadataSession
from pymarc import parse_xml_to_array, Record

# This uses bookops_worldcat, currently on version 0.5.0 which
# does not yet fully support OCLC's Metadata API 2.0.
# Some methods still use Metadata API 1.0, which is deprecated
# and scheduled to be decommissioned 2024-04-30.
# Devs are working on bookops_worldcat to bring it up to date;
# there may be breaking changes from this work.
# https://github.com/BookOps-CAT/bookops-worldcat/issues/63


class WorldcatClient:
    def __init__(
        self,
        key: str,
        secret: str,
        principal_id: str,
        principal_idns: str,
        scopes: list = ["WorldCatMetadataAPI"],
    ) -> None:
        self._KEY = key
        self._SECRET = secret
        self._PRINCIPAL_ID = principal_id
        self._PRINCIPAL_IDNS = principal_idns
        self._SCOPES = scopes
        # Token will be set on first use.
        self._token = None

    def _set_authentication_token(self):
        """Initialize authorization token needed for all Worldcat interactions."""
        # TODO: What if this API call fails, leaving invalid / no token?
        self._token = WorldcatAccessToken(
            key=self._KEY,
            secret=self._SECRET,
            principal_id=self._PRINCIPAL_ID,
            principal_idns=self._PRINCIPAL_IDNS,
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

    def search_worldcat(self, search_term: str, search_index: str) -> dict:
        """Search Worldcat via Bookops implementation of OCLC's Metadata API /search/brief-bibs.
        Return dict with search results.
        """
        query = f"{search_index}:{search_term}"
        with MetadataSession(authorization=self.token) as session:
            response = session.search_brief_bibs(q=query)
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

    def get_worldcat_records(self, oclc_numbers: list) -> list[Record]:
        """Retrieve full MARC records from Worldcat, using Bookops implementation of OCLC's
        Metadata (1.0) API /bib/data and pymarc's XML -> MARC conversion.
        Return list of MARC records, or empty list if no records found.
        """
        records = []
        with MetadataSession(authorization=self.token) as session:
            for oclc_number in oclc_numbers:
                response = session.get_full_bib(oclc_number)
                data = BytesIO(response.content)
                bib = parse_xml_to_array(data)[0]
                records.append(bib)
        return records

    def is_held_by(self, oclc_number: str, oclc_symbol: str = "CLU") -> bool:
        """Determine whether the given OCLC number is held by the given OCLC symbol.
        Defaults to CLU for UCLA.
        """
        with MetadataSession(authorization=self.token) as session:
            response = session.holding_get_status(oclc_number, instSymbol=oclc_symbol)
            data = response.json()
            return data.get("content").get("holdingCurrentlySet")
