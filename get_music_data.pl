#!/usr/bin/env perl

use Data::Dumper qw(Dumper);
use File::Slurp qw(read_file);
use JSON qw(decode_json);
use LWP::UserAgent;
use MARC::File::XML (BinaryEncoding => 'utf8', RecordFormat => 'MARC21');
use MARC::Batch;
use String::Similarity qw(similarity);
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
my $oclc_marc_file = $upc_file . '_oclc.mrc';
my $orig_marc_file = $upc_file . '_orig.mrc';

# Read search terms from file, one search per line.
my @lines = read_file($upc_file, chomp => 1);
# Each line has 4 fields: search term (UPC or music pub number), accession number, barcode, and title.
foreach my $line (@lines) {
  say "==============================";
  my ($search_term, $accession, $barcode, $official_title) = split("\t", $line);
  say "$accession: Searching for: $search_term ($official_title)";

  # First, search Discogs and MusicBrainz for the given term.
  # Among other data, collect music publisher number(s) from those sources.
  my %discogs_data = search_discogs($search_term);
  my %mb_data = search_musicbrainz($search_term);

  my @titles = ();
  push (@titles, $discogs_data{'title'}) if %discogs_data;
  push (@titles, $mb_data{'title'}) if %mb_data;
  push (@titles, $official_title);

  # First WorldCat search is by UPC, using standard number index
  my @marc_records = search_worldcat($search_term, 'srw.sn');

  # Remove unwanted records to see if we should proceed with a music pub number search
  @marc_records = remove_unsuitable_records(\@marc_records, \@titles);

  # If initial search on UPC didn't find anything, try searching for
  # the music publisher numbers from Discogs/MusicBrainz.
  if (! @marc_records) {
	my @search_terms = get_all_pub_numbers(\%discogs_data, \%mb_data);
	if (@search_terms) {
	  say "Searching WorldCat again for music publisher numbers... ", join(", ", @search_terms);
      @marc_records = search_worldcat(\@search_terms, 'srw.mn');
	}
  }

  # If ANY WorldCat record we found is held by CLU, reject the whole set
  # and exit this iteration: we don't want to add any dup, from any source.
  if (any_record_has_clu(\@marc_records)) {
    # Error message was printed in routine; add more info here
	say "ERROR: Pull CD for review: $accession";
	next;
  }

  # Make sure this is reset for every iteration
  my $marc_record; 
  $marc_record = evaluate_marc(\@marc_records, \@titles) if @marc_records;

  # If there's a MARC record now, use it
  if ($marc_record) {
	say "";
    say "\tBest record: " . $marc_record->oclc_number();
	report_marc_problems($marc_record);
	$marc_record = add_local_fields($marc_record, $accession, $barcode);

	save_marc($marc_record, $oclc_marc_file);

	# Output for title review
	say "";
    say "\tWC Title: ", $marc_record->title();

  } else {
    # Create basic MARC record from DC/MB data
	# Prefer Discogs: use it if available, else MusicBrainz
	if (%discogs_data) {
	  $marc_record = create_marc_discogs(%discogs_data);
	  $marc_record = add_local_fields($marc_record, $accession, $barcode);
	  save_marc($marc_record, $orig_marc_file);
	} elsif (%mb_data) {
	  $marc_record = create_marc_mb(%mb_data);
	  $marc_record = add_local_fields($marc_record, $accession, $barcode);
	  save_marc($marc_record, $orig_marc_file);
	}
	else {
	  say "MARC not created: no data available";
	  say "ERROR: Pull CD for review: $accession";
	}
  }

  # Print artists & titles for comparison
  say "\tDC Title: " . $discogs_data{'title'} . " / " . $discogs_data{'artist'} if %discogs_data;;
  say "\tMB Title: " . $mb_data{'title'} . " / " . $mb_data{'artist'} if %mb_data;
  say "\tOfficial: " . $official_title;
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
		# Store a reference to the whole original JSON as well, for later use
		$discogs_data{'json'} = $release_json;
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
      # Store a reference to the whole original JSON for this release as well, for later use
	  $mb_data{'json'} = $release;
	}
  }
  return %mb_data;
}

