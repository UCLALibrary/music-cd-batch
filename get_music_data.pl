#!/usr/bin/env perl

use Data::Dumper qw(Dumper);
use File::Slurp qw(read_file);
use JSON qw(decode_json);
use LWP::UserAgent;
use MARC::File::XML (BinaryEncoding => 'utf8', RecordFormat => 'MARC21');
use MARC::Batch;
use feature qw(say);
use strict;
use warnings;
use utf8;

# Local libraries
use lib "/usr/local/bin/voyager/perl";
use UCLA::Worldcat::WSAPI;

# Include required API keys
BEGIN { require './api_keys.pl'; }

binmode STDOUT, ":utf8";

# 1 required argument: file containing values to search
if ($#ARGV != 0) {
  print "\nUsage: $0 upc_file\n";
    exit 1;
}

my $upc_file = $ARGV[0];

# Top-level resources used in various subroutines
my $browser = LWP::UserAgent->new();
$browser->agent('UCLA Library VBT-1035');
my $marc_file = $upc_file . '.mrc';

# Read search terms from file, one search per line.
my @lines = read_file($upc_file, chomp => 1);
# Each line has 3 fields: search term (UPC or music pub number), accession number, and barcode.
foreach my $line (@lines) {
  say "==============================";
  my ($search_term, $accession, $barcode) = split("\t", $line);
  say "Searching for: $search_term";
  SearchWorldcat($search_term);
  ###SearchDiscogs($search_term);
  ###SearchMusicbrainz($search_term);
  say "";
  sleep 1;
}

# End of main script, see subroutines below
exit 0;

##############################
# Searches for UPC or music publisher/issue number
# using the Discogs API.
sub SearchDiscogs {
  my $search_term = shift;
  # Discogs API key included above.

  my $discogs_url = 'https://api.discogs.com/database/search';
  # TODO: Figure out if value is UPC or not, which changes the API call
  $discogs_url .= "?q=$search_term&token=" . DISCOGS_TOKEN;

  # Call the API and store the result in JSON
  # TODO: Check response for more info?
  my $contents = $browser->get($discogs_url)->decoded_content;
  my $json = decode_json($contents);

  my $release = $json->{'results'}->[0];

  say "Discogs data:";
  #say "Title : ", $release->{'title'} if $release;

  # Experiment: Get first resource_url for release, then use that to get better
  # artist and title info?
  # Might have to cycle through releases to get one which is not a master.
  my $resource_url = $release->{'resource_url'} if $release;
  if ($resource_url) {
    $resource_url .= '?token=' . DISCOGS_TOKEN;
	#say $resource_url;
	$contents = $browser->get($resource_url)->decoded_content;
	$json = decode_json($contents);

	say "\tTitle : ", $json->{'title'};
	say "\tArtist: ", $json->{'artists_sort'};
	say "";
  }

}

##############################
# Searches for UPC or music publisher/issue number
# using the MusicBrainz API.
sub SearchMusicbrainz {
  my $search_term = shift;
  my $mb_url = 'http://musicbrainz.org/ws/2/release/?fmt=json&query=';
  # TODO: Figure out if value is UPC or not, which changes the API call
  $mb_url .= 'barcode:' . $search_term;

  # Call the API and store the result in JSON
  # TODO: Check response for more info?
  my $contents = $browser->get($mb_url)->decoded_content;
  my $json = decode_json($contents);

  my $release = $json->{'releases'}->[0];
  say "MusicBrainz data:";
  #say "UPC   : ", $release->{'barcode'};
  say "\tTitle : ", $release->{'title'} if $release;
  say "\tArtist: ", $release->{'artist-credit'}->[0]->{'artist'}->{'name'} if $release;
  say "";
}

##############################
# Searches for UPC or music publisher/issue number
# using the OCLC WorldCat Search API.
# WorldCat API key included above.
sub SearchWorldcat {
  my $search_term = shift;
  my $oclc = UCLA::Worldcat::WSAPI->new(WSKEY);

  my @marc_records = $oclc->search_sru_sn($search_term);
###TESTING
###my @marc_records = $oclc->search_sru('all scratched up'); 
  say "Found MARC records: " . scalar(@marc_records);

  # Evaluate MARC records, rejecting unsuitable ones, returning the one best remaining one (or none if all get rejected)
  my $best_record = EvaluateMARC(\@marc_records);

  # Proceed, if it's defined
  if ($best_record) {
    say "\tBest record: " . $best_record->oclc_number();
    say "\tTitle : ", $best_record->title();
  }

#  open MARC, '>>:utf8', $marc_file;
#  print MARC $marc->as_usmarc();
#  close MARC;

}

##############################
# Evaluate MARC records, rejecting unsuitable ones, returning
# the best remaining one record (or none, if all are rejected).
sub EvaluateMARC {
  my $marc_records = shift; # array reference
  my $best_marc;

  # Have to de-reference arrays...
  @$marc_records = RemoveUnsuitableRecords(\@$marc_records);

  # How many records are left?
  my $record_count = scalar(@$marc_records);
  say "Remaining: $record_count";

  # If no remaining records, this is undefined, which is fine
  return $best_marc if $record_count == 0;
  # If 1 remaining record, return it
  return @$marc_records[0] if $record_count == 1;

  # Multiple records remain: compare pairs to find the best
  # Start with the first record
  $best_marc = @$marc_records[0];
  # Iterate over the other records and compare:
  # Winner of [0,1] meets record 2; winner of that meets 3, etc.
  for (my $recnum = 1; $recnum < $record_count; $recnum++) {
    $best_marc = GetBestRecord($best_marc, @$marc_records[$recnum]);
  }

  return $best_marc;
}

