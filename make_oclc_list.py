import argparse
from pymarc import MARCReader


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("marc_file", help="Path to a file of MARC records")
    args = parser.parse_args()
    print_oclc_numbers(args.marc_file)


def print_oclc_numbers(marc_filename: str) -> None:
    """Prints the OCLC numbers (the digits in the 001 field) to stdout
    for each record in a file of MARC records.
    Assumes the records are indeed from OCLC, rather than checking the 003
    to try to confirm that.
    """
    with open(marc_filename, "rb") as f:
        reader = MARCReader(f)
        for record in reader:
            fld001 = record.get("001")
            if fld001:
                oclc_number = "".join(d for d in fld001.data if d.isdigit())
                print(oclc_number)


if __name__ == "__main__":
    main()
