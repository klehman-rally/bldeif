import sys, os
import time
import yaml
import shutil
import pytest
import spec_helper         as sh
import build_spec_helper   as bsh
import jenkins_spec_helper as jsh
from datetime import datetime, timedelta



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
    jc.validate()
    jenkins_builds = jc.getRecentBuilds(ref_time.utctimetuple())

    bc = bsh.BLDConnector(tkonf, logger)
    query = ['CreationDate >= %s' % ref_time.isoformat()]
    for view_proj, build_view in jenkins_builds.items():
        print(view_proj)
        for builds in build_view.values():
            for bld in builds:
                print("    %s" % bld)
                project = view_proj.split('::')[1]
                print ("PROJECT %s" %project)
                build_defn = bc.agicen_conn.ensureBuildDefinitionExists(job_name, project, bld.url)
                assert build_defn.Project.Name == project
                agicen_build, status = bc.postBuildToAgileCentral(build_defn, bld, [], job_name)
                assert agicen_build is not None
                assert agicen_build.BuildDefinition.Project.Name == project
                ac_response = bc.agicen_conn._retrieveBuilds(project, query)
                for build in ac_response:
                    print("    %24.24s Job Name: %24.24s build number: %s " % (build.BuildDefinition.Project.Name, build.BuildDefinition.Name, build.Number))
                    if build.BuildDefinition.Project.Name != project:
                        for proj in bc.agicen_conn.build_def.keys():
                            print("build_defn project: %s" % proj)
                            project_jobs = bc.agicen_conn.build_def[proj].keys()
                            for job in project_jobs:
                                print("    %s:   %s" % (job, bc.agicen_conn.build_def[proj][job].Project.Name))
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