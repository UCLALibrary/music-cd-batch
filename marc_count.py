import argparse
from pymarc import MARCReader


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("marc_file", help="Path to a file of MARC records")
    args = parser.parse_args()
    marc_filename = args.marc_file
    record_count = get_marc_record_count(marc_filename)
    print(f"{marc_filename} contains {record_count} records.")


def get_marc_record_count(marc_filename: str) -> int:
    """Returns the number of records in a binary MARC file."""
    with open(marc_filename, "rb") as f:
        reader = MARCReader(f)
        # MARCReader is a iterator, with no built-in support for len().
        # Iterate over it and return the sum.
        return sum(1 for _ in reader)


if __name__ == "__main__":
    main()