##############################
# Searches for UPC or music publisher/issue number
# using the OCLC WorldCat Search API.
# WorldCat API key included above.
sub search_worldcat {
  my ($search_terms_ref, $index) = @_;
  my $oclc = UCLA::Worldcat::WSAPI->new(WSKEY);
  $oclc->max_records(20);

  #my @marc_records = $oclc->search_sru_sn($search_terms_ref);
  my @marc_records = $oclc->search_sru($search_terms_ref, $index);
  say "Found MARC records: " . scalar(@marc_records);

  # Evaluate MARC records, rejecting unsuitable ones, returning the one best remaining one (or none if all get rejected)
  ####my $best_record = evaluate_marc(\@marc_records) if @marc_records;

  # TODO: Decide what you're really returning from here......
  ###return $best_record;
  return @marc_records;
}

##############################
# Return 1 (true) if any record in set is held by CLU, 0 (false) if not.
sub any_record_has_clu {
  my $marc_records_ref = shift; # array reference
  my $has_clu = 0; # false by default
  foreach my $marc_record (@$marc_records_ref) {
	if ($marc_record->held_by_clu()) {
	  say "\tREJECTING ALL RECORDS: OCLC " . $marc_record->oclc_number() . " is held by CLU";
	  say "\tWC Title: " . $marc_record->title();
	  $has_clu = 1; # true
	  last;
	}
  }
  return $has_clu;
}

