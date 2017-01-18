import os, sys
import re
import yaml
import json
import time
from datetime import datetime, timedelta
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
DUPES           = 'dupes.yml'

def connect_to_jenkins(config_file):
    #config_file = 'config/honey-badger.yml'
    config_file = "config/{}".format(config_file)
    jenk_conf = {}
    with open(config_file, 'r') as cf:
        content = cf.read()
        all_conf = yaml.load(content)
        jenk_conf = all_conf['JenkinsBuildConnector']['Jenkins']

    jc = bsh.JenkinsConnection(jenk_conf, ActivityLogger('log/inventory.log'))
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

def test_duplicate_job_names():
    jc = connect_to_jenkins(STANDARD_CONFIG)
    assert jc.connect()
    # 1 black-swan-2 job at the top level  in jc.inventory.jobs
    # 1 black-swan-2 job in the Parkour folder in jc.inventory.folder['Parkour']
    # 1 black-swan2 job in the abacab->bontamy folder in jc.inventory['bontamy']
    # the same black-swan-2 job as above in abacab folder -> 'dark flock' view in jc.inventory.views['dark flock]
    # and the job.container value should be different in each job to reflect the above
    black_swan2_job = [job for job in jc.inventory.jobs if job.name == 'black-swan-2'][0]
    p_folder = jc.inventory.getFolder('/Parkour')
    parkour_folder_black_swan2_job = [job for job in p_folder.jobs if job.name == 'black-swan-2'][0]
    b_folder = jc.inventory.getFolder('/abacab/bontamy')
    bontamy_folder_black_swan2_job = [job for job in b_folder.jobs if job.name == 'black-swan-2'][0]
    df_view = jc.inventory.getView('dark flock')
    darkflock_view_black_swan2_job = [job for job in  df_view.jobs if job.name == 'black-swan-2'][0]

    #for job in [black_swan2_job, parkour_folder_black_swan2_job, bontamy_folder_black_swan2_job, darkflock_view_black_swan2_job] :
    #    print("%s  %s  %s" % (job.container, job.name, job.url))

    assert black_swan2_job.container.split('//')[1] == 'tiema03-u183073.ca.com:8080'
    assert parkour_folder_black_swan2_job.container.split('//')[1] == 'tiema03-u183073.ca.com:8080/job/Parkour'
    assert bontamy_folder_black_swan2_job.container.split('//')[1] == 'tiema03-u183073.ca.com:8080/job/abacab/job/bontamy'
    assert darkflock_view_black_swan2_job.container.split('//')[1] == 'tiema03-u183073.ca.com:8080/job/abacab/job/bontamy/view/dark flock'
    assert black_swan2_job.name == 'black-swan-2'

    assert  darkflock_view_black_swan2_job.fully_qualified_path() == 'tiema03-u183073.ca.com:8080/job/abacab/job/bontamy/view/dark flock/job/black-swan-2'


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
    log = "log/{}.log".format(config_file.replace('.yml', ''))
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
    of = sh.OutputFile('log/inventory.log')
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
    of = sh.OutputFile('log/inventory.log')
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

def test_validate_jobs():
    jc = connect_to_jenkins(DUPES)
    assert jc.connect()
    assert jc.configItemsVetted()

    assert type(jc.vetted_jobs) == type(['a', 'b'])
    bs2 = [job for job in jc.vetted_jobs if job.job_path.split('::') == ['', 'black-swan-2']]
    assert len(bs2) == 1
    bs2 = bs2[0]
    assert bs2.name == 'black-swan-2'
    assert bs2.fully_qualified_path().endswith('/job/black-swan-2')

    # look for a specific job in the Parkour folder
    parkour_jobs = [jobs for  viewproject, jobs in jc.vetted_folder_jobs.items() if viewproject.startswith('Parkour::')][0]
    bs2f = [job  for job in parkour_jobs if job.fully_qualified_path().endswith('/job/Parkour/job/black-swan-2')]
    assert bs2f

    #make sure a job in a folder not specified in the config doesn't show up in vetted_folder_jobs
    bontamy_jobs = [jobs for viewproject, jobs in jc.vetted_folder_jobs.items() if viewproject.startswith('abacab/bontamy::')]
    assert not bontamy_jobs

    dfv_jobs = [jobs for viewproject, jobs in jc.vetted_view_jobs.items() if viewproject.startswith('dark flock::')][0]
    bs2v = [job for job in dfv_jobs if job.fully_qualified_path().endswith('/job/abacab/job/bontamy/view/dark flock/job/black-swan-2')]
    assert bs2v