##############################
# Remove unsuitable records from an array, returning just the acceptable ones.
sub RemoveUnsuitableRecords {
  my $marc_records = shift; # array reference
  my @keep_records = ();

  foreach my $marc_record (@$marc_records) {
    my $oclc_number = $marc_record->oclc_number();
	say "\tEvaluating " . $oclc_number;

	# Reject completely unsuitable records
	next if ! RecordIsSuitable($marc_record);

	# Reject if held by CLU
	if ($marc_record->held_by_clu()) {
	  say "\tREJECTED oclc $oclc_number - held by CLU";
	  next;
	}

	# Made it to here: save the record
	push(@keep_records, $marc_record);
  }

  return @keep_records;
}

##############################
# Check MARC record for suitability:
# Evaluate several conditions; record fails if any condition fails.
# Return 1 (true) if record passes; 0 (false) if not (it is unsuitable).
sub RecordIsSuitable {
  my $marc_record = shift;
  # Assume record will be acceptable
  my $OK = 1;
  # TODO: For debugging
  #say $marc_record->as_formatted();
  my $oclc_number = $marc_record->oclc_number();

  # Check 008/23 (form of item)
  my $fld008 = $marc_record->field('008')->data();
  if (substr($fld008, 23, 1) eq 'o') {
    say "\tREJECTED oclc $oclc_number - bad Form in 008/23";
	$OK = 0;
  }

  # Check LDR/06 (record type)
  if ($marc_record->record_type() !~ /[ij]/) {
    say "\tREJECTED oclc $oclc_number - bad Type in LDR/06";
	$OK = 0;
  }

  return $OK;
}

##############################
# Compare two MARC records and return the "best" one.
# Criteria: 040 $b, encoding level, number of holdings.
sub GetBestRecord {
  my ($record1, $record2) = @_;
  my $oclc_number1 = $record1->oclc_number();
  my $oclc_number2 = $record2->oclc_number();
  say "\tComparing $oclc_number1 and $oclc_number2...";

  my $score1 = 0;
  my $score2 = 0;

  # First: Compare 040 $b (language of cataloging), with preference to English.
  # Subfield may not exist in all records.
  my $lang1 = $record1->field('040')->subfield('b');
  my $lang2 = $record2->field('040')->subfield('b');
  $score1 += score_040b($lang1);
  $score2 += score_040b($lang2);
  if ($score1 > $score2) {
    say "\tLanguage: * $lang1 > $lang2";
  } elsif ($score2 > $score1) {
    say "\tLanguage: $lang1 < $lang2 *";
  } else {
    say "\tLanguage: $lang1 = $lang2";
  }

#say "DEBUG: Round 1: $score1 **** $score2";

  # Second: Compare encoding levels: (best to worst): Blank, 4, I, 1, 7, K, M, L, 3
  # Use instr to compare; lowest index (including -1 for not found) is worst.
  # Represent blank with '#' for printing clarity.
  my $elvl_values = '3LMK71I4#';
  my $elvl1 = $record1->encoding_level();
  my $elvl2 = $record2->encoding_level();
  if (index($elvl_values, $elvl1) > index($elvl_values, $elvl2)) {
    $score1 += 5;
	say "\tEncoding: * $elvl1 > $elvl2";
  } elsif (index($elvl_values, $elvl2) > index($elvl_values, $elvl1)) {
    $score2 += 5;
	say "\tEncoding: $elvl1 < $elvl2 *";
  } else {
    say "\tEncoding: $elvl1 = $elvl2";
  }

#say "DEBUG: Round 2: $score1 **** $score2";

  # Third: Compare number of holdings attached to each record.
  my $hcount1 = $record1->holdings_count();
  my $hcount2 = $record2->holdings_count();
  if ($hcount1 > $hcount2) {
    $score1 += 1;
	say "\tHoldings: * $hcount1 > $hcount2";
  } elsif ($hcount2 > $hcount1) {
	$score2 += 1;
	say "\tHoldings: $hcount1 < $hcount2 *";
  } else {
    say "\tHoldings: $hcount1 = $hcount2";
  }
  
#say "DEBUG: Round 3: $score1 **** $score2";

  # Return the record with best score, or record 1 if scores are equal
  if ($score1 >= $score2) {
    say "\t$oclc_number1 beats $oclc_number2";
    return $record1;
  } else {
    say "\t$oclc_number2 beats $oclc_number1";
    return $record2;
  }
}

##############################
# Get score for comparing 040 $b (language of cataloging) values.
sub score_040b {
  my $lang = shift;
  my $score;
  if (! $lang) {
    $score = 7;
	say "\t040 \$b is not defined";
  } elsif ($lang ne 'eng') {
    # Explicitly non-english, which is worst
    $score = 0;
  } else {
    # Default case, must be eng, which is best
	$score = 10;
  }
  return $score;
}

