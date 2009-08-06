#!/usr/bin/perl
require 5.000;
use strict;

# default task specification
my $task = '123';

my  $opt_string = 'ht:e';

use Getopt::Std;
our %opt;
getopts("$opt_string", \%opt) or usage();
usage() if $opt{h};
usage() if $#ARGV < 0;
if ($opt{t}) {$task = $opt{t}}


if ($task !~ /^12?3?$/) {
    print STDERR "### Invalid task specification: $task ###\n";
    usage();
} # if
#print STDERR "generate files for task $task\n";


foreach (@ARGV) {
    my ($path, $pmid, $suffix) = ('', '');
    if (/([1-9][0-9]*)(\.a2\.t12?3?|\.a2)$/) {$pmid = $1; $suffix = $2; $path = substr ($_, 0, length ($_) - length ($pmid . $suffix))}
    else {print STDERR "unrecognizable filename : $_\n"; next}


    # read text file
    my @line = ();

    open (FILE, "<", $_) or print STDERR "cannot open the file: $_\n";
    while (<FILE>) {
	chomp;
	if ($_ eq '') {next}


	# text-bound annotation
	if (/^T/) {
	    my ($id, $anno, $note) = split "\t";
      
	    # do not output text-bound 'Entity' annotation if the task '2' is not specified.
	    if ((($task eq '1') || ($task eq '13')) && ($anno =~ /^Entity/)) {}

	    # output the line as it is if the task '2' is specified.
	    else {push @line, $_}
	} # if


	# event expression annotation
	elsif (/^E/) {
	    my ($id, $anno) = split "\t";
      
	    # output only Theme and Cause arguments if the task '2' is not specified.
	    if (($task eq '1') || ($task eq '13')) {
		my @arg = split ' ', $anno;

		my @newarg = ();
		push (@newarg, shift @arg);
		foreach (@arg) {if (/^Theme/ || /^Cause/) {push @newarg, $_}}

		push @line, join ("\t", ($id, join (' ', @newarg)));
	    } # if

	    # output the line as it is if the task '2' is specified.
	    else {push @line, $_}
	} # elsif


	elsif (/^M/) {
	    # output the line as it is if the task '3' is specified.
	    if ($task =~ /3$/) {push @line, $_}
	} # elsif


	elsif (/\*/) {
	    # do not output the annotation for equvalent proteins, except for evaluation purpose
	    if ($opt{e}) {push @line, $_}
	} # elsif
	    

	else {
	    print STDERR "undefined type of annotation ID: $_\n";
	} # else
    } # foreach
    close (FILE);


    # remove duplicates unless task is '123'.
    my %id_drop = ();
    if ($task ne '123') { 
	my %seen = ();
	for (my $i = 0; $i <= $#line; $i++) {
	    my ($id, $anno) = split "\t", $line[$i];

	    # if duplication, drop
	    if ($seen{$anno}) {$id_drop{$id} = 1}
	    else              {$seen{$anno} = 1}
	} # for ($i)


	# transitive removal
	for (my $i = 0; $i <= $#line; $i++) {
	    if ($line[$i] =~ /^E/) {
		my ($id, $anno) = split "\t", $line[$i];

		if (!$id_drop{$id}) {
		    my @aid = map {(split ':')[1]} split ' ', $anno;
		    foreach my $aid (@aid) {
			if ($id_drop{$aid}) {$id_drop{$id} = 1; $i = 0; last} # $i=0 for further transitivity
		    } # foreach
		} # if
	    } # if

	    elsif ($line[$i] =~ /^M/) {
		my ($id, $mod, $aid) = split /[\t ]/, $line[$i];
		if ($id_drop{$aid}) {$id_drop{$id} = 1}
	    } # elif
	} # for ($i)
    } # if


    # output
    my $ofilename = "$path$pmid.a2.t$task";
    open (FILE, ">", $ofilename) or print STDERR "cannot open the file: $ofilename\n";
    foreach (@line) {
	my ($id, $anno) = split "\t";
	if (!$id_drop{$id}) {print FILE "$_\n"}
    } # foreach
    close (FILE);
} # foreach


sub usage {
    print STDERR << "EOF";

[generate-task-specific-a2-file] last updated by jdkim\@is.s.u-tokyo.ac.jp at 3 July, 2009.


<DESCRIPTION>
It is a part of the BioNLP'09 Shared Task evaluation software.
It reads a2 file(s) and produces corresponding file(s) for task specification as specified by the option -t.


<USAGE>
generate-task-specific-a2-file.py [$opt_string] *.a2_file(s)


<OPTIONS>
-h            show help (this) page.
-e            tells it to include Equiv information in the task file.
              please do not use it if you do not have a particular reason.
-t task_spec  specifies the task.


<TASK SPECIFICATIONS>
1   : task 1
12  : task 1 and 2
13  : task 1 and 3
123 : task 1, 2 and 3 (default)

	      
EOF
exit;
} # usage
