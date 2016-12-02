import os, sys
import re
import yaml
import json
import time
from datetime import datetime, timedelta
from bldeif.bld_connector    import BLDConnector
from bldeif.utils.time_file  import TimeFile
import build_spec_helper   as bsh
import spec_helper as sh
from bldeif.utils.klog       import ActivityLogger
from bldeif.bld_connector_runner import BuildConnectorRunner

STANDARD_CONFIG = 'honey-badger.yml'
MIN_CONFIG1     = 'bluestem.yml'
MIN_CONFIG2     = 'cliffside.yml'
MIN_CONFIG3     = 'crinkely.yml'
BAD_CONFIG1     = 'attila.yml'
BAD_CONFIG2     = 'genghis.yml'
BAD_CONFIG3     = 'caligula.yml'
SHALLOW_CONFIG  = 'shallow.yml'
DEEP_CONFIG     = 'deepstate.yml'

def connect_to_jenkins(config_file):
    config_file = "config/{}".format(config_file)
    jenk_conf = {}
    with open(config_file, 'r') as cf:
        content = cf.read()
        all_conf = yaml.load(content)
        jenk_conf = all_conf['JenkinsBuildConnector']['Jenkins']

    jc = bsh.JenkinsConnection(jenk_conf, ActivityLogger('inventory.log'))
    return jc

def test_Top_changesets():
    target_job = 'Top'
    magic_number = 71
    repo_name = 'wombats'
    vcs = 'git'
    jc = connect_to_jenkins(STANDARD_CONFIG)
    assert jc.connect()
    jobs = jc.inventory.jobs
    assert next((job for job in jobs if job.name == target_job))
    jc.views = []
    jc.jobs  = []
    del jc.folders[1]
    assert jc.folders

    t = datetime.now() - timedelta(days=1)
    ref_time = t.utctimetuple()
    builds = jc.getRecentBuilds(ref_time)
    for build_info in builds.values():
        for builds in build_info.values():
            for build in builds:
                if build.number != magic_number:
                    continue
                #print(build)
                print (build.repository)
                assert build.repository == repo_name
                assert build.changeSets
                assert build.changeSets[0].vcs == vcs
                # for changeset in build.changeSets:
                #    print(changeset)


