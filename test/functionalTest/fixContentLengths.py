#!/usr/bin/python
# -*- coding: latin-1 -*-
# Copyright 2016 Telefonica Investigacion y Desarrollo, S.A.U
#
# This file is part of Orion Context Broker.
#
# Orion Context Broker is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Orion Context Broker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Orion Context Broker. If not, see http://www.gnu.org/licenses/.
#
# For those usages not covered by this license please contact with
# iot_support at tid dot es


from getopt import getopt, GetoptError

import os
import sys
import re
import tempfile

__author__ = 'fermin'


#####################
# Functions program #
#####################

def msg(m):
    """
    Print message if verbose mode is enabled

    :param m: message to print
    """
    global verbose

    if verbose:
        print m


def usage_and_exit(m):
    """
    Print usage message and exit"

    :param m: optional error message to print
    """

    if m != '':
        print m
        print

    usage()
    sys.exit(1)


def usage():
    """
    Print usage message
    """

    print 'Modifies each "Content-Length" line in .test files, based on the same values in the corresponding .out file'
    print ''
    print 'Usage: %s -f <file> [-d] [-v] [-u]' % os.path.basename(__file__)
    print ''
    print 'Parameters:'
    print '  -f <file>: .test or .out file to modify. Alternatively, it can be a directory in which case'
    print '             all the .test/.out files in that directory are checked, recursively.'
    print '  -d: dry-run mode, i.e. .test files are not modified'
    print '  -v: verbose mode'
    print '  -u: print this usage message'


def patch_content_lengths(file_name, cl):
    """
    Patch the Content-Length lines in file_name with the data comming from the cl argument,
    assuming it is a list of pairs as returned by content_length_extract(), i.e. using the
    second argument in each pair.

    The patch is based in the technique of writing a temporal file, then replace the original
    one with it.

    It is assumed that cl is ok before invoking this function, i.e. check_same_lines() has been
    previously named.
    """

    n = 0
    file_temp = tempfile.NamedTemporaryFile(delete=False)
    for line in open(file_name):
        m = re.match('^Content-Length: \d+', line)
        if m is not None:
            file_temp.write('Content-Length: %d\n' % cl[n][1])
            msg ('  - patching "Content-Length: %d"' % cl[n][1])
            n += 1
        else:
            file_temp.write(line)

    file_temp.close()

    # Remove old file, replacing by the edited one
    os.remove(file_name)
    os.rename(file_temp.name, file_name)


def content_length_extract(file_name):
    """
    Open file passed as argument, looking for Content-Lengh lines. A list of pairs is removed, the
    first item in each pair being a line number and the second item the Content-Lenght value

    :param file_name: file to be processed
    :return: a list of pairs as described above
    """

    r = []
    l = 0
    for line in open(file_name):
        l += 1
        m = re.match('^Content-Length: (\d+)', line)
        if m is not None:
            cl = int(m.group(1))
            msg('  - push [%d, %d]' % (l, cl))
            r.append([l, cl])
    return r


def check_same_lines(r1, r2):
    """
    Assuming arguments are list of pairs as generated by content_length_extract(), check that
    the have the same number of items and that the lines (firs item in each pair) match.

    :param r1: first list of pairs to compare
    :param r2: second list of pairs to compare
    :return: True if list check is ok, False otherwise
    """

    if len(r1) != len (r2):
        msg ('  - number of content-length entries does no match, skipping!')
        return False

    for i in range(0, len(r1)):
        if (r1[i][0] != r2[i][0]):
            msg('  - item #%d does not match: .test line %d vs .out line %d, skipping!' % (i, r1[i][0], r2[i][0]))
            return False

    return True


def process_dir(dir_name, dry_run):
    """
    Recursive dir processing.

    :param dir_name: directory to be processed
    :param dry_run: if True, then no actual modification in files is done.
    """

    # To be sure directory hasn't a trailing slash
    dir_name_clean = dir_name.rstrip('/')

    for file in os.listdir(dir_name_clean):

        file_name = dir_name_clean + '/' + file

        if os.path.isdir(file_name):
            process_dir(file_name, dry_run)
        else:
            extension = os.path.splitext(os.path.basename(file_name))[1]
            if extension == '.out':
                process_file(file_name, dry_run)


def process_file(file_name, dry_run):
    """
    Process the file pass as argument, In can be either .test or .out. The process is as follows

    1. Get the file basename (i.e. without .out or .test)
    2. Check that basename + .test exist, otherwise return
    3. Check that basename + .out exist, otherwise return
    4. Get all the [line, Content-Length value] pairs in the .test file
    5. Get all the [line, Content-Length value] pairs in the .out file
    6. Check that lines in both cases match
    7. Go through .test modifying Content-Length based the results in the .out file

    :param file_name: file to be processed
    :param dry_run: if True, then no actual modification in files is done (i.e. step 7 is skipped)
    :return: True if the process was ok, False otherwise

    """
    msg('* processing file %s' % file_name)

    # Step 1 to 3
    path = os.path.dirname(file_name)
    basename = os.path.splitext(os.path.basename(file_name))[0]

    file_test = '%s/%s.test' % (path, basename)
    file_out = '%s/%s.out' % (path, basename)

    if not os.path.isfile(file_test):
        msg('  - cannot find %s, skipping!' % file_test)
        return False
    else:
        msg('  - found %s' % file_test)

    if not os.path.isfile(file_out):
        msg('  - cannot find %s, skipping! ' % file_out)
        return False
    else:
        msg('  - found %s' % file_out)

    # Step 4 and 5
    msg ('  - extracting content length in .test file')
    cl_test = content_length_extract(file_test)
    msg ('  - extracting content length in .out file')
    cl_out = content_length_extract(file_out)

    # Step 6
    if not check_same_lines(cl_test, cl_out):
        return False

    # Step 7
    if dry_run:
        msg ('  - dry run mode: not touching file')
    else:
        patch_content_lengths(file_test, cl_out)

    return True


################
# Main program #
################


try:
    opts, args = getopt(sys.argv[1:], 'f:dvu', [])
except GetoptError:
    usage_and_exit('wrong parameter')

# Defaults
file = ''
verbose = False
dry_run = False

for opt, arg in opts:
    if opt == '-u':
        usage()
        sys.exit(0)
    elif opt == '-v':
        verbose = True
    elif opt == '-d':
        dry_run = True
    elif opt == '-f':
        file = arg
    else:
        usage_and_exit('')

if file == '':
    usage_and_exit('missing -f parameter')

if os.path.isdir(file):
    process_dir(file, dry_run)
else:
    process_file(file, dry_run)