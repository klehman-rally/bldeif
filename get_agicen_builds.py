#!/usr/bin/env python

import sys
import time
import yaml

sys.path.insert(0, 'bldeif')

__version__ = '0.2.2'

#from agicen_bld_connection import AgileCentralConnection
from bldeif.agicen_bld_connection import AgileCentralConnection
from bldeif.utils.eif_exception   import ConfigurationError, OperationalError
from bldeif.utils.klog import ActivityLogger

from pprint import pprint

config_chunk = """

    AgileCentral:
        Server   : rally1.rallydev.com
        Username : you@reclinaz.com 
        Password : "big**WHUPj9876"
       #API_Key  : _xxdabas3892qytqhqb89qev4h279ygb3497qy4739387y0

        Workspace: Wonnicam
        #DefaultProject: Engineering
        DefaultProject: Dancing Fruit Boggles

    Service:
        LogLevel: INFO
        Preview: True
        StrictProject: True
"""

CONFIG_CHUNK = """
    AgileCentral:
        Server   : rally1.rallydev.com
       #Username : klehman@rallydev.com
       #Password : abc123!!
        APIKey  : _x6CZhqQgiist6kTtwthsAAKHtjWE7ivqimQdpP3T4
        Workspace: Rally
        DefaultProject: Engineering

    Service:
        LogLevel: INFO
        Preview: True
        StrictProject: True
"""

###########################################################################################################

def main(args):

    conf = yaml.load(CONFIG_CHUNK)
    ac_conf = conf['AgileCentral']

    #pprint(ac_conf)
    #print("=" * 80)
    #print("")

    logger  = ActivityLogger("agicen.builds.log", policy='calls', limit=1000)
    agicen = AgileCentralConnection(ac_conf, logger)
    agicen_headers = {'name'    : 'AgileCentral Build Lister', 'version' : __version__,
                      'vendor'  : 'Open Source Galaxy', 'other_version' : 'placeholder' }
    agicen.set_integration_header(agicen_headers)
    agicen.setSourceIdentification('placeholder', '0.0.0')
    agicen.connect()

    ref_timestamp = (2016, 3, 1, 0, 0, 0, 5, 0, -1)

    started = time.time()
    builds = agicen.getRecentBuilds(ref_timestamp)
    print("%d Projects had Build items within the defined scope" % len(builds)) 
    finished = time.time()
    for project in builds:
    ##
      # if project != ac_conf['DefaultProject']:
      #     break
    ##
        print("AgileCentral Project: %s" % project)
        job_names = builds[project].keys()
        for job_name in job_names:
            for build in builds[project][job_name]:
                build_date = build.Start[:-5].replace('T', ' ')
                duration = pretty_duration(build.Duration)

                print("    %-24.24s   %5d  %-10.10s  %s  %15.15s" % \
                      (job_name, int(build.Number), build.Status, build_date, duration))
        print("")

    print("Elapsed retrieval time: %6.3f seconds" % (finished - started))

###########################################################################################################

def pretty_duration(value_in_secs_millis):
    whole_secs, millis = str(value_in_secs_millis).split('.')
    hours, seconds  = divmod(int(whole_secs),  3600)
    minutes, secs   = divmod(seconds, 60)

    duration = "%02d:%02d.%-3.3s" % (minutes, secs, millis[:3])

    if hours:
        duration = ("%d:" % hours) + duration
    else:
        duration = "%d:%02d.%-3.3s" % (minutes, secs, millis[:3])

    return duration

###########################################################################################################
###########################################################################################################

if __name__ == '__main__':
    main(sys.argv[1:])
	
