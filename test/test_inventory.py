import os, sys
import re
import yaml
import json
import time
from bldeif.bld_connector    import BLDConnector
from bldeif.utils.time_file  import TimeFile
import build_spec_helper   as bsh
import spec_helper as sh
from bldeif.utils.klog       import ActivityLogger

def connect_to_jenkins():
    config_file = 'config/honey-badger.yml'
    #logger, konf = sh.setup_config(config_file)
    jenk_conf = {}
    with open(config_file, 'r') as cf:
        content = cf.read()
        all_conf = yaml.load(content)
        jenk_conf = all_conf['JenkinsBuildConnector']['Jenkins']

    jc = bsh.JenkinsConnection(jenk_conf, ActivityLogger('inventory.log'))
    return jc

def test_jobs_bucket():
    jc = connect_to_jenkins()
    assert jc.connect()
    jobs = jc.inventory.jobs
    assert next((job for job in jobs if job.job_path == "/frozique::australopithicus"))
    assert next((job for job in jobs if job.name == "troglodyte"))

# def test_views_bucket():
#     jc = connect_to_jenkins()
#     assert jc.connect()
#     views = jc.inventory.views
#     my_view = jc.inventory.getView('Prairie')
#     assert my_view.__class__.__name__ == 'JenkinsView'
#     #assert next((view for view in views if view.name == "/Prairie"))
#     #assert next((job for job in jobs if job.name == "troglodyte"))