#!/usr/bin/env python

import sys
import time
sys.path.insert(0, 'bldeif')

from bldeif.jenkins_connection import JenkinsConnection
from bldeif.utils.klog import ActivityLogger

from pprint import pprint

import yaml

CONFIG_CHUNK = """
    Jenkins:
        Protocol : http
        Server   : almci
        Port     : 80
        Prefix   :
        Auth     : false
        User     : 
        Password :
        Debug    : True

        AgileCentral_Workspace: Rally
        AgileCentral_Project: Engineering

        Folders:
            - Folder: ALM
              AgileCentral_Project: ALM-PufnStuf
              #include: webapp
              exclude: backward-compatibility,on-demand
            - Folder: ALM Deploy
            - Folder: Pinata

    Service:
        Preview: True
        LogLevel: DEBUG
"""

############################################################################################################

def main(args):

    conf = yaml.load(CONFIG_CHUNK)
    jenkconf = conf['Jenkins']

    #pprint(jenkconf)
    #print("=" * 80)
    #print("")

    logger  = ActivityLogger("jenk.log", policy='calls', limit=1000)
    jenkins = JenkinsConnection(jenkconf, logger)
    started = time.time()
    try:
        jenkins.connect()
    except Exception as ex:
        # does ex include the following text?  
        #  Max retries exceeded with url: /manage .* nodename nor servname provided, or not known'
        print(sys.exc_info()[0]) # 0 is the Exception instance
        print(sys.exc_info()[1]) # 1 is the Exception text

    ref_timestamp = (2016, 6, 1, 0, 0, 0, 5, 0, -1)

    #top_level_folders = sorted(jenkins.view_folders['All'].keys())
    #for folder_name in top_level_folders:
    #    folder = jenkins.view_folders['All'][folder_name]
    #    print(folder.info())

    builds = jenkins.getRecentBuilds(ref_timestamp)
    finished = time.time()
    for tank_and_project in sorted(builds):
        container, project = tank_and_project.split('::', 1)
        print("Jenkins Container: %s" % container)
        print("AgileCentral Project: %s" % project)
        for job in builds[tank_and_project]:
            print("     Job: %s" % job)
            build_results = builds[tank_and_project][job]
            for build in build_results:
                print("%s%s" % (" " * 8, build))
            print("")

    #for view_and_project in builds:
    #    view, project = view_and_project.split('::', 1)
    #    print("Jenkins View: %s" % view)
    #    print("AgileCentral Project: %s" % project)
    #    for job in builds[view_and_project]:
    #        print("     Job: %s" % job)
    #        build_results = builds[view_and_project][job]
    #        for build in builds[view_and_project][job]:
    #            print("%s%s" % (" " * 8, build))
    #        print("")
    #
    print("")
    print("Elapsed processing time: %6.3f seconds" % (finished - started))

############################################################################################################
############################################################################################################

if __name__ == '__main__':
    main(sys.argv[1:])
