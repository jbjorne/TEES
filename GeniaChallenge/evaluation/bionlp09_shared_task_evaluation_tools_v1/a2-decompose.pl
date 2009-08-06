#!/usr/bin/perl
require 5.000;
use strict;

# default task specification

my  $opt_string = 'hv';

use Getopt::Std;
our %opt;
getopts("$opt_string", \%opt) or usage();
usage() if $opt{h};
usage() if $#ARGV < 0;


foreach my $fname (@ARGV) {
    if ($fname !~ /([1-9][0-9]*)\.a2\.t12?3?$/) {print STDERR "invalid file suffix: $fname\n"; next}
    my $pmid = $1;

    # storage for annotations
    my @tanno = ();  # text annotation
    my %eanno = ();  # event annotation
    my %split = ();  # splitted annotation information

    # read annotation file
    open (FILE, "<", $fname) or print STDERR "cannot open the file: $fname\n";
    while (<FILE>) {
	chomp;
	if ($_ eq '') {next}

	# text-bound annotation
	if (/^[T*]/) {
	    # store the line as it is.
	    push @tanno, $_;
	} # if

	# event expression annotation
	elsif (/^E/) {
	    my ($eid, $exp) = split "\t";
	    my (@arg) = split ' ', $exp;
	    my ($etype, $tid) = split ':', shift @arg;

	    if ($#arg > 0) {
		# decompose and store
		for (my $i=0; $i<=$#arg; $i++) {
		    my ($atype, $aid) = split (':', $arg[$i]);
		    $atype =~ s/([a-zA-Z])[0-9]+$/$1/;
		    $eanno{"$eid-$i"} = [$etype, $tid, $atype, $aid];
		} # for
		$split{$eid} = $#arg + 1;
	    } # if
	    else {
		my ($atype, $aid) = split (':', $arg[$0]);
		$atype =~ s/([a-zA-Z])[0-9]+$/$1/;
		$eanno{$eid} = [$etype, $tid, $atype, $aid];
	    } # else
	} # elsif

	elsif (/^M/) {
	    my ($mid, $mtype, $aid) = split /[ \t]/;
	    $eanno{$mid} = [$mtype, 'NULL', 'Theme', $aid];
	} # elsif

	else {
	    print STDERR "undefined type of annotation ID: $_\n";
	} # else
    } # foreach
    close (FILE);


    ## sort events
    my @elist = ();
    my %remain = ();
    foreach (keys %eanno) {$remain{$_} = 1}

    while (%remain) {
	my $changep = 0;
	my %remain_s = ();
	foreach my $eid (keys %remain) {$eid =~ s/-[0-9]+$//; $remain_s{$eid} = 1}

	foreach my $eid (keys %remain) {
	    my $aid = ${$eanno{$eid}}[3];
	    if (($aid =~ /^E/) && $remain_s{$aid}) {}
	    else {
		push @elist, $eid;
		delete $remain{$eid};
		$changep = 1
	    } # else
	} # foreach
	if (!$changep) {
	    if ($opt{v}) {print STDERR "circular reference: [$pmid]\n"; foreach (keys %remain) {printevent($_)}; print STDERR "=====\n"}
	    push @elist, keys %remain;
	    %remain = ();
	} # if
    } # while

#    sub printevent {
#	my ($eid) = @_;
#	my ($etype, $tid, $atype, $aid) = @{$eanno{$eid}};
#	print "$eid\t$etype:$tid $atype:$aid\n";
#    }

#    foreach (@elist) {
#	print STDERR "$_\t", join (", ", @{$eanno{$_}}), "\n";
#    }
#    print STDERR "===\n";


    ## transitive duplication
    my @nelist = ();
    foreach my $eid (@elist) {
	my ($etype, $tid, $atype, $aid) = @{$eanno{$eid}};
	if ($split{$aid}) {
	    my $i = 0;
	    foreach my $naid (&expand_aid($aid, \%split)) {
		$eanno{"$eid-$i"} = [$etype, $tid, $atype, $naid];
		push @nelist, "$eid-$i";
		$i++;
	    } # foreach
	    delete $eanno{$eid};
	    $split{$eid} = $i; #print STDERR "$eid\t$i===\n";
	} # if
	else {push @nelist, "$eid"}
    } # foreach

#    foreach (@nelist) {
#	print STDERR "$_\t", join (", ", @{$eanno{$_}}), "\n";
#    } # foreach
#    print STDERR "===\n";

    # remove duplicates
    @elist = @nelist;
    @nelist = ();
    my %eventexp = (); # for checking of event duplication
    my %equiv =();
    foreach my $eid (@elist) {
	my ($etype, $tid, $atype, $aid) = @{$eanno{$eid}};
	if ($equiv{$aid}) {${$eanno{$eid}}[3] = $equiv{$aid}}
	my $eventexp = join ', ', @{$eanno{$eid}};

	# check duplication
	if (my $did = $eventexp{$eventexp}) {
	    delete $eanno{$eid};
	    $equiv{$eid} = $did; #print STDERR "EQUIV $eid\t==> $equiv{$eid}\n";
	    if ($opt{v}) {print STDERR "[$pmid] $eid is equivalent to $did => removed.\n"}
	} # if
	else {$eventexp{$eventexp} = $eid; push @nelist, $eid}
    } # foreach


#    foreach (@nelist) {
#	print STDERR "$_\t", join (", ", @{$eanno{$_}}), "\n";
#   } # foreach
#    print STDERR "===\n";

    # remove less meaningful regulation chains
    @elist  = @nelist;
    @nelist = ();
    foreach my $eid (@elist) {
	my ($etype, $tid, $atype, $aid) = @{$eanno{$eid}};
	if ($aid =~ /^E[0-9]/) {
	    if ($eanno{$aid} && (${$eanno{$aid}}[2] eq 'Theme')) {push @nelist, $eid}
	    else                                                 {delete $eanno{$eid}}
	} # if

	else {push @nelist, $eid}
    } # foreach

#    foreach (@nelist) {
#	print STDERR "$_\t", join (", ", @{$eanno{$_}}), "\n";
#    }
#    print STDERR "===\n";


    @elist  = @nelist;
    @nelist = sort {$a cmp $b} @elist;


    # output
    open (FILE, ">", "${fname}d") or print STDERR "cannot open the file: ${fname}d\n";

    foreach (@tanno) {print FILE "$_\n"}

    foreach my $eid (@nelist) {
	my ($etype, $tid, $atype, $aid) = @{$eanno{$eid}};
	if    ($eid =~ /^E/) {print FILE "$eid\t$etype:$tid $atype:$aid\n"}
	elsif ($eid =~ /^M/) {print FILE "$eid\t$etype $aid\n"}
    } # foreach

    close (FILE);
} # foreach


sub expand_aid {
    my ($aid, $rh_split) = @_;
    my @naid = ();

    if ($rh_split->{$aid}) {
#	print STDERR "$aid\t$rh_split->{$aid}\n";
	for (my $i = 0; $i < $rh_split->{$aid}; $i++) {
	    push (@naid, &expand_aid("$aid-$i", $rh_split));
	} # for
#	print STDERR "==> ", join (", ", @naid), "\n";
	return @naid;
    } # if
    else {return $aid}
} # expand_aid


sub usage {
    print STDERR << "EOF";

[a2-decompose] last updated by jdkim\@is.s.u-tokyo.ac.jp on 3 July, 2009.


<DESCRIPTION>
It is a part of the BioNLP'09 Shared Task evaluation software.
It reads a2 file(s) and produces corresponding files with events decomposed into predicate-argument pairs.
Note that it generates the resulting files with the suffix 'd'.


<USAGE>
$0 [-$opt_string] a2_file(s)

* The a2_file has to have one of the valid suffixes (.a2.t1, .a2.t12, .a2.t13, or .a2.t123).


<OPTIONS>
-h     show help (this) page.
-v     verbose


EOF
      exit;
} # usage
