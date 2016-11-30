#!/usr/bin/env python

##########################################################################################
#
# jenaco  -- reflect Jenkins Builds in Agile Central
#
USAGE = """
Usage: python jenaco.py <config_file.yml>
 
       where the config file named must have content in YAML format with 3 sections;
         one for the Agile Central system, 
         one for the Jenkins system, 
         one for the Service configuration 
"""
##########################################################################################

import sys
import re
import traceback
import inspect

sys.path.insert(0, 'bldeif')

from bldeif.bld_connector_runner import BuildConnectorRunner
from bldeif.utils.eif_exception  import ConfigurationError, OperationalError

PROG = 'jenaco'

##########################################################################################

def main(args):

    try:
        connector_runner = BuildConnectorRunner(args)
        connector_runner.run()
    except ConfigurationError as msg:
        # raising a ConfigurationError will cause an ERROR to be logged
        sys.stderr.write('ERROR: %s detected a fatal configuration error. See log file.\n' % PROG)
        sys.exit(1)
    except Exception as msg:
        sys.stderr.write('ERROR: %s encountered an ERROR condition.\n' % PROG)
        # blurt out a formatted stack trace
        excp_type, excp_value, tb = sys.exc_info()
        traceback.print_tb(tb)
        mo = re.search(r"'(?P<ex_name>.+)'", str(excp_type))
        if mo:
            excp_type = mo.group('ex_name').replace('exceptions.', '').replace('bldeif.utils.', '')
        sys.stderr.write('%s: %s\n' % (excp_type, str(excp_value)))
        sys.exit(2)
    sys.exit(0)

##########################################################################################
##########################################################################################

if __name__ == '__main__':
    main(sys.argv[1:])

