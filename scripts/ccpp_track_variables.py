#!/usr/bin/env python

# Standard modules
import argparse
import logging
import collections
import glob

# CCPP framework imports
from metadata_table import find_scheme_names, parse_metadata_file
from ccpp_prebuild import import_config, gather_variable_definitions
from mkstatic import Suite
from parse_checkers import registered_fortran_ddt_names

###############################################################################
# Set up the command line argument parser and other global variables          #
###############################################################################

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--sdf',           action='store', \
                    help='suite definition file to use', required=True)
parser.add_argument('-m', '--metadata_path', action='store', \
                    help='path to CCPP scheme metadata files', required=True)
parser.add_argument('-c', '--config',        action='store', \
                    help='path to CCPP prebuild configuration file', required=True)
parser.add_argument('-v', '--variable',      action='store', \
                    help='variable to track through CCPP suite', required=True)
parser.add_argument('--debug', action='store_true', help='enable debugging output', default=False)
args = parser.parse_args()

###############################################################################
# Functions and subroutines                                                   #
###############################################################################

def parse_arguments(args):
    """Parse command line arguments."""
    success = True
    sdf = args.sdf
    var = args.variable
    configfile = args.config
    metapath = args.metadata_path
    debug = args.debug
    return(success,sdf,var,configfile,metapath,debug)

def setup_logging(debug):
    """Sets up the logging module and logging level."""
    success = True
    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(format='%(levelname)s: %(message)s', level=level)
    if debug:
        logging.info('Logging level set to DEBUG')
    else:
        logging.info('Logging level set to INFO')
    return success

def parse_suite(sdf):
    """Reads provided sdf, parses ordered list of schemes for the suite specified by said sdf"""
    print('reading sdf ' + sdf)
    suite = Suite(sdf_name=sdf)
    success = suite.parse()
    if not success:
        logging.error('Parsing suite definition file {0} failed.'.format(sdf))
        success = False
        return (success, suite)
    print('Successfully read sdf' + suite.sdf_name)
    print('reading list of schemes from suite ' + suite.name)
    print('creating calling tree of schemes')
    success = suite.make_call_tree()
    print(suite.call_tree)
    if not success:
        logging.error('Parsing suite definition file {0} failed.'.format(sdf))
        success = False
        return (success, suite)
    return (success, suite)

def create_metadata_filename_dict(metapath):
    """Given a path, read all .meta files and add them to dictionary with their assoc schemes"""

    success = True
    scheme_filenames=glob.glob(metapath + "*.meta")
    metadata_dict = {}
    print(scheme_filenames)

    for scheme_fn in scheme_filenames:
        schemes=find_scheme_names(scheme_fn)
        # The above returns a list of schemes in each filename, but
        # we want a dictionary of schemes associated with filenames:
        for scheme in schemes:
            metadata_dict[scheme]=scheme_fn

    return (metadata_dict, success)


def create_var_graph(suite, var, config, metapath):
    """Given a suite, variable name, a 'config' dictionary, and a path to .meta files:
         1. Loops through the call tree of provided suite
         2. For each scheme, reads .meta file for said scheme, checks for variable within that
            scheme, and if it exists, adds an entry to an ordered dictionary with the name of
            the scheme and the intent of the variable"""

    success = True

    # Create an ordered dictionary that will hold the in/out information for each scheme
    var_graph=collections.OrderedDict()

    logging.debug("reading .meta files in path:\n {0}".format(metapath))
    (metadata_dict, success)=create_metadata_filename_dict(metapath)

    print(metadata_dict)

    logging.debug(f"reading metadata files for schemes defined in config file: "
                  f"{config['scheme_files']}")

    # Loop through call tree, find matching filename for scheme via dictionary schemes_in_files,
    # then parse that metadata file to find variable info
    partial_matches = {}
    for scheme in suite.call_tree:
        logging.debug("reading meta file for scheme {0} ".format(scheme))

        if scheme in metadata_dict:
            scheme_filename = metadata_dict[scheme]
        else:
            raise Exception(f"Error, scheme '{scheme}' from suite '{suite.sdf_name}' "
                            f"not found in metadata files in {metapath}")

        logging.debug("reading metadata file {0} for scheme {1}".format(scheme_filename, scheme))

        new_metadata_headers = parse_metadata_file(scheme_filename, \
                                                   known_ddts=registered_fortran_ddt_names(), \
                                                   logger=logging.getLogger(__name__))
        for scheme_metadata in new_metadata_headers:
            for section in scheme_metadata.sections():
                found_var = []
                intent = ''
                for scheme_var in section.variable_list():
                    exact_match = False
                    if var == scheme_var.get_prop_value('standard_name'):
                        logging.debug("Found variable {0} in scheme {1}".format(var,section.title))
                        found_var=var
                        exact_match = True
                        intent = scheme_var.get_prop_value('intent')
                        break
                    scheme_var_standard_name = scheme_var.get_prop_value('standard_name')
                    if scheme_var_standard_name.find(var) != -1:
                        logging.debug(f"{var} matches {scheme_var_standard_name}")
                        found_var.append(scheme_var_standard_name)
                if not found_var:
                    logging.debug(f"Did not find variable {var} in scheme {section.title}")
                elif exact_match:
                    logging.debug(f"Exact match found for variable {var} in scheme {section.title},"
                                  f" intent {intent}")
                    var_graph[section.title] = intent
                else:
                    logging.debug(f"Found inexact matches for variable(s) {var} "
                                  f"in scheme {section.title}:\n{found_var}")
                    partial_matches[section.title] = found_var
    if var_graph:
        logging.debug("Successfully generated variable graph for sdf {0}\n".format(suite.sdf_name))
    else:
        success = False
        logging.error(f"Variable {var} not found in any suites for sdf {suite.sdf_name}\n")
        if partial_matches:
            print("Did find partial matches that may be of interest:\n")
            for key in partial_matches:
                print("In {0} found variable(s) {1}".format(key, partial_matches[key]))

    return (success,var_graph)

def check_var():
    """Check given variable against standard names"""
    # This function may ultimately end up being unnecessary
    success = True
    print('Checking if ' + args.variable + ' is in list of standard names')
    return success

def main():
    """Main routine that traverses a CCPP suite and outputs the list of schemes that modify given variable"""

    (success, sdf, var, configfile, metapath, debug) = parse_arguments(args)
    if not success:
        raise Exception('Call to parse_arguments failed.')

    success = setup_logging(debug)
    if not success:
        raise Exception('Call to setup_logging failed.')

#    success = check_var()
#    if not success:
#        raise Exception('Call to check_var failed.')

    (success, suite) = parse_suite(sdf)
    if not success:
        raise Exception('Call to parse_suite failed.')

    (success, config) = import_config(configfile, None)
    if not success:
        raise Exception('Call to import_config failed.')

    # Variables defined by the host model
    (success, _, _) = gather_variable_definitions(config['variable_definition_files'], config['typedefs_new_metadata'])
    if not success:
        raise Exception('Call to gather_variable_definitions failed.')

    (success, var_graph) = create_var_graph(suite, var, config, metapath)
    if not success:
        raise Exception('Call to create_var_graph failed.')

    print('For suite {0}, the following schemes (in order) modify the variable {1}:'.format(suite.sdf_name,var))
    for key in var_graph:
        print("{0} (intent {1})".format(key,var_graph[key]))


if __name__ == '__main__':
    main()
