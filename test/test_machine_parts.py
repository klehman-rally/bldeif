import os, sys
import re
import yaml
import requests
import json
from datetime import datetime, timedelta
import time
from bldeif.bld_connector_runner import BuildConnectorRunner
from bldeif.bld_connector    import BLDConnector
from bldeif.utils.time_file  import TimeFile
import jenkins_spec_helper as jsh
import spec_helper as sh

def create_time_file(config_file, delta):
    t = datetime.now() - timedelta(minutes=delta)
    now_zulu = time.strftime('%Y-%m-%d %H:%M:%S Z', time.gmtime(time.time()))
    last_run_zulu = time.strftime('%Y-%m-%d %H:%M:%S Z', time.gmtime(time.mktime(t.timetuple())))
    time_file_name = "{}_time.file".format(config_file.replace('.yml', ''))
    with open("config/{}".format(time_file_name), 'w') as tf:
        tf.write(last_run_zulu)

    return last_run_zulu

def test_bld_connector_runner():
    #default_lookback = 3600  # 1 hour in seconds
    config_lookback = 7200  # this is in seconds, even though in the config file the units are minutes
    config_file = 'wombat.yml'
    last_run_zulu = create_time_file(config_file, 60)
    #t = int(time.mktime(time.strptime(last_run_zulu, '%Y-%m-%d %H:%M:%S Z'))) - default_lookback
    t = int(time.mktime(time.strptime(last_run_zulu, '%Y-%m-%d %H:%M:%S Z')))  - config_lookback
    last_run_minus_lookback_zulu = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime(t))
    args = [config_file]
    runner = BuildConnectorRunner(args)
    assert runner.first_config == config_file

    runner.run()

    assert config_file in runner.config_file_names
    assert 'AgileCentral' in runner.connector.config.topLevels()
    assert 'Static' in runner.connector.target_projects
    log = "{}.log".format(config_file.replace('.yml', ''))
    assert runner.logfile_name == log

    with open(log, 'r') as f:
        log_content = f.readlines()

    line1 = "Connected to Jenkins server"
    line2 = "Connected to Agile Central"
    line3 = "Got a BLDConnector instance"
    line4 = "recent Builds query: CreationDate >= {}".format(last_run_minus_lookback_zulu)

    match1 = [line for line in log_content if "{}".format(line1) in line][-1]
    match2 = [line for line in log_content if "{}".format(line2) in line][-1]
    match3 = [line for line in log_content if "{}".format(line3) in line][-1]
    match4 = [line for line in log_content if "{}".format(line4) in line][-1]

    assert last_run_minus_lookback_zulu in match4

    assert re.search(r'%s' % line1, match1)
    assert re.search(r'%s' % line2, match2)
    assert re.search(r'%s' % line3, match3)
    assert re.search(r'%s' % line4, match4)

def test_reflect_builds():
    config_file = 'wombat.yml'
    create_time_file(config_file, 2)
    args = [config_file]
    runner = BuildConnectorRunner(args)
    assert runner.first_config == config_file

    runner.run()

    assert config_file in runner.config_file_names
    assert 'AgileCentral' in runner.connector.config.topLevels()
    assert 'Static' in runner.connector.target_projects
    log = "{}.log".format(config_file.replace('.yml', ''))
    assert runner.logfile_name == log

    config_path = "config/{}".format(config_file)
    folder = "immovable wombats"
    my_job = "Top"


    ymlfile = open("config/{}".format(config_file), 'r')
    data = yaml.load(ymlfile)
    jenkins = data['JenkinsBuildConnector']['Jenkins']
    username  = jenkins['Username']
    api_token = jenkins['API_Token']
    protocol  = jenkins['Protocol']
    server    = jenkins['Server']
    port      = jenkins['Port']
    headers = {'Content-Type': 'application/json'}

    jenkins_base_url = "{}://{}:{}".format(protocol, server, port)
    url = "{}/job/{}/job/{}/build".format(jenkins_base_url, folder, my_job)
    r = requests.post(url, auth=(username, api_token), headers=headers)
    assert r.status_code in [200, 201]
    with open(log, 'r') as f:
        log_content = f.readlines()

    line1 = "{} Build #".format(my_job)
    match1 = [line for line in log_content if "{}".format(line1) in line][0]

    assert re.search(r'%s' % line1, match1)







