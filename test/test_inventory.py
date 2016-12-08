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
    #config_file = 'config/honey-badger.yml'
    config_file = "config/{}".format(config_file)
    jenk_conf = {}
    with open(config_file, 'r') as cf:
        content = cf.read()
        all_conf = yaml.load(content)
        jenk_conf = all_conf['JenkinsBuildConnector']['Jenkins']

    jc = bsh.JenkinsConnection(jenk_conf, ActivityLogger('inventory.log'))
    return jc

def test_jobs_bucket():
    jc = connect_to_jenkins(STANDARD_CONFIG)
    assert jc.connect()
    jobs = jc.inventory.jobs
    for j in jc.inventory.jobs:
        print(j.job_path)
    assert next((job for job in jobs if job.job_path == "/frozique::australopithicus"))
    assert next((job for job in jobs if job.name == "troglodyte"))

def test_views_bucket():
    jc = connect_to_jenkins(STANDARD_CONFIG)
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
    jc = connect_to_jenkins(STANDARD_CONFIG)
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
    jc = connect_to_jenkins(STANDARD_CONFIG)
    assert jc.connect()
    container = 'http://tiema03-u183073.ca.com:8080/job/abacab/job/bontamy'
    folder_name, view_name = 'crinkely', 'Cliffside'
    fqp = jc.get_view_full_path(container, folder_name, view_name)
    expected_value = '/abacab/bontamy/crinkely/Cliffside'
    assert fqp == expected_value

def test_folder_full_path():
    jc = connect_to_jenkins(STANDARD_CONFIG)
    assert jc.connect()
    jc.showFolderJobs()
    container = 'job/abacab/job/bontamy'
    folder_name = 'crinkely'
    fqp = jc.get_folder_full_path(container, folder_name)
    expected_value = '/abacab/bontamy/crinkely'
    assert fqp == expected_value

def test_job_vetting():
    jc = connect_to_jenkins(MIN_CONFIG1)
    assert jc.connect()
    assert jc.configItemsVetted()

    jc = connect_to_jenkins(BAD_CONFIG1)
    assert jc.connect()
    assert not jc.configItemsVetted()

def test_view_vetting():
    jc = connect_to_jenkins(MIN_CONFIG2)
    assert jc.connect()
    assert jc.configItemsVetted()

    jc = connect_to_jenkins(BAD_CONFIG2)
    assert jc.connect()
    assert not jc.configItemsVetted()

def test_folder_vetting():
    jc = connect_to_jenkins(MIN_CONFIG3)
    assert jc.connect()
    assert jc.configItemsVetted()

    jc = connect_to_jenkins(BAD_CONFIG3)
    assert jc.connect()
    assert not jc.configItemsVetted()

def test_log_for_config_vetting():
    config_file = BAD_CONFIG1
    args = [config_file]
    runner = BuildConnectorRunner(args)
    assert runner.first_config == config_file
    runner.run()
    log = "{}.log".format(config_file.replace('.yml', ''))
    assert runner.logfile_name == log

    with open(log, 'r') as f:
        log_content = f.readlines()

    #error = "these jobs: Parkour, pillage-and-plunder, torment  were not present in the Jenkins inventory of Jobs"
    # the log contained the same error, but the order of job names is different:
    # "these jobs: 'pillage-and-plunder', 'torment', 'Parkour'  were not present in the Jenkins inventory of Jobs"
    error = "were not present in the Jenkins inventory of Jobs"
    match = [line for line in log_content if "{}".format(error) in line][0]
    assert re.search(r'%s' % error, match)

def test_shallow_depth_config():
    of = sh.OutputFile('inventory.log')
    t = datetime.now() - timedelta(days=365)
    ref_time = t.utctimetuple()
    jc = connect_to_jenkins(SHALLOW_CONFIG)
    assert jc.connect()
    assert not jc.configItemsVetted()

    log_output = of.readlines()
    error_lines = [line for line in log_output if 'ERROR' in line][0]
    error = "these folders: 'dungeon'  were not present in the Jenkins inventory of Folders"
    assert re.search(error, error_lines) is not None

def test_deepy_depth_config():
    of = sh.OutputFile('inventory.log')
    t = datetime.now() - timedelta(days=365)
    ref_time = t.utctimetuple()
    jc = connect_to_jenkins(DEEP_CONFIG)
    assert jc.connect()
    assert jc.configItemsVetted()

    log_output = of.readlines()
    error_lines = [line for line in log_output if 'ERROR' in line]
    assert len(error_lines) == 0

    builds = jc.getRecentBuilds(ref_time)
    assert builds

