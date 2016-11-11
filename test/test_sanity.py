import sys, os
import time
import yaml
import shutil
import pytest
import spec_helper         as sh
import build_spec_helper   as bsh
import jenkins_spec_helper as jsh
from datetime import datetime, timedelta
from bldeif.utils.test_konfabulus import TestKonfabulator
from bldeif.utils.klog       import ActivityLogger

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


# def test_simple_config():
#     t = datetime.now() - timedelta(minutes=60)
#     ref_time = t.utctimetuple()
#     job_name = 'troglodyte'
#
#     r1 = jsh.create_job(job_name)
#     assert r1.status_code == 200
#
#     r2 = jsh.build(job_name)
#     assert r2.status_code == 200
#
#     filename = "trumpkin.yaml"
#
#     logger, konf = sh.setup_config(filename)
#     assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
#     jenk_conf = konf.topLevel('Jenkins')
#
#     jenk_conf['Jobs'][0] = {'Job':job_name}
#     assert jenk_conf['Jobs'][0]['Job'] == job_name
#     jc = bsh.JenkinsConnection(jenk_conf, logger)
#     jc.connect()
#     builds = jc.getRecentBuilds(ref_time)
#     assert (job_name in builds["All::%s" % jenk_conf['AgileCentral_DefaultBuildProject']]) == True
#
#     r3 = jsh.delete_job( job_name)
#     assert r3.status_code == 200


def test_folder_config():
    t = datetime.now() - timedelta(minutes=1440)
    ref_time = t.utctimetuple()
    job_folder, job_name = 'ALM', 'alm'

    filename = "../config/almci.yml"

    logger, konf = sh.setup_config(filename, False)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = konf.topLevel('Jenkins')

    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)
    assert (job_name in builds["%s::%s" % (job_folder, jenk_conf['AgileCentral_DefaultBuildProject'])]) == True

def test_test_konfabulator():
    logger = ActivityLogger('test.log')
    filename = "../config/buildorama.yml"
    test_konfabulator = TestKonfabulator(filename, logger)
    job1 = 'slippery slope'
    item1 = {'Job' : job1}
    test_konfabulator.add_to_container(item1)
    assert test_konfabulator.has_item('Job', job1) == True
    job2 = 'uphill both ways'
    item2 = {'Job' : job2}
    test_konfabulator.replace_in_container(item1,item2)
    assert test_konfabulator.has_item('Job', job1) == False
    assert test_konfabulator.has_item('Job', job2) == True


def jenkins_job_lifecycle(job_name, config, view="All", folder=None):
    """
       Given a job name and a config dictionary, create a Job for the job name,
       simulate a build, run the part of the bldeif connector that will detect the job
       and then delete the job.
    """
    logger, konf = sh.setup_config(config)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = konf.topLevel('Jenkins')
    jenkins_url = jsh.construct_jenkins_url(jenk_conf)

    r1 = jsh.create_job(jenk_conf, jenkins_url, job_name, view, folder)
    assert r1.status_code in  [200, 201]

    r2 = jsh.build(jenk_conf, jenkins_url, job_name, folder=folder)
    assert r2.status_code in  [200, 201]

    r3 = jsh.delete_job(jenk_conf, jenkins_url, job_name, folder=folder)
    assert r3.status_code == 200

    return True


def test_manipulate_jenkins_jobs():
    naked_job = "troblodyte{}".format(time.time())
    config_path = "../config/buildorama.yml"
    assert jenkins_job_lifecycle(naked_job, config_path) == True

    view_job = "troblodyte{}".format(time.time())
    view = 'Prairie'
    assert jenkins_job_lifecycle(view_job, config_path, view=view) == True

    folder_job_name = "troblodyte{}".format(time.time())
    folder = 'Parkour'
    assert jenkins_job_lifecycle(folder_job_name, config_path, folder=folder) == True