##############################
# Evaluate MARC records, rejecting unsuitable ones, returning
# the best remaining one record (or none, if all are rejected).
sub evaluate_marc {
  my $marc_records = shift; # array reference
  my $titles_ref = shift; # array reference
  my $best_marc;

  # Have to de-reference arrays...
  @$marc_records = remove_unsuitable_records(\@$marc_records, $titles_ref);

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
  my $titles_ref = shift; # array reference
  my @keep_records = ();

  foreach my $marc_record (@$marc_records) {
    my $oclc_number = $marc_record->oclc_number();

	# Reject completely unsuitable records
	next if ! record_is_suitable($marc_record);

	# Reject if held by CLU
	# TODO: Remove this after testing
	#if ($marc_record->held_by_clu()) {
	#  say "\tREJECTED oclc $oclc_number - held by CLU";
	#  next;
	#}

	# Reject if MARC title is too different from Discogs/MusicBrainz title(s)
	next if title_differs_too_much($marc_record, $titles_ref);

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

  # Check 040 $b (language of cataloging), rejecting records with value other than 'eng'
  my $lang = $marc_record->field('040')->subfield('b');
  if ($lang && $lang ne 'eng') {
    say "\tREJECTED oclc $oclc_number - bad 040 \$b language: $lang";
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
# Compare MARC title with Discogs/MusicBrainz title(s).
# Return true if too different, beyond threshhold.
sub title_differs_too_much {
  my $marc_record = shift;
  my $titles_ref = shift;  # array reference
  my $too_different = 0; # false by default
  my $total_score = 0;
  my $marc_title = $marc_record->field('245')->as_string('anpb');
  my $oclc_number = $marc_record->oclc_number();

  # Convert array to hash to de-dup
  my %titles = map { $_ => 1 } @$titles_ref;
  foreach my $title (keys %titles) {
    my $score = similarity(normalize($marc_title), normalize($title));
	if ($score < 0.4) {
	  # Experiment: if full title is too different, maybe just 245 $a is closer?
	  my $short_title = $marc_record->field('245')->as_string('a');
	  if ($short_title ne $marc_title) {
	    $score = similarity(normalize($short_title), normalize($title));
	  }
	  if ($score < 0.4) {
	    $score = sprintf("%.2f", $score);
	    say "\tWarning: Titles are too different: $score";
	    say "\t\tMARC Title : $marc_title (OCLC $oclc_number)";
	    say "\t\tOther Title: $title";
	  }
	}
	$total_score += $score;
  }

  my $number_of_keys = scalar(keys %titles);
  if ($number_of_keys > 0) {
    my $average = $total_score / $number_of_keys;
	$average = sprintf("%.2f", $average);
    if ($average < 0.37) {
      say "\t\tREJECTED OCLC $oclc_number: Titles are too different: $average";
      $too_different = 1;
    } else {
      say "\tDEBUG: Average is: $average";
    }
  }

  return $too_different;
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

  # Create 005 timestamp for start of today
  my $f005_timestamp = '20' . get_yymmdd() . '000000.0';
  $marc_record->insert_fields_ordered(MARC::Field->new('005', $f005_timestamp));

  # Add 049 field: 049 ## $a CLUV $o muclsdsdr $p {SPAC} $l {barcode} 
  my $fld049 = MARC::Field->new('049', ' ', ' ', 
    'a' => 'CLUV',
	'o' => 'muclsdsdr',
	'p' => 'MEHER',
	'l' => $barcode
  );
  $marc_record->insert_fields_ordered($fld049);
  
  # Add 099 field with accession number: 099 ## $a $accession
  my $fld099 = MARC::Field->new('099', ' ', ' ', 'a' => $accession);
  $marc_record->insert_fields_ordered($fld099);

  # Add 910 field: 910 ## $a meherbatch {date processed in YYMMDD format}
  my $fld910 = MARC::Field->new('910', ' ', ' ', 'a' => 'meherbatch ' . get_yymmdd());
  $marc_record->insert_fields_ordered($fld910);

  # Add 948 field: 
  # From OCLC: 948 ## $a cmc $b meherbatch $c [yyyymmdd] $d 1 $k batchcat 
  # Original : 948 ## $a cmc $b meherbatch $c [yyyymmdd] $d 3 $k meherbatch $k batchcat
  # Note date in $c is yyyymmdd; prepend 20, won't care by 2100....
  my $fld948 = MARC::Field->new('948', ' ', ' ',
    'a' => 'cmc',
	'b' => 'meherbatch',
	'c' => '20' . get_yymmdd()
  );
  # Check 001 to decide if OCLC record, via hacky 001 added in create_marc_shared();
  # Add $k batchcat to all, along with meherorig in original records.
  if ($marc_record->field('001')->data() =~ /ocm00000NEW/) {
    $fld948->add_subfields('d' => '3', 'k' => 'meherorig', 'k' => 'batchcat');
  } else {
    $fld948->add_subfields('d' => '1', 'k' => 'batchcat');
  }

  $marc_record->insert_fields_ordered($fld948);

  return $marc_record;

}

##############################
# Create MARC records with data common to both Discogs and MusicBrainz
sub create_marc_shared {
  my $marc = MARC::Record->new();
  $marc->encoding('UTF-8');
  $marc->leader('00000njm a22003373i 4500');
  # TODO: Placeholder 001 field
  $marc->append_fields(MARC::Field->new('001', 'ocm00000NEW'));
  # Create 005 timestamp for start of today
  my $f005_timestamp = '20' . get_yymmdd() . '000000.0';
  $marc->append_fields(MARC::Field->new('005', $f005_timestamp));
  $marc->append_fields(MARC::Field->new('007', 'sd fungnn|||eu'));
  $marc->append_fields(MARC::Field->new('008', get_yymmdd() . 's        xx   nn           n zxx d'));

  # 040 field
  $marc->append_fields(MARC::Field->new('040', ' ', ' ',
    'a' => 'CLU',
	'b' => 'eng',
	'c' => 'CLU'
  ));

  # 3xx fields
  $marc->append_fields(MARC::Field->new('336', ' ', ' ',
    'a' => 'performed music',
	'b' => 'prm',
	'2' => 'rdacontent'
  ));
  $marc->append_fields(MARC::Field->new('337', ' ', ' ',
    'a' => 'audio',
	'b' => 's',
	'2' => 'rdamedia'
  ));
  $marc->append_fields(MARC::Field->new('338', ' ', ' ',
    'a' => 'audio disc',
	'b' => 'sd',
	'2' => 'rdacarrier'
  ));
  $marc->append_fields(MARC::Field->new('344', ' ', ' ',
    'a' => 'digital',
	'b' => 'optical',
	'2' => 'rda'
  ));
  $marc->append_fields(MARC::Field->new('347', ' ', ' ',
    'a' => 'audio file',
	'b' => 'CD audio',
	'2' => 'rda'
  ));

  return $marc;
}

##############################
# Create MARC record from Discogs data
sub create_marc_discogs {
  my %data = @_;
  say "Creating MARC from Discogs data for: ", $data{'title'};
  my $full_data = $data{'json'};
  my $marc = create_marc_shared();

  # Update 008
  my $fld008 = $marc->field('008');
  my $fld008_data = $fld008->data();
  # If date, set 008/07-10; otherwise, set 008/06 and 008/07-14
  if ($full_data->{'released'}) {
    substr($fld008_data, 7, 4) = substr($full_data->{'released'}, 0, 4);
  } else {
    substr($fld008_data, 6, 9) = 'nuuuuuuuu';
  }
  # Set language - always unknown from Discogs
  substr($fld008_data, 35, 3) = 'zxx';
  $fld008->update($fld008_data);

  # Generic MARC field variable for frequent reuse below
  my $fld;

  # Create 024, if possible
  foreach my $id (@{$full_data->{'identifiers'}}) {
    # Only create fields for things called barcodes
	if ($id->{'type'} eq 'Barcode') {
	  $marc->insert_fields_ordered(MARC::Field->new('024', '8', ' ', 'a' => $id->{'value'}));
	}
  }

  # Create 028, if possible
  my %catnos;
  foreach my $label (@{$full_data->{'labels'}}) {
    # Discogs uses literal 'none' when no value for catno
	my $catno = $label->{'catno'};
	my $name = $label->{'name'};
	if ($catno && $catno ne 'none') {
	  # De-dup on catno, via hash; name might not exist
	  $catnos{normalize($catno)} = [$catno, $name];
	}
  }
  # Now go through the hash, creating an 028 for each one remaining
  foreach my $catno (keys %catnos) {
    $fld = MARC::Field->new('028', '0', '2', 'a' => $catnos{$catno}[0]);
    $fld->add_subfields('b', $catnos{$catno}[1]) if $catnos{$catno};
    $marc->insert_fields_ordered($fld);
  }

  # Create 245
  my $title = $full_data->{'title'};
  my $artist = $full_data->{'artists'}->[0]->{'name'} if $full_data->{'artists'}->[0]->{'name'};
  my $ind2 = get_filing_indicator($title);
  if ($artist) {
    $title .= ' /';
	$artist .= '.';
    $fld = MARC::Field->new('245', '0', $ind2, 'a' => $title, 'c' => $artist);
  } else {
    $title .= '.';
    $fld = MARC::Field->new('245', '0', $ind2, 'a' => $title);
  }
  $marc->insert_fields_ordered($fld);

  # Create 264
  $fld = MARC::Field->new('264', ' ', '1', 'a' => '[Place of publication not identified] :');
  my $publisher = $full_data->{'labels'}->[0]->{'name'};
  if ($publisher) {
    $fld->add_subfields('b' => $publisher . ',');
  } else {
    $fld->add_subfields('b' => '[publisher not identified],');
  }
  my $year = substr($full_data->{'released'}, 0, 4) if $full_data->{'released'};
  if ($year) {
    $fld->add_subfields('c' => "[$year]");
  } else {
    $fld->add_subfields('c' => '[date of publication not identified]');
  }
  $marc->insert_fields_ordered($fld);

  # Create 300
  my $quantity = $full_data->{'formats'}->[0]->{'qty'} if $full_data->{'formats'}->[0]->{'qty'};
  $quantity = 1 if not $quantity || $quantity == 0;
  my $discs = $quantity > 1 ? 'discs' : 'disc';
  $fld = MARC::Field->new('300', ' ', ' ',
    'a' => "$quantity audio $discs :",
	'b' => 'digital ;',
	'c' => '4 3/4 in.'
  );
  $marc->insert_fields_ordered($fld);

  # Create 500
  $marc->insert_fields_ordered(MARC::Field->new('500', ' ', ' ', 'a' => 'Title from Discogs database.'));
  
  # Create 505, if possible
  my $tracks_combined = '';
  foreach my $track (@{$full_data->{'tracklist'}}) {
    # Add separator if needed
    $tracks_combined .= ' -- ' if $tracks_combined;
	$tracks_combined .= $track->{'title'};
  }
  # Add a period to the end
  $tracks_combined .= '.';
  $marc->insert_fields_ordered(MARC::Field->new('505', '0', ' ', 'a' => $tracks_combined));

  # Create 653(s), if possible
  foreach my $genre (@{$full_data->{'genres'}}) {
    $marc->insert_fields_ordered(MARC::Field->new('653', ' ', '6', 'a' => $genre));
  }

  # Create 720, if possible
  $marc->insert_fields_ordered(MARC::Field->new('720', ' ', ' ', 'a' => $full_data->{'artists_sort'} . '.')) if $full_data->{'artists_sort'};

  return $marc;
}

##############################
# Create MARC record from MusicBrainz data
sub create_marc_mb {
  my %data = @_;
  say "Creating MARC from MusicBrainz data for: ", $data{'title'};
  my $full_data = $data{'json'};
  my $marc = create_marc_shared();

  # Update 008
  my $fld008 = $marc->field('008');
  my $fld008_data = $fld008->data();
  # If date, set 008/07-10; otherwise, set 008/06 and 008/07-14
  if ($full_data->{'date'}) {
    substr($fld008_data, 7, 4) = substr($full_data->{'date'}, 0, 4);
  } else {
    substr($fld008_data, 6, 9) = 'nuuuuuuuu';
  }
  # Get language - only if it's English
  my $lang = $full_data->{'text-representation'}->{'language'} if $full_data->{'text-representation'}->{'language'};
  substr($fld008_data, 35, 3) = 'eng' if $lang eq 'eng';
  $fld008->update($fld008_data);

  # Generic MARC field variable for frequent reuse below
  my $fld;

  # Create 024, if possible
  $marc->insert_fields_ordered(MARC::Field->new('024', '8', ' ', 'a' => $full_data->{'barcode'})) if $full_data->{'barcode'};

  # Create 028, if possible
  my %catnos;
  foreach my $label (@{$full_data->{'label-info'}}) {
	my $catno = $label->{'catalog-number'};
	my $name = $label->{'label'}->{'name'};
	if ($catno) {
	  # De-dup on catno, via hash; name might not exist
	  $catnos{normalize($catno)} = [$catno, $name];
	}
  }
  # Now go through the hash, creating an 028 for each one remaining
  foreach my $catno (keys %catnos) {
	$fld = MARC::Field->new('028', '0', '2', 'a' => $catnos{$catno}[0]);
	$fld->add_subfields('b', $catnos{$catno}[1]) if $catnos{$catno};
    $marc->insert_fields_ordered($fld);
  }

  # Create 245
  my $title = $full_data->{'title'};
  my $artist = $full_data->{'artist-credit'}->[0]->{'artist'}->{'name'} if $full_data->{'artist-credit'}->[0]->{'artist'}->{'name'};
  my $ind2 = get_filing_indicator($title);
  if ($artist) {
    $title .= ' /';
	$artist .= '.';
    $fld = MARC::Field->new('245', '0', $ind2, 'a' => $title, 'c' => $artist);
  } else {
    $title .= '.';
    $fld = MARC::Field->new('245', '0', $ind2, 'a' => $title);
  }
  $marc->insert_fields_ordered($fld);

  # Create 264
  $fld = MARC::Field->new('264', ' ', '1', 'a' => '[Place of publication not identified] :');
  my $publisher = $full_data->{'label-info'}->[0]->{'label'}->{'name'};
  if ($publisher) {
    $fld->add_subfields('b' => $publisher . ',');
  } else {
    $fld->add_subfields('b' => '[publisher not identified],');
  }
  my $year = substr($full_data->{'date'}, 0, 4) if $full_data->{'date'};
  if ($year) {
    $fld->add_subfields('c' => "[$year]");
  } else {
    $fld->add_subfields('c' => '[date of publication not identified]');
  }
  $marc->insert_fields_ordered($fld);

  # Create 300
  my $quantity = $full_data->{'media'}->[0]->{'disc-count'} if $full_data->{'media'}->[0]->{'disc-count'};
  $quantity = 1 if (not $quantity or $quantity == 0);
  my $discs = $quantity > 1 ? 'discs' : 'disc';
  $fld = MARC::Field->new('300', ' ', ' ',
    'a' => "$quantity audio $discs :",
	'b' => 'digital ;',
	'c' => '4 3/4 in.'
  );
  $marc->insert_fields_ordered($fld);

  # Create 500
  $marc->insert_fields_ordered(MARC::Field->new('500', ' ', ' ', 'a' => 'Title from MusicBrainz database.'));

  # No tracklist data to create 505?

  # Create 653(s), if possible
  foreach my $genre (@{$full_data->{'tags'}}) {
    $marc->insert_fields_ordered(MARC::Field->new('653', ' ', '6', 'a' => $genre->{'name'}));
  }

  # Create 720, if possible
  $marc->insert_fields_ordered(MARC::Field->new('720', ' ', ' ', 'a' => $full_data->{'artist-credit'}->[0]->{'artist'}->{'sort-name'} . '.'))
    if $full_data->{'artist-credit'}->[0]->{'artist'}->{'sort-name'};

  return $marc;
}

##############################
# Save MARC record to given file, as binary MARC
sub save_marc {
  my ($marc_record, $marc_file) = @_;
  open MARC, '>>:utf8', $marc_file;
  print MARC $marc_record->as_usmarc();
  close MARC;
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
# Normalize strings for comparison:
# remove spaces and punctuation, then
# force string to upper-case.
sub normalize {
  my $string = shift;
#say "IN : $string";
  $string =~ s/[[:punct:]]//g;
  $string =~ s/[[:space:]]//g;
  $string = uc($string);
#say "OUT: $string";
  return $string;
}

##############################
# Get filing indicator for title, for use in MARC record.
sub get_filing_indicator {
  my $title = shift;
  # Default is 0; set other values based on start of title.
  my $ind2 = '0';
  $ind2 = '2' if $title =~ /^A /;
  $ind2 = '3' if $title =~ /^An /;
  $ind2 = '4' if $title =~ /^The /;
  return $ind2;
}

##############################
# Get all publisher/catalog numbers from Discogs and MusicBrainz JSON data.
sub get_all_pub_numbers {
  my ($dc_data_ref, $mb_data_ref) = @_; # 2 hash refs
  my $dc_json = $dc_data_ref->{'json'};
  my $mb_json = $mb_data_ref->{'json'};

  # Use a hash to automatically dedup; we care only about keys, so all values will be 1.
  my %pub_numbers;

  # Discogs data
  foreach my $label (@{$dc_json->{'labels'}}) {
    # Discogs uses literal 'none' when no value for catno
	my $pub_num = $label->{'catno'};
	$pub_numbers{normalize_pub_num($pub_num)} = 1 if ($pub_num && $pub_num ne 'none');
  }

  # MusicBrainz data
  foreach my $label (@{$mb_json->{'label-info'}}) {
    my $pub_num = $label->{'catalog-number'};
    $pub_numbers{normalize_pub_num($pub_num)} = 1 if $pub_num;
  }

  # Return just the keys - the unique pub numbers
  return (keys %pub_numbers);
}

##############################
##############################
