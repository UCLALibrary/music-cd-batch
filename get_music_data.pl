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

# Output from XML and JSON should all be in UTF-8
binmode STDOUT, ":utf8";
# Flush STDOUT buffers immediately so we can view output in real time
STDOUT->autoflush(1);

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

  # First, search Discogs and MusicBrainz for the given term.
  # Among other data, collect music publisher number(s) from those sources.
  my %discogs_data = search_discogs($search_term);
  my %mb_data = search_musicbrainz($search_term);

  my $marc_record = search_worldcat($search_term);
  # If initial search on UPC didn't find anything, try searching for
  # the music publisher numbers from Discogs/MusicBrainz.
  if (! $marc_record) {
    # Use hash for automatic uniqueness; values all are 1, we only care about the unique keys.
    my %search_terms;
    $search_terms{$discogs_data{'pub_num'}} = 1 if $discogs_data{'pub_num'};
    $search_terms{$mb_data{'pub_num'}} = 1 if %mb_data;
	# Convert the hash to an array
    my @search_terms = (keys %search_terms);
###say Dumper(@search_terms);
	if (@search_terms) {
	  say "Searching WorldCat again for music publisher numbers... ", join(", ", @search_terms);
      $marc_record = search_worldcat(\@search_terms);
	}
  }

  # If there's a MARC record now, use it
  if ($marc_record) {
	say "";
    say "\tBest record: " . $marc_record->oclc_number();
	report_marc_problems($marc_record);
	$marc_record = add_local_fields($marc_record, $accession, $barcode);

	# Save the record as binary MARC
    open MARC, '>>:utf8', $marc_file;
    print MARC $marc_record->as_usmarc();
    close MARC;

	# Output for title review
	say "";
    say "\tWC Title: ", $marc_record->title();

  } else {
    # TODO: Create basic MARC record from DC/MB data?
  }

  # Print artists & titles for comparison
  say "\tDC Title: " . $discogs_data{'title'} . " / " . $discogs_data{'artist'} if %discogs_data;;
  say "\tMB Title: " . $mb_data{'title'} . " / " . $mb_data{'artist'} if %mb_data;
  say "";
  # Discogs and Musicbrainz have rate limits on their APIs
  sleep 1;
}
say "=== END OF LOG ===";

# End of main script, see subroutines below
exit 0;

##############################
# Searches for UPC or music publisher/issue number
# using the Discogs API.
# Note: Rate limit of 60/minute for authenticated users.
sub search_discogs {
  my $search_term = shift;
  # Data to be returned to caller for later use.
  my %discogs_data;

  # Discogs API key included above.

  my $discogs_url = 'https://api.discogs.com/database/search';
  # TODO: Figure out if value is UPC or not, which changes the API call
  $discogs_url .= "?q=$search_term&token=" . DISCOGS_TOKEN;

  # Call the API and store the result in JSON
  my $contents = $browser->get($discogs_url)->decoded_content;
  my $json = decode_json($contents);

  # Search API gives minimal info.
  # Call first "releases" resource_url from initial data 
  # to get detailed data.
  if ($json) {
    foreach my $result (@{$json->{'results'}}) {
	  my $resource_url = $result->{'resource_url'};
	  if ($resource_url =~ /releases/) {
	    $resource_url .= '?token=' . DISCOGS_TOKEN;
		$contents = $browser->get($resource_url)->decoded_content;
		my $release_json = decode_json($contents);
		my $title = $release_json->{'title'};
		my $artist = $release_json->{'artists_sort'};
		my $pub_num = $release_json->{'labels'}->[0]->{'catno'};
		$pub_num = normalize_pub_num($pub_num) if $pub_num;
		# Discogs sends literal 'none' for pub_num if no data; remove that
		undef $pub_num if $pub_num eq 'none';

        #say "Discogs data:";
	    #say "\tTitle : $title / $artist";
	    say "\tDC Pubnum: $pub_num" if $pub_num;
	    #say "";
		$discogs_data{'title'} = $title if $title;
		$discogs_data{'artist'} = $artist if $artist;
		$discogs_data{'pub_num'} = $pub_num if $pub_num;
		last; # Only check the first matching resource_url
	  }
	}
  }
  return %discogs_data;
}