def test_find_build():
    t = datetime.now() - timedelta(minutes=60)
    ref_time = t.utctimetuple()
    naked_job = "troblodyte{}".format(time.time())
    config = "../config/buildorama.yml"
    logger, tkonf = sh.setup_test_config(config)

    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = tkonf.topLevel('Jenkins')

    jenkins_url = jsh.construct_jenkins_url(jenk_conf)
    r1 = jsh.create_job(jenk_conf, jenkins_url, naked_job)
    assert r1.status_code in [200, 201]
    tkonf.add_to_container({'Job': naked_job })

    # create a build
    r2 = jsh.build(jenk_conf, jenkins_url, naked_job)
    assert r2.status_code in [200, 201]
    # find it
    target_job_builds = []
    time.sleep(10)
    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)

    for view_project, jobs in builds.items():
        if jobs and naked_job in jobs:  # jobs is dict keyed by the job name with a value of a list of JenkinsBuild instances
            target_job_builds = jobs[naked_job]

    #target_job_builds = [build_info[naked_job] for view_project, build_info  in builds.items() if naked_job in build_info.keys() ]

    for key, val in builds.items():
        #print("key: %s, val: %s" % (key, val))
        print(key)
        #for k, v in val.items():
        #    print("...k: %s, v: %s" % (k, v))
        for builds in val.values():
            for build in builds:
                print("    %s" % build)

    assert len(target_job_builds) == 1

    # delete the job
    r3 = jsh.delete_job(jenk_conf, jenkins_url, naked_job)
    assert r3.status_code == 200

def test_find_two_builds():
    t = datetime.now() - timedelta(minutes=60)
    ref_time = t.utctimetuple()
    naked_job = "troblodyte{}".format(time.time())
    config = "../config/buildorama.yml"
    logger, tkonf = sh.setup_test_config(config)

    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = tkonf.topLevel('Jenkins')

    jenkins_url = jsh.construct_jenkins_url(jenk_conf)
    r1 = jsh.create_job(jenk_conf, jenkins_url, naked_job)
    assert r1.status_code in [200, 201]
    tkonf.add_to_container({'Job': naked_job})

    # create two build for the same job
    r2 = jsh.build(jenk_conf, jenkins_url, naked_job)
    assert r2.status_code in [200, 201]
    time.sleep(10)
    r2 = jsh.build(jenk_conf, jenkins_url, naked_job)
    assert r2.status_code in [200, 201]

    # find two builds
    target_job_builds = []
    time.sleep(10)
    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)

    for view_project, jobs in builds.items():
        if jobs and naked_job in jobs:  # jobs is dict keyed by the job name with a value of a list of JenkinsBuild instances
            target_job_builds = jobs[naked_job]

    # target_job_builds = [build_info[naked_job] for view_project, build_info  in builds.items() if naked_job in build_info.keys() ]

    for key, val in builds.items():
        # print("key: %s, val: %s" % (key, val))
        print(key)
        # for k, v in val.items():
        #    print("...k: %s, v: %s" % (k, v))
        for builds in val.values():
            for build in builds:
                print("    %s" % build)

    assert len(target_job_builds) == 2

    # delete the job
    r3 = jsh.delete_job(jenk_conf, jenkins_url, naked_job)
    assert r3.status_code == 200

def test_find_builds_of_two_jobs():
    t = datetime.now() - timedelta(minutes=60)
    ref_time = t.utctimetuple()
    job1 = "troblodyte{}".format(time.time())
    job2 = "fukebane{}".format(time.time())
    two_jobs = [job1, job2]
    config = "../config/buildorama.yml"
    logger, tkonf = sh.setup_test_config(config)

    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = tkonf.topLevel('Jenkins')

    jenkins_url = jsh.construct_jenkins_url(jenk_conf)

    r1 = jsh.create_job(jenk_conf, jenkins_url, job1)
    assert r1.status_code in [200, 201]
    tkonf.add_to_container({'Job': job1})

    r1 = jsh.create_job(jenk_conf, jenkins_url, job2)
    assert r1.status_code in [200, 201]
    tkonf.add_to_container({'Job': job2})

    # create two build for the same job
    r2 = jsh.build(jenk_conf, jenkins_url, job1)
    assert r2.status_code in [200, 201]
    time.sleep(10)
    r2 = jsh.build(jenk_conf, jenkins_url, job2)
    assert r2.status_code in [200, 201]

    time.sleep(10)
    # find two builds
    target_job_builds = []
    time.sleep(10)
    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)

    # for view_project, jobs in builds.items():
    #     if jobs and naked_job in jobs:  # jobs is dict keyed by the job name with a value of a list of JenkinsBuild instances
    #         target_job_builds = jobs[naked_job]

    for job_name in two_jobs:
        for view_project, jobs in builds.items():
            if jobs and job_name in jobs:
                target_job_builds.append(jobs[job_name])

    # target_job_builds = [build_info[naked_job] for view_project, build_info  in builds.items() if naked_job in build_info.keys() ]

    for key, val in builds.items():
        # print("key: %s, val: %s" % (key, val))
        print(key)
        # for k, v in val.items():
        #    print("...k: %s, v: %s" % (k, v))
        for builds in val.values():
            for build in builds:
                print("    %s" % build)

    assert len(target_job_builds) == 2

    # delete the jobs
    for job_name in two_jobs:
        r3 = jsh.delete_job(jenk_conf, jenkins_url, job_name)
        assert r3.status_code == 200


