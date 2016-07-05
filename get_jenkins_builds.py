
import sys
import time
sys.path.insert(0, 'bldeif')

from bldeif.jenkins_connection import JenkinsConnection
from bldeif.utils.klog import ActivityLogger

from pprint import pprint

import yaml


config_chunk = """

    Jenkins:
        Protocol : http
        Server   : int-win7bldmstr
        Port     : 8080
        Prefix   :
        Auth     : false
        User     : 
        Password :
        API_Token: 320ca9ae9408d099183aa052ff3199c2 

        AgileCentral_Workspace: Rally
        AgileCentral_Project: Engineering

       #Views:
            #- View: WRK EIF
            #  include: ^master-*
            #  exclude: ^feature-*,cq,clearquest
            #  AgileCentral_Project: Alligator Tiers

            #  JobNameNumber: 
            #      - 'Foobar #123'
            #      - 'MischieviousMonkey Farm Implement #7'

            #- View: WRK EIF Deliverables
            #  include: ^master-*
            # AgileCentral_Project: Alligator Tiers

            #- View: Smoke and Release
            #  include: smoke-test-TFS2015
            #  exclude: bz,bugzilla,QC11,CQ
            # #AgileCentral_Project: while (e_coyote)
            #  AgileCentral_Project: Alligator Tiers

        Jobs:
            - Job: WICoCo-master build
              AgileCentral_Project: TPFKA Outer Limits

            - Job: jenkins-rally-build-publisher
              AgileCentral_Project: Alligator Tiers
 
    Service:
        Preview: True
"""

alt_chunk = """
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
            - Folder: ALM Prod
            - Folder: Pinata

    Service:
        Preview: True
        LogLevel: DEBUG
"""

#conf = yaml.load(config_chunk)
conf = yaml.load(alt_chunk)
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
    print sys.exc_info[0] # or 1 or 2 for the exception text

ref_timestamp = (2016, 3, 1, 0, 0, 0, 5, 0, -1)

builds = jenkins.getRecentBuilds(ref_timestamp)
finished = time.time()
for view_and_project in builds:
    view, project = view_and_project.split('::', 1)
    print("Jenkins View: %s" % view)
    print("AgileCentral Project: %s" % project)
    for job in builds[view_and_project]:
        print("     Job: %s" % job)
        build_results = builds[view_and_project][job]
        for build in builds[view_and_project][job]:
            print("%s%s" % (" " * 8, build))
        print("")

print("")
print("Elapsed processing time: %6.3f seconds" % (finished - started))