##############################
# Searches for UPC or music publisher/issue number
# using the MusicBrainz API.
# Note: Rate limit of 60/minute (on average) per IP address.
sub search_musicbrainz {
  my $search_term = shift;
  # Data to be returned to caller for later use.
  my %mb_data;
  my $mb_url = 'http://musicbrainz.org/ws/2/release/?fmt=json&query=';
  # TODO: Figure out if value is UPC or not, which changes the API call
  $mb_url .= 'barcode:' . $search_term;

  # Call the API and store the result in JSON
  # TODO: Check response for more info?
  my $contents = $browser->get($mb_url)->decoded_content;
  my $json = decode_json($contents);

  if ($json) {
    my $release = $json->{'releases'}->[0];
	if ($release) {
	  my $title = $release->{'title'};
	  my $artist = $release->{'artist-credit'}->[0]->{'artist'}->{'name'};
	  my $pub_num = $release->{'label-info'}->[0]->{'catalog-number'};
      $pub_num = normalize_pub_num($pub_num) if $pub_num;
	  $pub_num = '' if ! $pub_num;
      #say "MusicBrainz data:";
      #say "\tTitle : $title / $artist";
      say "\tMB Pubnum: $pub_num";
      #say "";
	  %mb_data = ('title' => $title, 'artist' => $artist, 'pub_num' => $pub_num);
	}
  }
  return %mb_data;
}

##############################
# Searches for UPC or music publisher/issue number
# using the OCLC WorldCat Search API.
# WorldCat API key included above.
sub search_worldcat {
  my $search_terms_ref = shift;
  my $oclc = UCLA::Worldcat::WSAPI->new(WSKEY);

  my @marc_records = $oclc->search_sru_sn($search_terms_ref);
  say "Found MARC records: " . scalar(@marc_records);

  # Evaluate MARC records, rejecting unsuitable ones, returning the one best remaining one (or none if all get rejected)
  my $best_record = evaluate_marc(\@marc_records) if @marc_records;

  # TODO: Decide what you're really returning from here......
  return $best_record;
}

##############################
# Evaluate MARC records, rejecting unsuitable ones, returning
# the best remaining one record (or none, if all are rejected).
sub evaluate_marc {
  my $marc_records = shift; # array reference
  my $best_marc;

  # Have to de-reference arrays...
  @$marc_records = remove_unsuitable_records(\@$marc_records);

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
    $best_marc = get_best_record($best_marc, @$marc_records[$recnum]);
  }

  return $best_marc;
}

