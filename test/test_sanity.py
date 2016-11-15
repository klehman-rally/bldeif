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
from bldeif.bld_connector import BLDConnector

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
    konf = bsh.Konfabulator('config/trumpkin.yaml', logger)
    jenkins_conf = konf.topLevel('Jenkins')
    jc = bsh.JenkinsConnection(jenkins_conf, logger)
    result = jc.jobBeforeRefTime(mock_build, ref_time)
    assert result == False


def test_folder_config():
    t = datetime.now() - timedelta(minutes=60)
    ref_time = t.utctimetuple()
    folder = "A1"
    job_name = "frog"

    config = "config/buildorama.yml"
    logger, tkonf = sh.setup_test_config(config)
    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']

    tkonf.topLevel('Jenkins')['AgileCentral_DefaultBuildProject'] = 'Dunder Donut'
    tkonf.add_to_container({'Folder': folder})
    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = tkonf.topLevel('Jenkins')

    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)
    assert (job_name in builds["%s::%s" % (folder, jenk_conf['AgileCentral_DefaultBuildProject'])]) == True


def test_test_konfabulator():
    logger = ActivityLogger('test.log')
    filename = "config/buildorama.yml"
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
    config_path = "config/buildorama.yml"
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
    config = "config/buildorama.yml"
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
    config = "config/buildorama.yml"
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
    config = "config/buildorama.yml"
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
    folder1 = "friendly amphibian"
    folder2 = "unfriendly amphibian"

    job1 = "naked-troblodyte{}".format(time.time())
    job2 = "foldered-fukebane{}".format(time.time())
    job3 = "ignore-it{}".format(time.time())

    three_jobs = [job1, job2, job3]
    config = "config/buildorama.yml"
    logger, tkonf = sh.setup_test_config(config)

    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = tkonf.topLevel('Jenkins')

    jenkins_url = jsh.construct_jenkins_url(jenk_conf)

    r0 = jsh.create_folder(jenk_conf, jenkins_url, folder1)
    assert r0.status_code in [200, 201]

    r0 = jsh.create_folder(jenk_conf, jenkins_url, folder2)
    assert r0.status_code in [200, 201]

    r1 = jsh.create_job(jenk_conf, jenkins_url, job1)
    assert r1.status_code in [200, 201]
    tkonf.add_to_container({'Job': job1})

    r1 = jsh.create_job(jenk_conf, jenkins_url, job2, folder=folder1)
    assert r1.status_code in [200, 201]
    tkonf.add_to_container({'Folder': folder1})

    # create a job in a folder in Jenkins but do not add this folder name to config
    r1 = jsh.create_job(jenk_conf, jenkins_url, job3, folder=folder2)
    assert r1.status_code in [200, 201]

    # check if new containers were added
    assert tkonf.has_item('Job', job1)
    assert tkonf.has_item('Folder', folder1)
    assert tkonf.has_item('Folder', folder2) == False

    # create two builds for the same job
    r2 = jsh.build(jenk_conf, jenkins_url, job1)
    assert r2.status_code in [200, 201]
    time.sleep(10)

    r2 = jsh.build(jenk_conf, jenkins_url, job2, folder=folder1)
    assert r2.status_code in [200, 201]
    time.sleep(10)

    r2 = jsh.build(jenk_conf, jenkins_url, job3, folder=folder2)
    assert r2.status_code in [200, 201]
    time.sleep(10)


    # find two builds: a build for job3 should not be found
    target_job_builds = []
    time.sleep(10)
    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)

    for job_name in three_jobs:
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

    r3 = jsh.delete_job(jenk_conf, jenkins_url, job2, folder=folder1)
    assert r3.status_code == 200

    r3 = jsh.delete_job(jenk_conf, jenkins_url, job3, folder=folder2)
    assert r3.status_code == 200

    r3 = jsh.delete_job(jenk_conf, jenkins_url, folder1)
    assert r3.status_code == 200

    r3 = jsh.delete_job(jenk_conf, jenkins_url, folder2)
    assert r3.status_code == 200

def test_same_name_jobs_in_diff_folders():
    folder1  = "A1"
    folder2  = "A2"
    job_name = "frog"

    config = "config/buildorama.yml"
    logger, tkonf = sh.setup_test_config(config)
    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    agicen_konf =  tkonf.topLevel('AgileCentral')
    agicen_konf['Workspace'] = 'Alligators BLD Unigrations'
    tkonf.topLevel('Jenkins')['AgileCentral_DefaultBuildProject'] = 'Jenkins'
    tkonf.add_to_container({'Folder': folder1, 'AgileCentral_Project': 'Dunder Donut'})
    tkonf.add_to_container({'Folder': folder2, 'AgileCentral_Project': 'Corral'})
    tkonf.remove_from_container({'Folder' : 'Parkour'})
    tkonf.remove_from_container({'View': 'Shoreline'})
    tkonf.remove_from_container({'Job': 'truculent elk medallions'})
    assert tkonf.has_item('Folder', folder1)
    assert tkonf.has_item('Folder', folder2)
    assert tkonf.has_item('Folder', 'Parkour') == False

    ref_time = datetime.now() - timedelta(minutes=5)


    jenk_conf = tkonf.topLevel('Jenkins')
    jenkins_url = jsh.construct_jenkins_url(jenk_conf)

    r1 = jsh.build(jenk_conf, jenkins_url, job_name, folder=folder1)
    assert r1.status_code in [200, 201]
    time.sleep(10)

    r2 = jsh.build(jenk_conf, jenkins_url, job_name, folder=folder2)
    assert r2.status_code in [200, 201]
    time.sleep(10)

    # find two builds
    target_job_builds = []
    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time.utctimetuple())

    target_job_builds = [build_info[job_name] for view_project, build_info  in builds.items() if job_name in build_info.keys() ]
    bc = bsh.BLDConnector(tkonf, logger)


    agicen = bc.agicen_conn.agicen
    query = ['CreationDate >= %s' % ref_time.isoformat()]
    for view_proj, build_view in builds.items():
        print(view_proj)
        for builds in build_view.values():
            for build in builds:
                print("    %s" % build)
                project = view_proj.split('::')[1]
                print ("PROJECT %s" %project)
                build_defn = bc.agicen_conn.ensureBuildDefinitionExistence(job_name, project, True, build.url)
                build_data = build.as_tuple_data()
                info = bsh.OrderedDict(build_data)
                agicen_build = bc.postBuildsToAgileCentral(info, build_defn, build)
                assert agicen_build is not None
                ac_response = bc.agicen_conn._retrieveBuilds(project, query)
                for build in ac_response:
                    assert (build.BuildDefinition.Project.Name) == project
                    assert (build.BuildDefinition.Name) == job_name


def test_depth():
    t = datetime.now() - timedelta(minutes=60)
    ref_time = t.utctimetuple()
    naked_job = "freddy-flintstone"
    config = "config/buildorama.yml"
    logger, tkonf = sh.setup_test_config(config)

    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = tkonf.topLevel('Jenkins')

    jc = bsh.JenkinsConnection(jenk_conf, logger)
    assert (jc.connect()) == True

    assert 'freddy-flintstone' not in jc.all_jobs






