#!/usr/bin/env python

"""
Create prototype CCPP metadata tables from Fortran files

Parses annotated Fortran files to produce metadata files where the
standard_name, units, and dimension standard names must be filled in.
The annotation is a two line comment for every physics scheme, derived
data type (DDT) definition, or host model data section.
The annotation form is:

!> \section arg_table_<name>  Argument Table
!! \htmlinclude arg_table_<name>.html

where <name> is the name of the scheme, the name of the DDT, or
the name of the module containing data to be included in the metadata
file.
The annotation must appear just before the scheme or DDT and before
any module data which should not be included in the metadata file.
"""

# Python library imports
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import argparse
import sys
import os
import os.path
import logging
import re
# CCPP framework imports
from parse_tools import init_log, set_log_level, context_string
from parse_tools import CCPPError, ParseInternalError
from parse_tools import reset_standard_name_counter, unique_standard_name
from fortran_tools import parse_fortran_file
from file_utils import create_file_list
from metadata_table import MetadataTable

## Init this now so that all Exceptions can be trapped
logger = init_log(os.path.basename(__file__))

## Recognized Fortran filename extensions
__fortran_filename_extensions = ['F90', 'f90', 'F', 'f']

###############################################################################
def parse_command_line(args, description):
###############################################################################
    "Create an ArgumentParser to parse and return command-line arguments"
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("--files", metavar='<list of files to process>',
                        type=str, required=True,
                        help="""Comma separated list of filenames to process
Filenames with a '.meta' suffix are treated as host model metadata files
Filenames with a '.txt' suffix are treated as containing a list of .meta
filenames""")

    parser.add_argument("--preproc-directives",
                        metavar='VARDEF1[,VARDEF2 ...]', type=str, default=None,
                        help="Proprocessor directives used to correctly parse source files")

    parser.add_argument("--output-root", type=str,
                        metavar='<directory for generated files>',
                        default=os.getcwd(),
                        help="directory for generated files")

    parser.add_argument("--verbose", action='count',
                        help="Log more activity, repeat for increased output")
    pargs = parser.parse_args(args)
    return pargs

###############################################################################
def parse_fortran_files(filenames, preproc_defs, output_dir, logger):
###############################################################################
    """
    Parse each file in <filenames> and produce a prototype metadata file
    with a metadata table for each arg_table entry in the file.
    """
    meta_filenames = list()
    for filename in filenames:
        logger.info('Looking for arg_tables from {}'.format(filename))
        reset_standard_name_counter()
        fheaders = parse_fortran_file(filename, preproc_defs==preproc_defs,
                                      logger=logger)
        # Create metadata filename
        filepath = '.'.join(os.path.basename(filename).split('.')[0:-1])
        fname = filepath + '.meta'
        mfilename = os.path.join(output_dir, fname)
        # Write the metadata file with all the items collected from Fortran
        with open(mfilename, 'w') as outfile:
            for header in fheaders:
                lname_dict = {'1':'ccpp_constant_one'}
                outfile.write('[ccpp-arg-table]\n')
                outfile.write('  name  = {}\n'.format(header.title))
                outfile.write('  type  = {}\n'.format(header.header_type))
                for var in header.variable_list():
                    lname = var.get_prop_value('local_name')
                    outfile.write('[ {} ]\n'.format(lname))
                    prop = var.get_prop_value('standard_name')
                    outfile.write('  standard_name = {}\n'.format(prop))
                    lname_dict[lname] = prop
                    prop = var.get_prop_value('units')
                    if not prop:
                        prop = 'enter units'
                    # End if
                    outfile.write('  units = {}\n'.format(prop))
                    prop = var.get_prop_value('type')
                    outfile.write('  type = {}'.format(prop))
                    prop = var.get_prop_value('kind')
                    if prop:
                        outfile.write(' | kind = {}'.format(prop))
                    # End if
                    outfile.write('\n')
                    dims = var.get_dimensions()
                    # Fill in standard names for dimensions
                    dlist = list()
                    for dim in dims:
                        dslist = list()
                        for dimspec in dim.split(':'):
                            if dimspec and (dimspec in lname_dict):
                                dstr = lname_dict[dimspec]
                            else:
                                dstr = unique_standard_name()
                            # End if
                            dslist.append(dstr)
                        # End for
                        dlist.append(':'.join(dslist))
                    # End for
                    prop = '(' + ','.join(dlist) + ')'
                    outfile.write('  dimensions = {}\n'.format(prop))
                    if header.header_type == 'scheme':
                        prop = var.get_prop_value('intent')
                        outfile.write('  intent = {}\n'.format(prop))
                    # End if
                # End for
            # End for
        # End with
        meta_filenames.append(mfilename)
    return meta_filenames

###############################################################################
def _main_func():
###############################################################################
    """Parse command line, then parse indicated Fortran files.
    Finally, generate a prototype metadata file for each Fortran file."""
    args = parse_command_line(sys.argv[1:], __doc__)
    verbosity = args.verbose
    if verbosity > 1:
        set_log_level(logger, logging.DEBUG)
    elif verbosity > 0:
        set_log_level(logger, logging.INFO)
    # End if
    # Make sure we know where output is going
    output_dir = os.path.abspath(args.output_root)
    # We need to create a list of input Fortran files
    fort_files = create_file_list(args.files, __fortran_filename_extensions,
                                  'Fortran', logger)
    preproc_defs = args.preproc_directives
    ## A few sanity checks
    ## Make sure output directory is legit
    if os.path.exists(output_dir):
        if not os.path.isdir(output_dir):
            errmsg = "output-root, '{}', is not a directory"
            raise CCPPError(errmsg.format(args.output_root))
        elif not os.access(output_dir, os.W_OK):
            errmsg = "Cannot write files to output-root ({})"
            raise CCPPError(errmsg.format(args.output_root))
        # End if (output_dir is okay)
    else:
        # Try to create output_dir (let it crash if it fails)
        os.makedirs(output_dir)
    # End if
    # Parse the files and create metadata
    meta_files = parse_fortran_files(fort_files, preproc_defs,
                                     output_dir, logger)

###############################################################################

if __name__ == "__main__":
    try:
        _main_func()
        sys.exit(0)
    except ParseInternalError as pie:
        logger.exception(pie)
        sys.exit(-1)
    except CCPPError as ca:
        if logger.getEffectiveLevel() <= logging.DEBUG:
            logger.exception(ca)
        else:
            logger.error(ca)
        # End if
        sys.exit(1)
    finally:
        logging.shutdown()
    # End try
