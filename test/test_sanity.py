import sys, os
import time
import yaml
import shutil
import pytest
import spec_helper as sh
import build_spec_helper as bsh
import jenkins_spec_helper as jsh
from datetime import datetime, timedelta
import time



def test_mock_build():
    two_days_ago = bsh.epochSeconds("-2d")
    mock = bsh.MockJenkinsBuild("fukebane", 13, "Yuge Disaxter", two_days_ago, 34)

    assert(mock.name)   == "fukebane"
    assert(mock.status) == "Yuge Disaxter"


def test_compare_regular_build_time():
    two_days_ago = bsh.epochSeconds("-2d")
    mock_build = bsh.MockJenkinsBuild("fukebane", 13, "Yuge Disaxter", two_days_ago, 34)
    ref_time = time.strptime("2015-10-23T10:23:45Z", '%Y-%m-%dT%H:%M:%SZ')
    logger = bsh.ActivityLogger('test.log')
    konf = bsh.Konfabulator('trumpkin.yaml', logger)
    jenkins_conf = konf.topLevel('Jenkins')
    jc = bsh.JenkinsConnection(jenkins_conf, logger)
    result = jc.jobBeforeRefTime(mock_build, ref_time)
    assert result == False


def test_simple_config():
    t = datetime.now() - timedelta(minutes=60)
    ref_time = t.utctimetuple()
    job_name = 'troglodyte'

    r1 = jsh.create_job(job_name)
    assert r1.status_code == 200

    r2 = jsh.build(job_name)
    assert r2.status_code == 200

    filename = "trumpkin.yaml"

    logger, konf = setup_config(filename)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = konf.topLevel('Jenkins')

    jenk_conf['Jobs'][0] = {'Job':job_name}
    assert jenk_conf['Jobs'][0]['Job'] == job_name
    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)
    assert (job_name in builds["All::%s" % jenk_conf['AgileCentral_DefaultBuildProject']]) == True

    r3 = jsh.delete_job(job_name)
    assert r3.status_code == 200


def test_folder_config():
    t = datetime.now() - timedelta(minutes=1440)
    ref_time = t.utctimetuple()
    job_folder, job_name = 'ALM', 'alm'

    filename = "../config/almci.yml"

    logger, konf = setup_config(filename, False)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = konf.topLevel('Jenkins')

    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)
    assert (job_name in builds["%s::%s" % (job_folder, jenk_conf['AgileCentral_DefaultBuildProject'])]) == True


def x(job, config):
    t = datetime.now() - timedelta(minutes=60)
    ref_time = t.utctimetuple()
    job_name = job

    config_file = config
    file_copy = "%sx" % config_file
    shutil.copyfile(config_file, file_copy)
    logger, konf = setup_config(file_copy)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = konf.topLevel('Jenkins')
    jenkins_url = jsh.construct_jenkins_url(jenk_conf)

    r1 = jsh.create_job(jenkins_url, job_name)
    assert r1.status_code == 200

    r2 = jsh.build(job_name)
    assert r2.status_code == 200

    jenk_conf['Jobs'][0] = {'Job':job_name}
    assert jenk_conf['Jobs'][0]['Job'] == job_name
    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)
    assert (job_name in builds["All::%s" % jenk_conf['AgileCentral_DefaultBuildProject']]) == True
    print("config: %s   job: %s    number of builds: %d" % (file_copy, job_name, len(builds)))

    # r3 = jsh.delete_job(job_name)
    # assert r3.status_code == 200


def test_the_simple_stuff():
    x("troblodyte123", "../config/buildorama.yml")
    # jobs    = ['troglodytex',    'bluestemx']
    # configs = ['trumpkin.yaml', 'buildorama']
    # for j, c in zip(jobs, configs):
    #     x(j, c)

