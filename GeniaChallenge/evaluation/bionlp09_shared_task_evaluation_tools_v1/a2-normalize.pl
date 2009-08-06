#!/usr/bin/perl
require 5.000;
use strict;

my %target_eclass = (
		     ('Gene_expression', 1),
		     ('Transcription', 1),
		     ('Protein_catabolism', 1),
		     ('Phosphorylation', 1),
		     ('Localization', 1),
		     ('Binding', 1),
		     ('Regulation', 1),
		     ('Positive_regulation', 1),
		     ('Negative_regulation',1 )
		     );

my $gDir = '.';
my $oDir = '';

my  $opt_string = 'heg:o:uv';
our %opt;
 

use Getopt::Std;
getopts("$opt_string", \%opt) or &usage;
usage() if $opt{h};
usage() if $#ARGV < 0;
if ($opt{g}) {$gDir = $opt{g}; $gDir =~ s/\/$//}

if ($opt{u} && $opt{o}) {usage()}
if (!$opt{u} && !$opt{o}) {usage()}

if ($opt{o}) {$oDir = $opt{o}}


# per-text variables referenced globally. Should be initialzed for each file.
my ($text, $textlen);

my (@panno, @tanno, @eanno, @manno);  # annotations
my (%panno, %tanno, %eanno, %manno);  # annotations
my @equiv; # list equivalent groups


my ($pmid, $suffix) = ('', '');
foreach my $fname (@ARGV) {
    if ($fname =~ /([1-9][0-9]*)(\.a2\.t12?3?|\.a2)$/) {$pmid = $1; $suffix = $2}
    else {print STDERR "unrecognized filename : $fname\n"; next}

    # initialize per-text variables
    $text = '';
    @panno = @tanno= @eanno = @manno = ();
    %panno = %tanno= %eanno = %manno = @equiv = ();

    &read_text_file("$gDir/$pmid.txt");
    &read_a1_file("$gDir/$pmid.a1");
    &read_a2_file($fname);

    foreach my $eid (@eanno) {
	my ($etype, $etid, @arg) = @{$eanno{$eid}};

	## id-linkage verification

	if (!$tanno{$etid}) {print STDERR "invalid reference to event trigger: [$pmid] $eid => $etid\n"; next}
	if (${$tanno{$etid}}[0] ne $etype) {print STDERR "event type mismatch: [$pmid] $eid => $etype vs ${$tanno{$etid}}[0]\n"; next}

	foreach (@arg) {
	    my ($atype, $aid) = split /:/;

	    if (($aid =~ /^T/) && !$panno{$aid} && !$tanno{$aid}) {print STDERR "unkown reference: [$pmid] $eid => $aid\n"}
	    if (($aid =~ /^E/) && !$eanno{$aid}) {print STDERR "unkown reference: [$pmid] $eid => $aid\n"}
	    if ($aid eq $eid) {print STDERR "self-reference: [$pmid] $eid => $aid\n"; next}

	    if (($atype =~ /^Theme/) || ($atype eq 'Cause')) {
		if ($etype =~ /egulation$/) {
		    if (!$panno{$aid} && !$eanno{$aid}) {print STDERR "Only a protein or a event can be a Theme or a Cause for a regulation event: [$pmid] $eid => $atype:$aid\n"}
		} # if
		else {
		    if (!$panno{$aid}) {print STDERR "Only a protein can be a Theme for a non-regulation event: [$pmid] $eid => $atype:$aid\n"}
		} # else
	    } # if

	    else {
		if (!$tanno{$aid} || (${$tanno{$aid}}[0] ne 'Entity')) {print STDERR "A secondary argument has to reference to a 'Entity' type t-entity: [$pmid] $eid => $atype:$aid\n"}
	    } # else
	} # foreach


	# canonicalize the order of arguments
	my %argorder = (('Theme', 0), ('Theme1', 1), ('Theme2', 2), ('Theme3', 3), ('Theme4', 4), ('Theme5', 5), ('Theme6', 6), ('Cause', 7),
			('Site', 10), ('Site1', 11), ('Site2', 12), ('Site3', 13), ('Site4', 14), ('Site5', 15), ('Site6', 16), ('CSite', 17), ('AtLoc', 18), ('ToLoc', 19));
	@arg = sort {$argorder{(split /:/, $a)[0]} <=> $argorder{(split /:/, $b)[0]}} @arg;


	# canonicalize the order of multiple themes for binding events
	if ($etype eq 'Binding') {
	    my (%theme, %site) = ();

	    foreach (@arg) {
		my ($atype, $aid) = split /:/;
		$aid =~ s/^T//;

		if ($atype =~ /^Theme([2-5]?)/) {
		    my $i = ($1)? $1:1;
		    if ($theme{$i}) {
			if ($suffix =~ /t12/) {print STDERR "duplicate theme numbering: [$pmid] $eid => $atype\n"}
			else                  {while ($theme{$i}) {$i++}}
		    } # if
		    $theme{$i} = $aid;
		} # if
		if ($atype =~ /^Site([2-5]?)/)  {
		    my $i = ($1)? $1:1;
		    if ($site{$i}) {print STDERR "duplicate site numbering: [$pmid] $eid => $atype\n"}
		    else           {$site{$i} = $aid}
		    $theme{$i} .= '-' . $aid;
		} # if
	    } # foreach

	    my @theme = sort {(split /-/, $theme{$a})[0] <=> (split /-/, $theme{$b})[0]} keys %theme;

	    my (@newtheme, @newsite) = ();
	    for (my $i = 0; $i <= $#theme; $i++) {
		my ($t , $s) = split /-/, $theme{$theme[$i]};
		my $j = $i? $i+1 : '';
		push @newtheme, "Theme$j:T" . $t;
		if ($s) {push @newsite, "Site$j:T" . $s}
	    } # for

	    @arg = (@newtheme, @newsite);
	} # if

	$eanno{$eid} = ["$etype:$etid", @arg];
    } # foreach (%eanno)


    # id-linkage verification
    foreach my $mid (@manno) {
	my ($mod, $aid) = @{$manno{$mid}};
	if (($aid !~ /^E/) || (!$eanno{$aid})) {
	    print STDERR "invalid ID reference: [$pmid] $mid: $aid?\n";
	} # if
    } # foreach (%manno)


    # id-linkage verification
    foreach (@equiv) {
	my @egroup = @$_;
	foreach (@egroup) {
	    if (!$panno{$_}) {print STDERR "non-protein entity in Equiv relation: $pmid\t[", join (",", @egroup), "]\n"}
	} # foreach
    } # foreach


    # count the number of events referencing each term
    my %nref = ();
    foreach my $eid (@eanno) {
	my @aid = map {(split ':')[1]} @{$eanno{$eid}};
	foreach (@aid) {if ($nref{$_}) {$nref{$_}++} else {$nref{$_}=1}}
    } # foreach


    # find the referenced one and put it in the first place.
    foreach (@equiv) {
	my @egroup = @$_;

	my ($rterm, @others) = ();
	my $num_rterm = 0;
	foreach (@egroup) {
	    if ($nref{$_}) {$rterm = $_; $num_rterm++}
	    else           {push @others, $_}
	}
	if ($num_rterm > 1) {print STDERR "multiple terms in a equiv group are referenced: $pmid\t[", join (",", @egroup), "]\n"}

	if ($rterm) {$_ = [$rterm, @others]}
    } # foreach

    # check duplication
    my %seen = ();
    foreach my $id (@tanno, @eanno, @manno) {
	my $anno = ($id =~ /^T/)? $tanno{$id} : (($id =~ /^E/)? $eanno{$id} : $manno{$id});
	my $exp  = join ' ', @{$anno};
	if ($seen{$exp}) {print STDERR "duplicate events: [$pmid] $id = $seen{$exp}\n"}
	else             {$seen{$exp} = $id}
    } # for ($i)



    my $newfname = $fname;

    if ($oDir) {
	if (!-e $oDir) {mkdir $oDir or die " !Cannot create the directory for output, $oDir.\n"}

	$newfname =~ s/^.*\///;
	$newfname = "$oDir/$newfname";
	if ($opt{v}) {print STDERR "$fname\t-> $newfname.\n"}
    } # if
    elsif ($opt{u}) {
	-w $newfname or die " !The target file is not writable.\n";
	if ($opt{v}) {print STDERR "update $newfname.\n"}
    } # elsif

    if (!open (FILE, ">", $newfname)) {print STDERR "cannot open output file: $newfname\n"; return}

    foreach (@equiv) {print FILE "*\tEquiv ", join (' ', @$_), "\n"}
    foreach my $id (@tanno) {print FILE "$id\t", join (' ', @{$tanno{$id}}[0 .. 2]); if (${$tanno{$id}}[3]) {print FILE "\t${$tanno{$id}}[3]"} print FILE "\n"}
    foreach my $id (@eanno) {print FILE "$id\t", join (' ', @{$eanno{$id}}), "\n"}
    foreach my $id (@manno) {print FILE "$id\t", join (' ', @{$manno{$id}}), "\n"}
    close (FILE);
} # foreach


sub read_text_file {
    my ($fname) = @_;

    if (!open (FILE, "<", "$fname")) {print STDERR "cannot open txt file: $fname\n"; exit}
    while (<FILE>) {$text .= $_}
    close (FILE);

    $textlen = length $text;
} # read_text_file


# t-entity : (type, beg, end)
# event    : (type, tid, arg1, arg2, ...)

sub read_a1_file {
    my ($fname) = @_;

    if (!open (FILE, "<", $fname)) {print STDERR "cannot open a1 file: $fname\n"; exit}

    while (<FILE>) {
	chomp;
	my ($id, $anno, $extra) = split /\t/;
	if ($id !~ /^T[0-9-]+$/) {print STDERR "invalid ID in a1 file: [$pmid] $_\n"; next}

	my ($type, $beg, $end) = split / /, $anno;
	if ($type ne 'Protein')   {print STDERR "non-protein entity in a1 file: [$pmid] $_\n"}
	if (!&rangep($beg, $end)) {print STDERR "invalid text range: [$pmid] $beg - $end\n"}

	if ($panno{$id}) {print STDERR "duplicated entity ID: [$pmid] $id\n"}

	push @panno, $id;
	$panno{$id} = [$type, $beg, $end, $extra];
    } # while

    close (FILE);
} # read_a1_file


sub read_a2_file {
    my ($fname) = @_;

    if (!open (FILE, "<", $fname)) {print STDERR "cannot open a2 file: $fname\n"; return}

    while (<FILE>) {
	chomp;

	my ($id, $anno, $extra) = split /\t/;
	if ($id !~ /^([TEM][0-9-]+|\*)$/) {
	    print STDERR "invalide ID: $id\nAn ID has to begin with 'T', 'E', or 'M', being followed by digits or dash '-'.\n";
	    next;
	} # if

	if ($id =~ /^T/) {
	    my ($type, $beg, $end) = split / +/, $anno;

	    if (!$target_eclass{$type} && ($type ne 'Entity')) {print STDERR "invalid entity type for a2 file: [$pmid] $id => $type\n"}
	    if (!&rangep($beg, $end)) {print STDERR "invalid text range: [$pmid] $beg - $end\n"}
	    if ($tanno{$id}) {print STDERR "duplicated entity ID: [$pmid] $id\n"}
	    push @tanno, $id;
	    $tanno{$id} = [$type, $beg, $end, $extra];
	} # if

	elsif ($id =~ /^E/) {
	    my ($pred, @arg) = split / +/, $anno;
	    my ($type, $tid) = split ':', $pred;
	    if (!$target_eclass{$type}) {print STDERR "invalid event type: [$pmid] $id => $type\n"}
	    if ($#arg < 0) {print STDERR "event with no argument: [$pmid] $id => $_\n"}

	    my %argnum = ();
	    foreach (@arg) {
		my ($type, $aid) = split ':';
		if ($aid !~ /^[TE][0-9-]+$/) {print STDERR "invalid reference for an argument: [$pmid] $id => $aid\n"}

		$type =~ s/^Theme[1-6]$/Theme/;
		$type =~ s/^Site[1-6]$/Site/;
		$type =~ s/^..Loc$/Loc/;
		if ($argnum{$type}) {$argnum{$type}++} else {$argnum{$type}=1}
	    } # foreach

	    if (($suffix !~ /a2$/) && ($suffix !~ /t12/) && ($argnum{'Site'} || $argnum{'CSite'} || $argnum{'Loc'})) {print STDERR "invalid argument for this task: [$pmid] $_\n"}

	    if (!$argnum{'Theme'}) {print STDERR "event with no theme: [$pmid] $_\n"}

	    if ($type eq 'Binding') {
		if ($argnum{'Site'} > $argnum{'Theme'}) {print STDERR "more sites than themes: [$pmid] $_\n"}
		delete $argnum{'Theme'};
		delete $argnum{'Site'};
	    } # if

	    else {
		if ($argnum{'Theme'}>1) {print STDERR "multiple themes for non-Binding event: [$pmid] $_\n"}
		delete $argnum{'Theme'};

		if ($type =~ /egulation$/) {
		    if ($argnum{'Cause'}>1) {print STDERR "multiple causes: [$pmid] $_\n"}
		    if ($argnum{'Site'}>1)  {print STDERR "multiple sites: [$pmid] $_\n"}
		    if ($argnum{'CSite'}>1) {print STDERR "multiple csites: [$pmid] $_\n"}
		    if (!$argnum{'Cause'} && $argnum{'CSite'}) {print STDERR "no cause but csite: [$pmid] $_\n"}
		    delete $argnum{'Cause'};
		    delete $argnum{'Site'};
		    delete $argnum{'CSite'};
		} # if

		elsif ($type =~ /^Phosphorylation$/) {
		    if ($argnum{'Site'}>1)  {print STDERR "multiple sites: [$pmid] $_\n"}
		    delete $argnum{'Site'};
		} # if

		elsif ($type =~ /^Localization$/) {
		    if ($argnum{'Loc'}>1)  {print STDERR "multiple location arguments: [$pmid] $_\n"}
		    delete $argnum{'Loc'};
		} # if

	    } # else

	    if (%argnum) {print STDERR "invalid argument(s) for $type type: [$pmid] " , join (', ', keys %argnum) , "\n"}

	    if ($eanno{$id}) {print STDERR "duplicated event ID: [$pmid] $_\n"}
	    push @eanno, $id;
	    $eanno{$id} = [$type, $tid, @arg];
	} # if

	elsif ($id =~ /^M/) {
	    my ($mod, $aid) = split ' ', $anno;
	    if (($mod ne 'Negation') && ($mod ne 'Speculation')) {print STDERR "invalid type of event modification: [$pmid] $_\n"}
	    if (($suffix !~ /a2$/) && ($suffix !~ /3/)) {print STDERR "invalid type of annotation for this task: [$pmid] $_\n"}
	    if ($manno{$id}) {print STDERR "duplicated modifier ID: [$pmid] $_\n"}
	    push @manno, $id;
	    $manno{$id} = [$mod, $aid];
	} # elsif

	elsif ($id eq '*') {
	    my ($type, @pid) = split ' ', $anno;
	    if ($type ne 'Equiv') {print STDERR "invalid type of relation: [$pmid] $_\n"}
	    if ($suffix ne '.a2') {print STDERR "Equiv annotation is only allowed to apper in gold files: [$pmid] $_\n"}

	    push @equiv, [@pid];
	} # elsif

    } # while

    close (FILE);
} # read_a2_file


sub rangep {
    my ($beg, $end) = @_;

    if (($beg =~ /^\d+$/) && ($end =~ /^\d+$/)
	&& ($beg >= 0) && ($end <= $textlen) && ($beg < $end)) {return 1}

    else {return 0}
} # rangep


sub usage() {
    print STDERR << "EOF";

[a2-normalize] last updated by jdkim\@is.s.u-tokyo.ac.jp on 3 July 2009.


<DESCRIPTION>
It is a part of the BioNLP'09 Shared Task evaluation software.
It checks on the format of the shared task output files, and normalizes the order of the event arguments for the efficiency of evaluation.


<USAGE>
$0 [-$opt_string] a2_file(s)

* The a2_file has to have one of the valid suffixes (.a2.t1, .a2.t12, .a2.t13, or .a2.t123).


<OPTIONS>
-h            : this (help) message.
-e            : tells it to allow 'Equiv' annotation.
                Use it only when you normalize the 'gold' a2 files.
-g gold_dir   : specifies the 'gold' directory where the *.txt and *.a1 files are placed.
-o output_dir : specifies the directory where the normalized files will be placed.
-u            : tells it update the input files instead of producing separate output files.
                *One of -o or -u has to be given, but not both*
-v            : verbose mode


EOF
      exit;
}