##############################
# Remove unsuitable records from an array, returning just the acceptable ones.
sub remove_unsuitable_records {
  my $marc_records = shift; # array reference
  my @keep_records = ();

  foreach my $marc_record (@$marc_records) {
    my $oclc_number = $marc_record->oclc_number();

	# Reject completely unsuitable records
	next if ! record_is_suitable($marc_record);

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
sub record_is_suitable {
  my $marc_record = shift;
  # Assume record will be acceptable
  my $OK = 1;
  # TODO: For debugging
  #say $marc_record->as_formatted();
  my $oclc_number = $marc_record->oclc_number();

  # Check 008/23 (form of item)
  # All OCLC records have 008 - ?
  my $fld008 = $marc_record->field('008')->data();
  if (substr($fld008, 23, 1) eq 'o') {
    say "\tREJECTED oclc $oclc_number - bad Form in 008/23";
	$OK = 0;
  }

  # Check LDR/06 (record type)
  if ($marc_record->record_type() !~ /[ij]/) {
    say "\tREJECTED oclc $oclc_number - bad Type in LDR/06 " . $marc_record->record_type();
	$OK = 0;
  }
  
  # Check 007/03 (speed, for sound recordings)
  # CDs should have 007/03 = f (1.4 m/sec)... TODO? but some have z (unknown), allow that too.
  # However, allow records which lack 007 completely as not always coded.
  # TODO: Move this check to warnings, for accepted records?
  # Not reliable enough to exclude records.
  #my $fld007 = $marc_record->field('007');
  #if ($fld007) {
  #  my $speed = substr($fld007->data(), 3, 1);
	#if ($speed !~ /[f]/) {
    #  say "\tREJECTED oclc $oclc_number - bad Speed in 007/03: $speed";
	#  $OK = 0;
	#}
  #}

  # TODO: Experiment: Check 007/06 (dimensions, for sound recordings)
  # CDs should have 007/06 = g (4 3/4 in)
  #my $fld007 = $marc_record->field('007');
  #if ($fld007) {
  #  my $dimension = substr($fld007->data(), 6, 1);
#	if ($dimension !~ /[g]/) {
#      say "\tREJECTED oclc $oclc_number - bad Dimension in 007/06: $dimension";
#	  $OK = 0;
#	}
#  }

  return $OK;
}

##############################
# Compare two MARC records and return the "best" one.
# Criteria: 040 $b, encoding level, number of holdings.
sub get_best_record {
  my ($record1, $record2) = @_;
  my $oclc_number1 = $record1->oclc_number();
  my $oclc_number2 = $record2->oclc_number();
  say "\tComparing OCLC $oclc_number1 and $oclc_number2...";

  my $score1 = 0;
  my $score2 = 0;

  # First: Compare 040 $b (language of cataloging), with preference to English.
  # Subfield may not exist in all records.
  my $lang1 = $record1->field('040')->subfield('b');
  my $lang2 = $record2->field('040')->subfield('b');
  $score1 += score_040b($lang1);
  $score2 += score_040b($lang2);
  if ($score1 > $score2) {
    say "\t\tLanguage: * $lang1 > $lang2";
  } elsif ($score2 > $score1) {
    say "\t\tLanguage: $lang1 < $lang2 *";
  } else {
	# Langs may not be the same, but both score equivalently - good enough
    say "\t\tLanguage: $lang1 = $lang2";
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
	say "\t\tEncoding: * $elvl1 > $elvl2";
  } elsif (index($elvl_values, $elvl2) > index($elvl_values, $elvl1)) {
    $score2 += 5;
	say "\t\tEncoding: $elvl1 < $elvl2 *";
  } else {
    say "\t\tEncoding: $elvl1 = $elvl2";
  }

#say "DEBUG: Round 2: $score1 **** $score2";

  # Third: Compare number of holdings attached to each record.
  my $hcount1 = $record1->holdings_count();
  my $hcount2 = $record2->holdings_count();
  if ($hcount1 > $hcount2) {
    $score1 += 1;
	say "\t\tHoldings: * $hcount1 > $hcount2";
  } elsif ($hcount2 > $hcount1) {
	$score2 += 1;
	say "\t\tHoldings: $hcount1 < $hcount2 *";
  } else {
    say "\t\tHoldings: $hcount1 = $hcount2";
  }
  
#say "DEBUG: Round 3: $score1 **** $score2";

  # Return the record with best score, or record 1 if scores are equal
  if ($score1 >= $score2) {
    say "\t\t$oclc_number1 beats $oclc_number2";
    return $record1;
  } else {
    say "\t\t$oclc_number2 beats $oclc_number1";
    return $record2;
  }
  say "";
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

##############################
# Normalize music publisher number by 
# removing space and hyphen.
sub normalize_pub_num {
  my $pub_num = shift;
  $pub_num =~ s/[ -]//g;
  return $pub_num;
}


##############################
# Report problems with MARC record we're keeping,
# for later review / cleanup.
sub report_marc_problems {
  my $marc_record = shift;
  my $fld;
  my $sfd;

  # 040 $b exists, but is not eng; both are not repeatable
  $fld = $marc_record->field('040');
  if ($fld) {
    $sfd = $fld->subfield('b');
	if ($sfd && $sfd ne 'eng') {
      say "\t\tWARNING: 040 \$b = $sfd";
	}
  }

  # No 007 and/or 300 and/or 650
  say "\t\tWARNING: No 007 field" if not has_field($marc_record, qw(007));
  say "\t\tWARNING: No 300 field" if not has_field($marc_record, qw(300));
  say "\t\tWARNING: No 650 field" if not has_field($marc_record, qw(650));

  # None of 100/110/700/710 name fields
  say "\t\tWARNING: No 100/110/700/710 fields" if not has_field($marc_record, qw(100 110 700 710));

  # None of 260/264 publisher fields
  say "\t\tWARNING: No 260/264 fields" if not has_field($marc_record, qw(260 264));

  # None of 500/505/511/518 note fields
  say "\t\tWARNING: No 500/505/511/518 fields" if not has_field($marc_record, qw(500 505 511 518));

  # 245 $n or 490 $v exists, meaning it's probably a multi-CD set
  $fld = $marc_record->field('245');
  if ($fld) {
    $sfd = $fld->subfield('n');
    say "\t\tWARNING: 245 \$n = $sfd" if $sfd;
  }
  $fld = $marc_record->field('490');
  if ($fld) {
    $sfd = $fld->subfield('v');
    say "\t\tWARNING: 490 \$v = $sfd" if $sfd;
  }

}

##############################
# Test whether MARC record has any of the given fields
# in the @fields parameter.
sub has_field {
  my $marc_record = shift;
  my @fields = @_;
  my $has_it = 0; # false until we find it
  foreach my $fld (@fields) {
    $has_it = $marc_record->field($fld);
	# Return early if found any field
	return $has_it if $has_it;
  }
  # Made it to the end, return default value of false
  return $has_it;
}

##############################
# Add local fields to MARC record to prepare
# for load into Voyager.
sub add_local_fields {
  my ($marc_record, $accession, $barcode) = @_;

  # Add 099 field with accession number: 099 ## $a $accession
  my $fld099 = MARC::Field->new('099', ' ', ' ', 'a' => $accession);
  $marc_record->insert_fields_ordered($fld099);

  # Add 049 field: 049 ## $a CLUV $o muclsdsdr $p {SPAC} $l {barcode} 
  my $fld049 = MARC::Field->new('049', ' ', ' ', 
    'a' => 'CLUV',
	'o' => 'muclsdsdr',
	'p' => 'MEHER',
	'l' => $barcode
  );
  $marc_record->insert_fields_ordered($fld049);

  # Add 910 field: 910 ## $a meherbatch {date processed in YYMMDD format}
  my $fld910 = MARC::Field->new('910', ' ', ' ', 'a' => 'meherbatch ' . get_yymmdd());
  $marc_record->insert_fields_ordered($fld910);

  # Add 948 field: 948 ## $a cmc $b meherbatch $c [yyyymmdd] $d 1 
  # Note date in $c is yyyymmdd; prepend 20, won't care by 2100....
  my $fld948 = MARC::Field->new('948', ' ', ' ',
    'a' => 'cmc',
	'b' => 'meherbatch',
	'c' => '20' . get_yymmdd(),
	'd' => '1'
  );
  $marc_record->insert_fields_ordered($fld948);

  return $marc_record;

}

##############################
# Get today in YYMMDD format
sub get_yymmdd {
  my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time);
  $year-=100; # add 1900, subtract 2000, to get current 2-digit year for 2000-2099
  if ( $year <= 9 ) {
    $year = "0".$year;
  }
  $mon+=1;    # localtime gives $mon as 0..11
  if ( $mon <= 9 ) {
    $mon = "0".$mon;
  }
  if ( $mday <= 9 ) {
    $mday = "0".$mday;
  }
  return $year.$mon.$mday;
}

##############################
##############################
