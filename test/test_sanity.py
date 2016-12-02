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
    result = mock_build.id_as_ts < ref_time
    assert result == False


def test_folder_config():
    t = datetime.now() - timedelta(minutes=60)
    ref_time = t.utctimetuple()
    folder = "A{}".format(time.time())
    job_name = "frog"

    config = "config/buildorama.yml"
    logger, tkonf = sh.setup_test_config(config)
    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = tkonf.topLevel('Jenkins')
    jenkins_url = jsh.construct_jenkins_url(jenk_conf)

    # create a jenkins folder and a job in the folder
    r0 = jsh.create_folder(jenk_conf, jenkins_url, folder)
    assert r0.status_code in [200, 201]

    r1 = jsh.create_job(jenk_conf, jenkins_url, job_name, folder=folder)
    assert r1.status_code in [200, 201]

    # build in jenkins
    r2 = jsh.build(jenk_conf, jenkins_url, job_name, folder=folder)
    assert r2.status_code in [200, 201]
    time.sleep(10)

    tkonf.topLevel('Jenkins')['AgileCentral_DefaultBuildProject'] = 'Dunder Donut'
    tkonf.add_to_container({'Folder': folder})
    assert tkonf.has_item('Folder', folder)

    jenk_conf = tkonf.topLevel('Jenkins')
    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)

    assert (job_name in builds["%s::%s" % (folder, jenk_conf['AgileCentral_DefaultBuildProject'])]) == True

    r3 = jsh.delete_job(jenk_conf, jenkins_url, job_name, folder=folder)
    assert r3.status_code == 200

    r3 = jsh.delete_job(jenk_conf, jenkins_url, folder)
    assert r3.status_code == 200

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
    folder1 = "friendly amphibian{}".format(time.time())
    folder2 = "unfriendly amphibian{}".format(time.time())

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
    #tkonf.add_to_container({'Folder': folder2})

    # create a job in a folder in Jenkins but do not add this folder name to config
    r1 = jsh.create_job(jenk_conf, jenkins_url, job3, folder=folder2)
    assert r1.status_code in [200, 201]

    # check if new containers were added
    assert tkonf.has_item('Folder', folder1)
    #assert tkonf.has_item('Folder', folder2)

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
    folder1  = "A1{}".format(time.time())
    folder2  = "A2{}".format(time.time())
    job_name = "frog"

    config = "config/buildorama.yml"
    logger, tkonf = sh.setup_test_config(config)
    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    agicen_konf =  tkonf.topLevel('AgileCentral')
    agicen_konf['Workspace'] = 'Alligators BLD Unigrations'
    tkonf.topLevel('Jenkins')['AgileCentral_DefaultBuildProject'] = 'Jenkins'
    jenk_conf = tkonf.topLevel('Jenkins')
    jenkins_url = jsh.construct_jenkins_url(jenk_conf)

    r0 = jsh.create_folder(jenk_conf, jenkins_url, folder1)
    assert r0.status_code in [200, 201]
    r0 = jsh.create_folder(jenk_conf, jenkins_url, folder2)
    assert r0.status_code in [200, 201]

    r1 = jsh.create_job(jenk_conf, jenkins_url, job_name, folder=folder1)
    assert r1.status_code in [200, 201]

    r1 = jsh.create_job(jenk_conf, jenkins_url, job_name, folder=folder2)
    assert r1.status_code in [200, 201]

    tkonf.add_to_container({'Folder': folder1, 'AgileCentral_Project': 'Dunder Donut'})
    tkonf.add_to_container({'Folder': folder2, 'AgileCentral_Project': 'Corral'})
    tkonf.remove_from_container({'Folder' : 'Parkour'})
    tkonf.remove_from_container({'View': 'Shoreline'})
    tkonf.remove_from_container({'Job': 'truculent elk medallions'})

    assert tkonf.has_item('Folder', folder1)
    assert tkonf.has_item('Folder', folder2)
    assert tkonf.has_item('Folder', 'Parkour') == False

    ref_time = datetime.now() - timedelta(minutes=5)

    jenkins_url = jsh.construct_jenkins_url(jenk_conf)

    r1 = jsh.build(jenk_conf, jenkins_url, job_name, folder=folder1)
    assert r1.status_code in [200, 201]
    time.sleep(10)

    r2 = jsh.build(jenk_conf, jenkins_url, job_name, folder=folder2)
    assert r2.status_code in [200, 201]
    time.sleep(10)

    assert folder1 in [folder_rec['Folder'] for folder_rec  in jenk_conf['Folders']]
    assert folder2 in [folder_rec['Folder'] for folder_rec  in jenk_conf['Folders']]
    assert 'Parkour' not in [folder_rec['Folder'] for folder_rec  in jenk_conf['Folders']]

    # find two builds
    target_job_builds = []
    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    jenkins_builds = jc.getRecentBuilds(ref_time.utctimetuple())

    target_job_builds = [build_info[job_name] for view_project, build_info  in jenkins_builds.items() if job_name in build_info.keys() ]
    bc = bsh.BLDConnector(tkonf, logger)

    agicen = bc.agicen_conn.agicen
    query = ['CreationDate >= %s' % ref_time.isoformat()]
    for view_proj, build_view in jenkins_builds.items():
        print(view_proj)
        for builds in build_view.values():
            for build in builds:
                print("    %s" % build)
                project = view_proj.split('::')[1]
                print ("PROJECT %s" %project)
                build_defn = bc.agicen_conn.ensureBuildDefinitionExists(job_name, project, build.url)
                assert build_defn.Project.Name == project
                agicen_build = bc.postBuildsToAgileCentral(build_defn, build, [], job_name)
                assert agicen_build is not None
                assert agicen_build.BuildDefinition.Project.Name == project

                ac_response = bc.agicen_conn._retrieveBuilds(project, query)
                for build in ac_response:
                    print("    %24.24s Job Name: %24.24s build number: %s " % (build.BuildDefinition.Project.Name, build.BuildDefinition.Name, build.Number))
                for build in ac_response:
                    assert (build.BuildDefinition.Project.Name) == project
                    assert (build.BuildDefinition.Name) == job_name

    # delete the jobs

    r3 = jsh.delete_job(jenk_conf, jenkins_url, job_name, folder=folder1)
    assert r3.status_code == 200

    r3 = jsh.delete_job(jenk_conf, jenkins_url, job_name, folder=folder2)
    assert r3.status_code == 200

    r3 = jsh.delete_job(jenk_conf, jenkins_url, folder1)
    assert r3.status_code == 200

    r3 = jsh.delete_job(jenk_conf, jenkins_url, folder2)
    assert r3.status_code == 200

