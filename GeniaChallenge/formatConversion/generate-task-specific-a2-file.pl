#!/usr/bin/perl
require 5.000;
use strict;

# default task specification
my $task = '123';

my  $opt_string = 'ht:e';

sub usage {
    print STDERR << "EOF";

[generate-task-specific-a2-file] last updated by jdkim\@is.s.u-tokyo.ac.jp at 3 Feb 2009

<DESCRIPTION>
It is written to support the BioNLP09 Shared Task:

http://www-tsujii.is.s.u-tokyo.ac.jp/GENIA/SharedTask/. 

It reads *.a2 file(s) and produces corresponding file(s) for task specification as specified by the option -t.

<USAGE>
generate-task-specific-a2-file.py [$opt_string] *.a2_file(s)

<OPTIONS>
-h            show help (this) page.
-e            tells it to include Equiv information in the task file.
              please do not use it if you do not have a particular reason.
-t task_spec  specifies the task.

[possible task specifications]
    1   : task 1
    12  : task 1 and 2
    13  : task 1 and 3
    123 : task 1, 2 and 3 (default, just copy the input file except Equiv lines.)

EOF
      exit;
} # usage


use Getopt::Std;
our %opt;
getopts("$opt_string", \%opt) or usage();
usage() if $opt{h};
usage() if $#ARGV < 0;
if ($opt{t}) {$task = $opt{t}}


if ($task !~ /^12?3?$/) {
    print STDERR "Invalid task specification: $task";
    usage();
    exit(2);
} # if

foreach my $fname (@ARGV) {
    if (substr($fname, -3) ne '.a2') {
	print STDERR "This file does not have the right suffix, .a2: $fname\n";
	next;
    } # if


    my @line;
    # read text file
    open (FILE, "<:utf8", $fname) or print STDERR "cannot open the file: $fname\n";
    {
	@line = <FILE>;
	chomp (@line);
    }
    close (FILE);


    my @newline = ();
    foreach (@line) {
	if ($_ eq '') {next}

	# text-bound annotation
	if (/^T/) {
	    my ($id, $anno, $note) = split "\t";
      
	    # do not output text-bound 'Entity' annotation if the task '2' is not specified.
	    if ((($task eq '1') || ($task eq '13')) && ($anno =~ /^Entity/)) {}

	    # output the line as it is if the task '2' is specified.
	    else {push @newline, $_}
	} # if


	# event expression annotation
	elsif (/^E/) {
	    my ($id, $anno) = split "\t";
      
	    # do not output Site, CSite, AtLoc and ToLoc arguments if the task '2' is not specified.
	    if (($task eq '1') || ($task eq '13')) {
		my @arg = split ' ', $anno;
		my @newarg;

		foreach (@arg) {
		    if (/^ToLoc/ || /^AtLoc/ || /^Site/ || /^CSite/) {}
		    else {push @newarg, $_}
		} # foreach

		push @newline, join ("\t", ($id, join (' ', @newarg)));

	    } # if

	    # output the line as it is if the task '2' is specified.
	    else {
		push @newline, $_;
	    } # else
	} # elsif


	elsif (/^M/) {
	    # output the line as it is if the task '3' is specified.
	    if ($task =~ /3$/) {
		push @newline, $_;
	    } # if
	} # elsif


	elsif (/\*/) {
	    # do not output the annotation for equvalent proteins, except for evaluation purpose
	    if ($opt{e}) {push @newline, $_}
	} # elsif
	    

	else {
	    print STDERR "undefined type of annotation ID: $_\n";
	} # else
    } # foreach


    # remove duplicates unless task is '123'.
    my %id_drop = ();
    if ($task ne '123') { 
	my %seen = ();
	for (my $i = 0; $i <= $#newline; $i++) {
	    my ($id, $anno) = split "\t", $newline[$i];

	    # if duplication, drop
	    if ($seen{$anno}) {$id_drop{$id} = 1}
	    else              {$seen{$anno} = 1}
	} # for ($i)


	# transitive removal
	for (my $i = 0; $i <= $#newline; $i++) {
	    if ($newline[$i] =~ /^E/) {
		my ($id, $anno) = split "\t", $newline[$i];

		if (!$id_drop{$id}) {
		    my @aid = map {(split ':')[1]} split ' ', $anno;
		    foreach my $aid (@aid) {
			if ($id_drop{$aid}) {$id_drop{$id} = 1; $i = 0; last} # $i=0 for further transitivity
		    } # foreach
		} # if
	    } # if

	    elsif ($newline[$i] =~ /^M/) {
		my ($id, $mod, $aid) = split /[\t ]/, $newline[$i];
		if ($id_drop{$aid}) {$id_drop{$id} = 1}
	    } # elif
	} # for ($i)
    } # if

    # output
    open (FILE, ">:utf8", "$fname.t$task") or print STDERR "cannot open the file: $fname.t$task\n";
    {
	foreach (@newline) {
	    my ($id, $anno) = split "\t";
	    if (!$id_drop{$id}) {print FILE "$_\n"}
	} # foreach
    }
    close (FILE);
} # foreach

