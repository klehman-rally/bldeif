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
    for j in jc.inventory.jobs:
        print(j.job_path)
    assert next((job for job in jobs if job.job_path == "/frozique::australopithicus"))
    assert next((job for job in jobs if job.name == "troglodyte"))

def test_views_bucket():
    jc = connect_to_jenkins()
    assert jc.connect()
    views = jc.inventory.views

    jc.showViewJobs()

    assert jc.inventory.getView('/abacab/temporary insanity')
    assert jc.inventory.getView('/Prairie')
    assert jc.inventory.getView('/abacab/bontamy/crinkely/Cliffside')

    view_path = '/abacab/bontamy/crinkely/dungeon/ghosterly'
    job_name = 'freddy-flintstone'
    assert [job.name for job in views[view_path].jobs if job.name == job_name]

    view_path = '/frozique/submarine'
    job_name = 'bluestem'
    assert [job.name for job in views[view_path].jobs if job.name == job_name]

def test_folders_bucket():
    jc = connect_to_jenkins()
    assert jc.connect()
    folders = jc.inventory.folders

    #jc.showFolderJobs()

    assert jc.inventory.getFolder('/frozique')
    assert jc.inventory.getFolder('/Parkour')
    assert jc.inventory.getFolder('/abacab')
    folder = jc.inventory.getFolder('/abacab/bontamy')
    assert jc.inventory.getFolder('/abacab/bontamy')
    dungeon_folder =  jc.inventory.getFolder('/abacab/bontamy/crinkely/dungeon')
    assert [job.name for job in dungeon_folder.jobs if job.name == 'freddy-flintstone']


def test_fully_qualified_path():
    jc = connect_to_jenkins()
    assert jc.connect()
    container = 'http://tiema03-u183073.ca.com:8080/job/abacab/job/bontamy'
    folder_name, view_name = 'crinkely', 'Cliffside'
    fqp = jc.get_view_full_path(container, folder_name, view_name)
    expected_value = '/abacab/bontamy/crinkely/Cliffside'
    assert fqp == expected_value

def test_folder_full_path():
    jc = connect_to_jenkins()
    assert jc.connect()
    jc.showFolderJobs()
    container = 'job/abacab/job/bontamy'
    folder_name = 'crinkely'
    fqp = jc.get_folder_full_path(container, folder_name)
    expected_value = '/abacab/bontamy/crinkely'
    assert fqp == expected_value
