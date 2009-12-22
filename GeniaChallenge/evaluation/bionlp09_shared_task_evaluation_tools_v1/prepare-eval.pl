#!/usr/bin/perl -w
require 5.000;
use strict;
use warnings;
use File::Copy;

my $gdir       = 'gold';
my $dos2unix   = 'dos2unix';
my $normalizer = 'a2-normalize.pl';
my $decomposer = 'a2-decompose.pl';
my $generator  = 'generate-task-specific-a2-file.pl';


use Getopt::Std;
my  $opt_string = 'hg:';
our %opt;


getopts("$opt_string", \%opt) or &usage();
&usage() if $opt{h};
&usage() if $#ARGV < 0;
if ($opt{g}) {$gdir = $opt{g}; $gdir =~ s/\/$//}
if (!-d $gdir) {print STDERR "Cannot find the gold directory: $gdir.\n"; exit}

my $sdir = $ARGV[0]; $sdir =~ s/\/$//;
my $ddir = $ARGV[1]; $ddir =~ s/\/$//;

if (!-d $ddir) {
    if (!mkdir($ddir)) {print STDERR "Cannot open the destination directory: $ddir.\n"; exit}
} # if

print STDERR "\n[Preparation of the evaluation for the predicted a2 files]\n";

my $errmsg = '';

if (($sdir =~ /.tar.gz$/) || ($sdir =~ /.tgz$/)) {
    $errmsg = `tar -C $ddir -xzf $sdir 2>&1`;
    if ($errmsg) {print STDERR "Failed to unpack. Please check your tar-gziped file and try again.\n$errmsg\n"; exit}
    else         {print STDERR "- Uncompress the file, '$sdir' to '$ddir': done.\n"}
} # if

elsif (-d $sdir) {
    $errmsg = `cp $sdir/*.a2.* $ddir 2>&1`;
    if ($errmsg) {print STDERR $errmsg, "\n"; exit}
    else         {print STDERR "- File copy from '$sdir' to '$ddir': done.\n"}
} # elsif

else {
    print STDERR "The source is neither a directory nor a tar-gzipped file.\n";
    exit;
} # else


$errmsg = `$dos2unix $ddir/* 2>&1`;
#if ($errmsg) {print STDERR $errmsg, "\n"; exit}
#else {print STDERR "- dos2unix all files: done.\n"}


if (!opendir(DDIR, $ddir)) {print STDERR "Cannot open the destination directory: $ddir.\n"; exit}
my $task = '';
my $mixp = 0;
while (my $name = readdir(DDIR)) {
    if ($name =~ /^[1-9][0-9]+.a2.(t12?3?)$/) {
	if (!$task) {$task = $1}
	elsif (length($1) > length($task)) {$task = $1; $mixp = 1}
    } # if
} # while
closedir(DDIR);

if (!$task) {print STDERR "! Cannot find predicted a2 files (*.a2.t12?3?)."; exit}
print STDERR "- The addressed tasks are determined: $task.\n";
if ($mixp) {print STDERR "  * WARNING, files with a different task speicification found. They will be ignored.\n"}


$errmsg = `$normalizer -u -g $gdir $ddir/*.a2.$task 2>&1`;
if ($errmsg) {print STDERR $errmsg, "\n"; exit}
else {print STDERR "- Format validation and normalization: done.\n"}


# for task 1
if ($task ne 't1') {$errmsg .= `$generator -t1 $ddir/*.a2.$task`}
$errmsg .= `$decomposer $ddir/*.a2.t1`;


# for task 2
if (($task eq 't12') || ($task eq 't123')) {
    if ($task eq 't123') {$errmsg .= `$generator -t12 $ddir/*.a2.$task`}
    $errmsg .= `$decomposer $ddir/*.a2.t12`;
} # if

# for task 3
if (($task eq 't13') || ($task eq 't123')) {
    if ($task eq 't123') {$errmsg .= `$generator -t13 $ddir/*.a2.$task`}
    $errmsg .= `$decomposer $ddir/*.a2.t13`;
} # if


if ($errmsg) {print STDERR $errmsg, "\n"; exit}
else {print STDERR "- Generation of files for evaluation: done.\n"}

print STDERR "Finished!\n";

sub usage {
    print STDERR << "EOF";

[prepare-eval] last updated by jdkim\@is.s.u-tokyo.ac.jp on 3 July, 2009.


<DESCRIPTION>
It is a part of the BioNLP'09 Shared Task evaluation software.
It prepares required files for evaluation from the predicted a2 files.
Note that the predicted a2 files are supposed to have a suffix indicating the tasks addressed.
It is dependant on the following commands:
  dos2unix
  a2-normalize.pl,
  a2-decompose.pl,
  generate-task-specific-a2-file.pl.


<USAGE>
$0 [-$opt_string] source_dir_or_tgz destin_directory

source_dir_or_tgz is the directory or the tar-gzipped file which has the gold a2 files.
destin_dir        is the directory where the generated files are to be located.


<OPTIONS>
-h            : this (help) message.
-g gold_dir   : specifies the 'gold' directory.


EOF
      exit;
} # usage
