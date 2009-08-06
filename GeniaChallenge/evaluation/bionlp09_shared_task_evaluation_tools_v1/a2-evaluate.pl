#!/usr/bin/perl
require 5.000;
use strict;

my @target_eclass = ('Gene_expression', 'Transcription', 'Protein_catabolism', 'Phosphorylation', 'Localization');
my @target_rclass = ('Regulation', 'Positive_regulation', 'Negative_regulation');
my @target_mclass = ('Negation', 'Speculation');
my @target_class  = (@target_eclass, 'Binding', @target_rclass, @target_mclass);


my $gdir = '.';

my  $opt_string = 'g:smpvxdh';
our %opt;

use Getopt::Std;
getopts("$opt_string", \%opt) or usage();
usage() if $opt{h};
usage() if $#ARGV < 0;
if ($opt{g}) {$gdir = $opt{g}; $gdir =~ s/\/$//}


## functions for equivalency checking
my $fn_eq_span  = \&eq_span_hard;;
my $fn_eq_class = \&eq_class_hard;
my $fn_eq_args  = \&eq_args_hard;
my $fn_eq_rargs = \&eq_args_hard;


## for total scoring
#  - initialized only once.
my (%tnum_gold, %tnum_mgold, %tnum_answer, %tnum_manswer); # number of golds/matched golds/answers/matched answers
foreach (@target_class) {$tnum_gold{$_} = $tnum_answer{$_} = $tnum_mgold{$_} = $tnum_manswer{$_} = 0}

## for FPs and FNs
my (@FP, @FN) = ((), ());


## Variables which are file-specific.
#  - they are referenced globally.
#  - should be initialized for every file.

## for storing annotation
my ($text, $textlen, @textpic);
my (%protein, %gold, %gold_site, %equiv, %answer, %answer_site);
my (%rgold, %ranswer);   # raw data of gold and answer annotations

## for local scoring
my ($num_gold, $num_mgold, $num_answer, $num_manswer);
my (%num_gold, %num_mgold, %num_answer, %num_manswer); # number of golds/matched golds/answers/matched answers


my ($pmid, $task, $decompose); # $pmid is globally referenced to know what exact file is under processing.
foreach my $fname (@ARGV) {
    if ($fname =~ /([0-9]+)\.a2\.(t12?3?)(d?)$/) {$pmid = $1; $task = $2; $decompose = $3}
    else {print STDERR "failed to recognize the file name: $fname. ==> skipped.\n"; next} 

    ## initialization of file-specific global variables
    ($text, $textlen, @textpic) = ('', 0, ());
    (%protein, %gold, %gold_site, %equiv, %answer, %answer_site) = ((), (), (), (), (), ());
    (%rgold, %ranswer) = ((), ());
    ($num_gold, $num_mgold, $num_answer, $num_manswer) = (0, 0, 0, 0);
    foreach (@target_class) {$num_gold{$_} = $num_answer{$_} = $num_mgold{$_} = $num_manswer{$_} = 0}

    ## event loading
    if (!($textlen = &read_text_file("$gdir/$pmid.txt", $text))) {next}
    if (!&read_a1_file("$gdir/$pmid.a1", \%protein)) {next}
    if (($num_gold   = &read_a2_file("$gdir/$pmid.a2.$task$decompose", 'G')) < 0) {next}
    if (($num_answer = &read_a2_file($fname,               , 'A')) < 0) {next}

    ## set matching methods
    if ($opt{s}) {$fn_eq_span  = \&eq_span_soft}
#    if ($opt{m}) {$fn_eq_class = \&eq_class_soft}
    if ($opt{p}) {$fn_eq_rargs = \&eq_args_soft}

    ## Event matching
    &count_match;

    # debugging message
    if ($opt{d}) {
	foreach (@target_class) {
	    if ($num_manswer{$_} != $num_mgold{$_}) {print STDERR "inconsistent number of matched events: [$pmid] [$_]\t$num_manswer{$_} vs. $num_mgold{$_}\n"}
	    if ($num_manswer{$_} != $num_answer{$_}) {print STDERR "not perfect precision: [$pmid] [$_] $num_manswer{$_} / $num_answer{$_}\n"}
	    if ($num_mgold{$_}   != $num_gold{$_})   {print STDERR "not perfect recall   : [$pmid] [$_] $num_mgold{$_} / $num_gold{$_}\n"}
	} # foreach
    } # if

    ## adjustment for duplication
    foreach (@target_class) {
	if ($num_manswer{$_} > $num_mgold{$_}) {
	    my $num_danswer = $num_manswer{$_} - $num_mgold{$_};
	    $num_answer{$_}  -= $num_danswer;
	    $num_manswer{$_} -= $num_danswer;
	    if ($opt{v}) {print STDERR "According to approximate mathing criteria, $num_danswer equivalent event(s) in your submission is (are) detected, and discarded: [$pmid]\n"}
	} # if
    } # foreach

    ## totalling
    foreach (@target_class) {
	$tnum_gold{$_}    += $num_gold{$_};
	$tnum_answer{$_}  += $num_answer{$_};
	$tnum_mgold{$_}   += $num_mgold{$_};
	$tnum_manswer{$_} += $num_manswer{$_};
    } # foreach
} # foreach


my ($tnum_gold, $tnum_mgold, $tnum_answer, $tnum_manswer) = (0, 0, 0, 0);

foreach (@target_eclass) {
    &report ($_, $tnum_gold{$_}, $tnum_mgold{$_}, $tnum_answer{$_}, $tnum_manswer{$_});
    $tnum_gold += $tnum_gold{$_}; $tnum_mgold += $tnum_mgold{$_};
    $tnum_answer += $tnum_answer{$_}; $tnum_manswer += $tnum_manswer{$_};
} # foreach
&report ('=[SVT-TOTAL]=', $tnum_gold, $tnum_mgold, $tnum_answer, $tnum_manswer);

foreach (('Binding')) {
    &report ($_, $tnum_gold{$_}, $tnum_mgold{$_}, $tnum_answer{$_}, $tnum_manswer{$_});
    $tnum_gold += $tnum_gold{$_}; $tnum_mgold += $tnum_mgold{$_};
    $tnum_answer += $tnum_answer{$_}; $tnum_manswer += $tnum_manswer{$_};
} # foreach

&report ('==[EVT-TOTAL]==', $tnum_gold, $tnum_mgold, $tnum_answer, $tnum_manswer);
print STDOUT "------------------------------------------------------------------------------------\n";

my ($gnum_gold, $gnum_mgold, $gnum_answer, $gnum_manswer) = ($tnum_gold, $tnum_mgold, $tnum_answer, $tnum_manswer);

$tnum_gold = $tnum_mgold = $tnum_answer = $tnum_manswer = 0;
foreach (@target_rclass) {
    &report ($_, $tnum_gold{$_}, $tnum_mgold{$_}, $tnum_answer{$_}, $tnum_manswer{$_});
    $tnum_gold += $tnum_gold{$_}; $tnum_mgold += $tnum_mgold{$_};
    $tnum_answer += $tnum_answer{$_}; $tnum_manswer += $tnum_manswer{$_};
} # foreach
&report ('==[REG-TOTAL]==', $tnum_gold, $tnum_mgold, $tnum_answer, $tnum_manswer);
print STDOUT "------------------------------------------------------------------------------------\n";

$gnum_gold += $tnum_gold; $gnum_mgold += $tnum_mgold; $gnum_answer += $tnum_answer; $gnum_manswer += $tnum_manswer;

if ($task =~ /3$/) {
    $tnum_gold = $tnum_mgold = $tnum_answer = $tnum_manswer = 0;
    foreach (@target_mclass) {
	&report ($_, $tnum_gold{$_}, $tnum_mgold{$_}, $tnum_answer{$_}, $tnum_manswer{$_});
	$tnum_gold += $tnum_gold{$_}; $tnum_mgold += $tnum_mgold{$_};
	$tnum_answer += $tnum_answer{$_}; $tnum_manswer += $tnum_manswer{$_};
    } # foreach
    &report ('==[MOD-TOTAL]==', $tnum_gold, $tnum_mgold, $tnum_answer, $tnum_manswer);
    print STDOUT "------------------------------------------------------------------------------------\n";
    $gnum_gold += $tnum_gold; $gnum_mgold += $tnum_mgold; $gnum_answer += $tnum_answer; $gnum_manswer += $tnum_manswer;
} # if

&report ('==[ALL-TOTAL]==', $gnum_gold, $gnum_mgold, $gnum_answer, $gnum_manswer);
print STDOUT "------------------------------------------------------------------------------------\n";

if ($opt{x}) {
    if (@FP) {print "\n"}
    foreach (@FP) {print "[FP]  $_\n"}
    if (@FN) {print "\n"}
    foreach (@FN) {print "[FN]  $_\n"}
} # if

exit;


my ($c, $g, $mg, $w, $mw, $r, $p, $f);

format STDOUT_TOP =
------------------------------------------------------------------------------------
     Event Class          gold (match)   answer (match)   recall    prec.   fscore  
------------------------------------------------------------------------------------
.

format STDOUT =
  @||||||||||||||||||    @#### (@####)    @#### (@####)   @##.##   @##.##   @##.##  
$c, $g, $mg, $w, $mw, $r, $p, $f
.

sub report ($$$$$) {
    ($c, $g, $mg, $w, $mw) = @_;
    ($r, $p, $f) = &accuracy ($g, $mg, $w, $mw);
    write ();
} # report

sub accuracy {
    my ($gold, $mgold, $answer, $manswer) = @_;

    my $rec = ($gold)?   $mgold   /   $gold : 0;
    my $pre = ($answer)? $manswer / $answer : 0;
    my $f1s = ($pre + $rec)? (2 * $pre * $rec) / ($pre + $rec) : 0;
    
    return ($rec * 100, $pre * 100, $f1s * 100);
} # accuracy

sub storeFP {
    my $tanno = $ranswer{$_[0]};
    while ($tanno =~ /:(T[0-9]+)/) {my $tspan = &tspan($1, \%answer); $tanno =~ s/:$1/:$tspan/}
    push @FP, "$pmid#$tanno";
} # storeFP

sub storeFN {
    my $tanno = $rgold{$_[0]};
    while ($tanno =~ /:(T[0-9]+)/) {my $tspan = &tspan($1, \%gold); $tanno =~ s/:$1/:$tspan/}
    push @FN, "$pmid#$tanno";
} # storeFN

sub tspan {
    my ($id, $rh_anno) = @_;
    my ($beg, $end);
    if    (($id =~ /^T/) && $protein{$id})   {($beg, $end) = (${$protein{$id}}[1],   ${$protein{$id}}[2])}
    elsif (($id =~ /^T/) && $rh_anno->{$id}) {($beg, $end) = (${$rh_anno->{$id}}[1], ${$rh_anno->{$id}}[2])}
    else  {return $id}

    return '"' . substr ($text, $beg, $end-$beg) . '"'. "[$beg-$end]";
} # tspan

sub count_match {
    my %cnt_manswer = (); # count matches of answer annotation instances.
    my %cnt_mgold   = (); # count matches of gold annotation instances.

    my @answer = (); foreach (keys %answer) {if (/^[EM]/) {push @answer, $_; $cnt_manswer{$_} = 0}}
    my @gold   = (); foreach (keys %gold)   {if (/^[EM]/) {push @gold,   $_; $cnt_mgold{$_} = 0}}

    #  for each answer,
    foreach my $aid (@answer) {
	# search for golds which match it.
	foreach my $gid (@gold) {
	    # when found,
	    if (eq_event($aid, $gid)) {
		$cnt_manswer{$aid}++;
		$cnt_mgold{$gid}++;
	    } # if
	} # foreach
    } # foreach

    # update per-class statistics & store
    foreach (@answer) {if ($cnt_manswer{$_} > 0) {$num_manswer{${$answer{$_}}[0]}++}}
    foreach (@gold)   {if ($cnt_mgold{$_}   > 0) {$num_mgold{${$gold{$_}}[0]}++}}

    # store FPs and FNs
    foreach (@answer) {if ($cnt_manswer{$_} < 1) {&storeFP($_)}}
    foreach (@gold)   {if ($cnt_mgold{$_}   < 1) {&storeFN($_)}}
} # count_match


sub eq_event {
    my ($aeid, $geid) = @_;

    if    (($aeid =~ /^E/) && ($aeid =~ /^E/)) {
	if ($fn_eq_class->($aeid, $geid) &&
	    $fn_eq_span->($aeid, $geid) &&
	    $fn_eq_args->($aeid, $geid)) {return 1}
    } # if

    elsif (($aeid =~ /^M/) && ($aeid =~ /^M/)) {
	if ($fn_eq_class->($aeid, $geid) &&
	    $fn_eq_args->($aeid, $geid)) {return 1}
    } # elsif

    else {return 0}
} # eq_event


sub eq_revent {
    my ($aeid, $geid) = @_;
    if ($aeid !~ /^E/) {print STDERR "non-event annotation: $aeid.\n"; return 0}
    if ($geid !~ /^E/) {print STDERR "non-event annotation: $geid.\n"; return 0}

    if ($fn_eq_class->($aeid, $geid) &&
	$fn_eq_span->($aeid, $geid) &&
	$fn_eq_rargs->($aeid, $geid)) {return 1}

    else {return 0}
} # eq_event


sub eq_entity {
    my ($aeid, $geid) = @_;
    if ($aeid !~ /^T/) {print STDERR "[eq_entity] non-entity annotation: $aeid.\n"; return 0}
    if ($geid !~ /^T/) {print STDERR "[eq_entity] non-entity annotation: $geid.\n"; return 0}

    if ($fn_eq_class->($aeid, $geid) && $fn_eq_span->($aeid, $geid)) {return 1}
    else {return 0}
} # eq_entity


sub eq_span_hard {
    my ($aid, $gid) = @_;
    my ($abeg, $aend, $gbeg, $gend) = (-1, -1, -1, -1);

    if (($aid =~ /^T/) && $protein{$aid}) {return ($aid eq $gid)}

    if    ($aid =~ /^T/) {$abeg = ${$answer{$aid}}[1]; $aend = ${$answer{$aid}}[2]}
    elsif ($aid =~ /^E/) {$abeg = ${$answer{${$answer{$aid}}[1]}}[1]; $aend = ${$answer{${$answer{$aid}}[1]}}[2]}

    if    ($gid =~ /^T/) {$gbeg = ${$gold{$gid}}[1];   $gend = ${$gold{$gid}}[2]}
    elsif ($gid =~ /^E/) {$gbeg = ${$gold{${$gold{$gid}}[1]}}[1];     $gend = ${$gold{${$gold{$gid}}[1]}}[2]}

    if (($abeg < 0) || ($gbeg < 0)) {print STDERR "failed to find the span: $pmid ($aid, $gid)\n"; return ''}

    return (($abeg == $gbeg) && ($aend == $gend));
} # eq_span_hard


sub eq_span_soft {
    my ($aid, $gid) = @_;
    my ($abeg, $aend, $gbeg, $gend) = (-1, -1, -2, -2);

    if (($aid =~ /^T/) && $protein{$aid}) {return ($aid eq $gid)}

    if    ($aid =~ /^T/) {$abeg = ${$answer{$aid}}[1]; $aend = ${$answer{$aid}}[2]}
    elsif ($aid =~ /^E/) {$abeg = ${$answer{${$answer{$aid}}[1]}}[1]; $aend = ${$answer{${$answer{$aid}}[1]}}[2]}

    if    ($gid =~ /^T/) {$gbeg = ${$gold{$gid}}[1];   $gend = ${$gold{$gid}}[2]}
    elsif ($gid =~ /^E/) {$gbeg = ${$gold{${$gold{$gid}}[1]}}[1];     $gend = ${$gold{${$gold{$gid}}[1]}}[2]}

    if (($abeg < 0) || ($gbeg < 0)) {print STDERR "failed to find the span: $pmid ($aid, $gid)\n"; return ''}

    ($gbeg, $gend) = &expand_span($gbeg, $gend);
    return (($abeg >= $gbeg) && ($aend <= $gend));
} # eq_span_soft


# expand an entity span
# it refers to global variables $text and @entity 
sub expand_span  {
    my ($beg, $end) = @_;

    my $ebeg = $beg - 2;
    while (($ebeg >= 0)        && (substr ($text, $ebeg, 1) !~ /[ .!?,"']/) && ($textpic[$ebeg] ne 'E')) {$ebeg--} # '"
    $ebeg++;

    my $eend = $end + 2;
    while (($eend <= $textlen) && (substr ($text, $eend-1, 1) !~ /[ .!?,"']/) && ($textpic[$eend-1] ne 'E')) {$eend++} # '"
    $eend--;

#    print STDERR "\n", substr ($text, $ebeg-5, $eend-$ebeg+10), "\n";
#    for(my $i = $ebeg-5; $i< $eend+5; $i++) {
#	if ($textpic[$i]) {print STDERR $textpic[$i]}
#	else {print STDERR ' '}
#    } # for ($i)
#    print STDERR "\n";
#    print STDERR substr ($text, $beg, $end-$beg), "  ===> ", substr ($text, $ebeg, $eend-$ebeg), "\n";

    return ($ebeg, $eend);
} # expand_span


sub eq_class_hard {
    my ($aid, $gid) = @_;
    if    ($protein{$aid}) {return ($aid eq $gid)}
    elsif ($answer{$aid})  {return (${$answer{$aid}}[0] eq ${$gold{$gid}}[0])}
    else  {return 0}
} # eq_class_hard


sub eq_class_soft {
    my ($aid, $gid) = @_;
    if    ($protein{$aid}) {return ($aid eq $gid)}
    elsif ($answer{$aid})  {
	my $aclass = ${$answer{$aid}}[0];
	my $gclass = ${$gold{$gid}}[0];
	$aclass =~ s/^Positive_r/R/; $gclass =~ s/^Positive_r/R/;
	$aclass =~ s/^Negative_r/R/; $gclass =~ s/^Negative_r/R/;
	$aclass =~ s/^Transcription$/Gene_expression/; $gclass =~ s/^Transcription/Gene_expression/;
	return ($aclass eq $gclass);
    } # elsif
    else  {return 0}
} # eq_class_soft


sub eq_args_hard {
    my ($aeid, $geid) = @_;

    my @answer_arg = @{$answer{$aeid}};
    my $aetype = shift @answer_arg;
    my $atid   = shift @answer_arg;
    
    my @gold_arg =   @{$gold{$geid}};
    my $getype = shift @gold_arg;
    my $gtid   = shift @gold_arg;

    if ($#answer_arg != $#gold_arg) {return ''}

#    if (($aeid eq 'E14') && ($geid eq 'E14')) {
#	print STDERR " (", join (", ", @answer_arg), ")\t";
#	print STDERR " (", join (", ", @gold_arg), ")\n";
#    }

    ## compare argument lists as ordered lists.
    for (my $i = 0; $i <= $#answer_arg; $i++) {
	my ($aatype, $aaid) = split /:/, $answer_arg[$i];
	my ($gatype, $gaid) = split /:/, $gold_arg[$i];

	if ($aatype ne $gatype) {return ''}

	# both have to be either t-entities or events
	if (substr($aaid, 0, 1) ne substr($gaid, 0, 1))  {return ''}
	if (($aaid =~ /^E/) && !&eq_revent($aaid, $gaid)) {return ''}
	if (($aaid =~ /^T/) && !&eq_entity($aaid, $gaid)) {return ''}
    } # for

    return 1;
} # eq_args_hard


sub eq_args_soft {
    my ($aeid, $geid) = @_;

    my @answer_arg = @{$answer{$aeid}};
    my $aetype = shift @answer_arg;
    shift @answer_arg;
    while ($answer_arg[-1] !~ /^Theme:/) {pop @answer_arg}
    
    my @gold_arg =   @{$gold{$geid}};
    my $getype = shift @gold_arg;
    shift @gold_arg;
    while ($gold_arg[-1] !~ /^Theme:/) {pop @gold_arg}

    ## compare argument lists as ordered lists.
    if ($#answer_arg != $#gold_arg) {return ''}
    for (my $i = 0; $i <= $#answer_arg; $i++) {
	my ($aatype, $aaid) = split /:/, $answer_arg[$i];
	my ($gatype, $gaid) = split /:/, $gold_arg[$i];

	# both have to be either t-entities or events
	if (substr($aaid, 0, 1) ne substr($gaid, 0, 1))  {return ''}
	if (($aaid =~ /^E/) && !&eq_revent($aaid, $gaid)) {return ''}
	if (($aaid =~ /^T/) && !&eq_entity($aaid, $gaid)) {return ''}
    } # for

    return 1;
} # eq_args_soft


## representation of annotations
# t-entities:          TID (entity_type, beg, end)
#
# event annotation:    EID (event-type, event_entity_id, arg_type:arg_id, arg_type:arg_id, ...)
#                     * order of arguments: theme, cause, site, csite, AtLoc, ToLoc
#                     * linear order between themes
#                     * site may be numbered to indicate the specific theme
#
#  Modifier:           MID (mod_type, '', (Theme, $arg))

sub read_text_file ($$) {
    my ($fname) = $_[0];
    $_[1] = '';     # text, output variable

    if (!open (FILE, "<", $fname)) {print STDERR "cannot open the file: $fname\n"; return ''}
    while (<FILE>) {$_[1] .= $_}
    close (FILE);

    return length $_[1];
} # read_text_file


sub read_a1_file ($$) {
    my ($fname, $rh_anno) = @_;   # rh: reference to hash

    if (!open (FILE, "<", $fname)) {print STDERR "cannot open the a1 file: $fname\n"; return ''}
    my @line = <FILE>; chomp (@line);
    close (FILE);

    foreach (@line) {
	my ($id, $exp) = split /\t/;

	if (/^T/) {
	    my ($type, $beg, $end) = split ' ', $exp;

	    # for text picture
	    for (my $i = $beg; $i < $end; $i++) {$textpic[$i] = 'E'}

	    $rh_anno->{$id} = [$type, $beg, $end];
	} # if
	else {
	    print STDERR "invalid annotation in a1 file: [$pmid] $_\n";
	} # else
    } # foreach

    return $#line + 1;
} # read_a1_file


sub read_a2_file ($$) {
    my ($fname, $mode) = @_; # rh: reference to hash

    if (!open (FILE, "<", $fname)) {print STDERR "cannot open the a2 file: $fname\n"; return -1}
    my @line = <FILE>; chomp (@line);
    close (FILE);

    my ($rh_anno, $rh_site, $rh_ranno, $rh_num_event); # reference to hash
    if ($mode eq 'G') {$rh_anno = \%gold;   $rh_site = \%gold_site;   $rh_ranno = \%rgold;   $rh_num_event = \%num_gold}
    else              {$rh_anno = \%answer; $rh_site = \%answer_site; $rh_ranno = \%ranswer; $rh_num_event = \%num_answer}

    foreach (@line) {
	my ($id, $exp) = split /\t/;
	$rh_ranno->{$id} = $_;

	if (/^T/) {
	    my ($type, $beg, $end) = split ' ', $exp;

	    # for text picture
	    if ($mode eq 'G') {for (my $i = $beg; $i < $end; $i++) {$textpic[$i] = 'E'}}

	    $rh_anno->{$id} = [$type, $beg, $end];
	} # if

	elsif (/^E/) {
	    my @arg = split ' ', $exp;
	    my ($type, $tid) = split ':', shift @arg;

	    my @newarg = ();
	    foreach (@arg) {
		my ($atype, $aid) = split ':';

		$atype =~ s/^Theme[2-6]$/Theme/;
		if ($equiv{$aid}) {$aid = $equiv{$aid}}

		push @newarg, "$atype:$aid";
	    } # foreach

	    $rh_anno->{$id} = [$type, $tid, @newarg];
	} # elsif

	elsif (/^M/) {
	    my ($type, $aid) = split ' ', $exp;
	    $rh_anno->{$id} = [$type, '', ("Theme:$aid")];
	} # elsif

	elsif (/^\*/) {
	    my ($rel, @pid) = split ' ', $exp;
	    my ($rep, @other) = @pid;
	    foreach (@other) {$equiv{$_} = $rep}
	} # elsif

    } # foreach


    my @elist = grep /^[EM]/, keys %{$rh_anno};


    # detect and remove duplication by Equiv
    if ($mode eq 'A') {
	## sort events
	my @newelist = ();
	my %added = ();
	my %remain = ();
	foreach (@elist) {$remain{$_} = 1}
	while (%remain) {
	    my $changep = 0;
	    foreach (keys %remain) {
		my @earg = grep /:E[0-9-]+$/, @{$rh_anno->{$_}};
		my @eaid = map {(split /:/)[1]} @earg;
		my $danglingp = 0;
		foreach (@eaid) {
		    if (!$added{$_}) {$danglingp = 1; last}
		} # foreach
		if (!$danglingp) {push @newelist, $_; $added{$_} = 1; delete $remain{$_}; $changep = 1}
	    } # foreach
	    if (!$changep) {
		if ($opt{v}) {print STDERR "circular reference: [$pmid] ", join (', ', keys %remain), "\n"}
		push @newelist, keys %remain;
		%remain = ();
	    } # if
	} # while

	@elist = @newelist;

#	foreach (@elist) {
#	    print STDERR "$_\t", join (", ", @{$rh_anno->{$_}}), "\n";
#	} # foreach

	my %eventexp = (); # for checking of event duplication
	foreach my $eid (@elist) {
	    # get event expression
	    foreach (@{$rh_anno->{$eid}}) {
		if (!/:/) {next}
		my ($atype, $aid) = split /:/;
		if ($equiv{$aid}) {$aid = $equiv{$aid}}
		$_ = "$atype:$aid";
	    } # foreach

	    my $eventexp = join ',', @{$rh_anno->{$eid}};

	    # check duplication
	    if (my $did = $eventexp{$eventexp}) {
		delete $rh_anno->{$eid};
		$equiv{$eid} = $did;
		if ($opt{v}) {print STDERR "[$pmid] $eid is equivalent to $did => removed.\n"}
	    } # if
	    else {$eventexp{$eventexp} = $eid}
	} # foreach
    } # else

    # get statistics
    my $num_event = 0;
    foreach my $eid (@elist) {
	my $type = ${$rh_anno->{$eid}}[0];
	$rh_num_event->{$type}++; $num_event++;
    } # foreach

    return $num_event;
} # read_a2_file



sub usage {
    print STDERR << "EOF";

[a2-evaluate] last updated by jdkim\@is.s.u-tokyo.ac.jp on 3 July, 2009.


<DESCRIPTION>
It is a part of the BioNLP'09 Shared Task evaluation software.
It takes predicted a2 files and evaluate the accuracy by comparing them to the 'gold' ones.


<USAGE>
$0 [-$opt_string] a2_file(s)

* The a2_file has to have one of the valid suffixes (.a2.t1, .a2.t12, .a2.t13, or .a2.t123).


<OPTIONS>
-g gold_dir specifies the 'gold' directory.
-s          tells it to perform a soft matching for the boundary of triggers.
-p          tells it to perform a approximate recursive matching.
-v          verbose output.
-x          output false positives/negatives
-d          debugging message.


EOF
      exit;
} # usage
