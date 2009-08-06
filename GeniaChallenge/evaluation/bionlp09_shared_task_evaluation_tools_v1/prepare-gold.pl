#!/usr/bin/perl -w
require 5.000;
use strict;
use warnings;
use File::Copy;

my $normalizer = 'a2-normalize.pl';
my $decomposer = 'a2-decompose.pl';
my $generator  = 'generate-task-specific-a2-file.pl';


use Getopt::Std;
my  $opt_string = 'h';
our %opt;


getopts("$opt_string", \%opt) or &usage();
&usage() if $opt{h};
&usage() if $#ARGV < 0;


my $sdir = $ARGV[0]; $sdir =~ s/\/$//;
my $ddir = $ARGV[1]; $ddir =~ s/\/$//;


if (!-d $ddir) {
    if (!mkdir($ddir)) {print STDERR "Cannot open the destination directory: $ddir.\n"; exit}
} # if

print STDERR "\n[Generation of task specific gold annotation files]\n";

my $errmsg = '';


if (($sdir =~ /.tar.gz$/) || ($sdir =~ /.tgz$/)) {
    $errmsg = `tar -C $ddir -xzf $sdir 2>&1`;
    if ($errmsg) {print STDERR "Failed to unpack. Please check your tar-gziped file and try again.\n$errmsg\n"; exit}
    else         {print STDERR "- Uncompress the file, '$sdir' to '$ddir': done.\n"}
} # if

elsif (-d $sdir) {
    $errmsg = `cp $sdir/*.txt $sdir/*.a[12] $ddir 2>&1`;
    if ($errmsg) {print STDERR $errmsg, "\n"; exit}
    else         {print STDERR "- File copy from '$sdir' to '$ddir': done.\n"}
} # elsif

else {
    print STDERR "The source is neither a directory nor a tar-gzipped file.\n";
    exit;
} # else


# format checking & normalization
$errmsg = `$normalizer -eu -g $ddir $ddir/*.a2 2>&1`;
if ($errmsg) {print STDERR $errmsg, "\n"; exit}
else         {print STDERR "- Format validation and normalization: done.\n"}


# generate task specific files
$errmsg  = `$generator -e -t1   $ddir/*.a2`;
$errmsg .= `$generator -e -t12  $ddir/*.a2`;
$errmsg .= `$generator -e -t13  $ddir/*.a2`;
$errmsg .= `$generator -e -t123 $ddir/*.a2`;
if ($errmsg) {print STDERR $errmsg, "\n"; exit}
else         {print STDERR "- Generation of task specific files: done.\n"}


# decompose a2 files
$errmsg  = `$decomposer $ddir/*.a2.t1`;
$errmsg .= `$decomposer $ddir/*.a2.t12`;
$errmsg .= `$decomposer $ddir/*.a2.t13`;
$errmsg .= `$decomposer $ddir/*.a2.t123`;
if ($errmsg) {print STDERR $errmsg, "\n"; exit}
else         {print STDERR "- Event decomposition: done.\n"}

print STDERR "Finished!\n";


sub usage {
    print STDERR << "EOF";

[prepare-gold] last updated by jdkim\@is.s.u-tokyo.ac.jp on 3 July, 2009.


<DESCRIPTION>
It is a part of the BioNLP'09 Shared Task evaluation software.
It prepares 'gold' files for specific tasks for evaluation.
It is dependant on the following scripts:
  a2-normalize.pl,
  a2-decompose.pl,
  generate-task-specific-a2-file.pl.


<USAGE>
$0 [-$opt_string] source_dir_or_tgz destin_directory

source_dir_or_tgz is the directory or the tar-gzipped file which has the gold a2 files.
destin_dir        is the directory where the task-specific gold files are to be located.


EOF
      exit;
} # usage