def test_find_builds_in_different_containers():
    t = datetime.now() - timedelta(minutes=60)
    ref_time = t.utctimetuple()
    folder_name = "simple amphibian"
    job1 = "naked-troblodyte{}".format(time.time())
    job2 = "foldered-fukebane{}".format(time.time())
    two_jobs = [job1, job2]
    config = "../config/buildorama.yml"
    logger, tkonf = sh.setup_test_config(config)

    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = tkonf.topLevel('Jenkins')

    jenkins_url = jsh.construct_jenkins_url(jenk_conf)

    r0 = jsh.create_folder(jenk_conf, jenkins_url, folder_name)
    assert r0.status_code in [200, 201]

    r1 = jsh.create_job(jenk_conf, jenkins_url, job1)
    assert r1.status_code in [200, 201]
    tkonf.add_to_container({'Job': job1})

    r1 = jsh.create_job(jenk_conf, jenkins_url, job2, folder=folder_name)
    assert r1.status_code in [200, 201]
    tkonf.add_to_container({'Folder': folder_name})

    # create two build for the same job
    r2 = jsh.build(jenk_conf, jenkins_url, job1)
    assert r2.status_code in [200, 201]
    time.sleep(10)
    #r2 = jsh.build(jenk_conf, jenkins_url, job2, folder='Parkour')
    r2 = jsh.build(jenk_conf, jenkins_url, job2, folder=folder_name)
    assert r2.status_code in [200, 201]

    time.sleep(10)
    # find two builds
    target_job_builds = []
    time.sleep(10)
    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)

    for job_name in two_jobs:
        for view_project, jobs in builds.items():
            if jobs and job_name in jobs:
                target_job_builds.append(jobs[job_name])

    # target_job_builds = [build_info[naked_job] for view_project, build_info  in builds.items() if naked_job in build_info.keys() ]

    for key, val in builds.items():
        # print("key: %s, val: %s" % (key, val))
        print(key)
        # for k, v in val.items():
        #    print("...k: %s, v: %s" % (k, v))
        for builds in val.values():
            for build in builds:
                print("    %s" % build)

    assert len(target_job_builds) == 2

    # delete the jobs

    r3 = jsh.delete_job(jenk_conf, jenkins_url, job1)
    assert r3.status_code == 200

    r3 = jsh.delete_job(jenk_conf, jenkins_url, job2, folder=folder_name)
    assert r3.status_code == 200

    r3 = jsh.delete_job(jenk_conf, jenkins_url, folder_name)
    assert r3.status_code == 200

def test_depth():
    t = datetime.now() - timedelta(minutes=60)
    ref_time = t.utctimetuple()
    naked_job = "freddy-flintstone"
    config = "../config/buildorama.yml"
    logger, tkonf = sh.setup_test_config(config)

    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = tkonf.topLevel('Jenkins')

    jc = bsh.JenkinsConnection(jenk_conf, logger)
    assert (jc.connect()) == True

    assert 'freddy-flintstone' not in jc.all_jobs

    ######################### jenk_conf['Jobs'][0] = {'Job':job_name}

    #t = datetime.now() - timedelta(minutes=60)
    #ref_time = t.utctimetuple()


    # config_file = config
    # file_copy = "%sx" % config_file
    # shutil.copyfile(config_file, file_copy)
    # logger, konf = sh.setup_config(file_copy
    # assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    # jenk_conf = konf.topLevel('Jenkins')
    # jenkins_url = jsh.construct_jenkins_url(jenk_conf)
    # #assert jenk_conf['Jobs'][0]['Job'] == job_name
    # jc = bsh.JenkinsConnection(jenk_conf, logger)
    # jc.connect()
    # builds = jc.getRecentBuilds(ref_time)
    # assert (job_name in builds["All::%s" % jenk_conf['AgileCentral_DefaultBuildProject']]) == True
    # print("config: %s   job: %s    number of builds: %d" % (file_copy, job_name, len(builds)))





