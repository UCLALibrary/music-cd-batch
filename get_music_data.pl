#!/usr/bin/env perl

use Data::Dumper qw(Dumper);
use File::Slurp qw(read_file);
use JSON qw(decode_json);
#use LWP::Simple qw(get);
use LWP::UserAgent;
use MARC::File::XML (BinaryEncoding => 'utf8', RecordFormat => 'MARC21');
use MARC::Batch;
use feature qw(say);
use strict;
use warnings;
use utf8;

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

# Read search terms from file, one search per line
my @search_terms = read_file($upc_file, chomp => 1);
foreach my $search_term (@search_terms) {
  say "==============================";
  say $search_term;
  SearchWorldcat($search_term);
  #SearchDiscogs($search_term);
  #SearchMusicbrainz($search_term);
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

	say "Title : ", $json->{'title'};
	say "Artist: ", $json->{'artists_sort'};
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
  say "Title : ", $release->{'title'} if $release;
  say "Artist: ", $release->{'artist-credit'}->[0]->{'artist'}->{'name'} if $release;
  say "";
}

##############################
# Searches for UPC or music publisher/issue number
# using the OCLC WorldCat Search API.
sub SearchWorldcat {
  my $search_term = shift;
  # WorldCat API key included above.

  # Use WorldCat Standard Number (sn) index
  my $wc_url = 'http://www.worldcat.org/webservices/catalog/content/sn/';
  $wc_url .= "$search_term?servicelevel=full&frbrGrouping=off&wskey=" . WSKEY;
#say $wc_url;
# TODO: HACK to test multi-record XML
###$wc_url = "http://www.worldcat.org/webservices/catalog/search/sru?query=srw.ti=frisbees+and+srw.pl=york&wskey=omquRXhy1nxKQQWeoTjFxEwuHJQmioU0M0kit62O8t41QAL0wNNwYlWrxO8sDA3qTCU21q2siMclOD4r&servicelevel=full&frbrGrouping=off";
###$wc_url = "http://www.worldcat.org/webservices/catalog/search/sru?query=srw.ti=cupboards+and+srw.pl=durham&wskey=omquRXhy1nxKQQWeoTjFxEwuHJQmioU0M0kit62O8t41QAL0wNNwYlWrxO8sDA3qTCU21q2siMclOD4r&servicelevel=full&frbrGrouping=off";

  # Call the API and store the result in XML
  # TODO: Check response for more info?
  my $contents = $browser->get($wc_url)->decoded_content;
  utf8::encode($contents);
#say $contents;

  # TODO: Evaluate MARC record(s) and save the best 1 for each search
  # For now, just convert to binary MARC21
  # API could return multiple records so must iterate over them.
  # MARC library expects to read from filehandles, not variables...

  ### Having several problems with MARCXML from OCLC when there are multiple records...
  ### Maybe work around these by grabbing OCLC# directly from XML and fetching records directly?
  ### <controlfield tag="001">910604789</controlfield>
  my $pattern = '<controlfield tag="001">([0-9]{1,10})</controlfield>';
  my @oclc_numbers = ($contents =~ /$pattern/g);
  foreach my $oclc_number (@oclc_numbers) {
    say $oclc_number;
	my $marc = GetMARC($oclc_number);
	say "Title : ", $marc->subfield('245', 'a');
	say "Artist: ", $marc->subfield('245', 'c');

	my ($held_by_clu, $number_of_holdings) = GetHoldings($oclc_number);
	say "Count : ", $number_of_holdings;
	say "CLU?  : ", $held_by_clu;
    say "";
  }
  
#  open MARC, '>>:utf8', $marc_file;
#  print MARC $marc->as_usmarc();
#  close MARC;

}

##############################
# Retrieve individual MARCXML record from OCLC and convert to MARC
sub GetMARC {
  my $oclc_number = shift;
  # WorldCat API key included above
  my $wc_url = 'http://www.worldcat.org/webservices/catalog/content/';
  $wc_url .= "$oclc_number?servicelevel=full&wskey=" . WSKEY;
  my $contents = $browser->get($wc_url)->decoded_content;
  utf8::encode($contents);

  #open( my $xml_fh, '<', \$contents ) or die "Couldn't open file handle: $! / $^E";
  my $marc = MARC::Record->new_from_xml($contents, 'UTF-8');
  return $marc;
}

##############################
# Evaluate MARC record
sub EvaluateMARC {
}

##############################
# Call OCLC Locations API to get number of holdings and
# whether CLU (UCLA) holds the record, by OCLC number.
sub GetHoldings {
  my $oclc_number = shift;
  my $held_by_clu = 'NO';
  my $number_of_holdings = 0;

  # WorldCat API key included above.
  my $wc_url = 'http://www.worldcat.org/webservices/catalog/content/libraries/';
  $wc_url .= "$oclc_number?format=json&frbrGrouping=off&servicelevel=full&location=90095&wskey=" . WSKEY;

  my $contents = $browser->get($wc_url)->decoded_content;
  utf8::encode($contents);
  # Data in JSON, not XML
  my $json = decode_json($contents);
  # Bail out if this OCLC number has no holdings
  if ($json->{'diagnostics'}) {
    return ($held_by_clu, $number_of_holdings);
  }

  $number_of_holdings = $json->{'totalLibCount'};
  my @libraries = @{$json->{'library'}};
  foreach my $library (@libraries) {
#	say $library->{'oclcSymbol'};
    if ($library->{'oclcSymbol'} eq 'CLU') {
	  $held_by_clu = 'YES'; # clearer than perl's lack of true/false...
	  last;
	};
  }

  return ($held_by_clu, $number_of_holdings);
}