def test_depth():
    t = datetime.now() - timedelta(minutes=2)
    ref_time = t.utctimetuple()
    naked_job = "freddy-flintstone"
    config = "config/buildorama.yml"
    logger, tkonf = sh.setup_test_config(config)

    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = tkonf.topLevel('Jenkins')

    jc = bsh.JenkinsConnection(jenk_conf, logger)
    assert (jc.connect()) == True

    assert 'freddy-flintstone' not in jc.all_jobs

def test_existing_job():
    ref_time = datetime.now() - timedelta(minutes=2)
    folder = "immovable wombats"
    my_job = "Top"
    other_job = "Carver"
    jobs = [my_job, other_job ]
    jc = sh.build_immovable_wombats(folder, jobs)
    time.sleep(10)
    builds = jc.getRecentBuilds(ref_time.utctimetuple())
    #target_job_builds = [build_info[my_job] for container_proj, build_info in builds.items() if my_job in build_info.keys()][0]
    #print (target_job_builds)

    jobs_snarfed = []
    builds_snarfed = []
    for container_proj, build_info in builds.items():
        print (container_proj)
        for job, builds in build_info.items():
            jobs_snarfed.append(job)
            builds_snarfed.extend(builds)
            print (builds)
    assert other_job not in jobs_snarfed
    assert my_job in jobs_snarfed

    print ("FAMOUS WAMBATS-----------------")

    ref_time = datetime.now() - timedelta(minutes=10)
    folder = "immovable wombats"
    my_job = "Top"
    other_job = "Carver"
    jobs = [my_job, other_job]
    jc = sh.build_immovable_wombats(folder, jobs)
    time.sleep(10)
    builds = jc.getRecentBuilds(ref_time.utctimetuple())
    # target_job_builds = [build_info[my_job] for container_proj, build_info in builds.items() if my_job in build_info.keys()][0]
    # print (target_job_builds)

    more_jobs_snarfed = []
    more_builds_snarfed = []
    for container_proj, build_info in builds.items():
        print (container_proj)
        for job, builds in build_info.items():
            more_jobs_snarfed.append(job)
            more_builds_snarfed.extend(builds)
            print (builds)
    assert other_job not in jobs_snarfed
    assert my_job in more_jobs_snarfed

    assert len(more_builds_snarfed) > len(builds_snarfed)


