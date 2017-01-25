import os, sys
import re
import yaml
import json
import time
import requests
from datetime import datetime, timedelta, date
from bldeif.bld_connector    import BLDConnector
from bldeif.utils.time_file  import TimeFile
import build_spec_helper   as bsh
import spec_helper as sh
from bldeif.utils.klog       import ActivityLogger
from bldeif.bld_connector_runner import BuildConnectorRunner
from bldeif.utils.konfabulus import Konfabulator
from bldeif.agicen_bld_connection import AgileCentralConnection
import utility as util

STANDARD_CONFIG  = 'honey-badger.yml'
MIN_CONFIG1      = 'bluestem.yml'
MIN_CONFIG2      = 'cliffside.yml'
MIN_CONFIG3      = 'crinkely.yml'
BAD_CONFIG1      = 'attila.yml'
BAD_CONFIG2      = 'genghis.yml'
BAD_CONFIG3      = 'caligula.yml'
SHALLOW_CONFIG   = 'shallow.yml'
DEEP_CONFIG      = 'deepstate.yml'
SVN_CONFIG       = 'sarajevo.yml'
PIPE_CONFIG      = 'pipe.yml'

def connect_to_jenkins(config_file):
    config_file = "config/{}".format(config_file)
    jenk_conf = {}
    with open(config_file, 'r') as cf:
        content = cf.read()
        all_conf = yaml.load(content)
        jenk_conf = all_conf['JenkinsBuildConnector']['Jenkins']

    jc = bsh.JenkinsConnection(jenk_conf, ActivityLogger('inventory.log'))
    return jc

def connect_to_ac(config_file):
    logger = ActivityLogger('kublakhan.log')
    konf = Konfabulator('config/buildorama.yml', logger)
    jenk_conf = konf.topLevel('Jenkins')
    ac_conf = konf.topLevel('AgileCentral')
    ac_conf['Project'] = jenk_conf['AgileCentral_DefaultBuildProject']  # leak proj from jenkins section to ac section
    agicen = AgileCentralConnection(ac_conf, logger)
    agicen.other_name = 'Jenkins'
    agicen.connect()
    return agicen

def test_Top_changesets():
    target_job = 'Top'
    magic_number = 71
    magic_date   = date(2016,11,29)
    days_offset  = (datetime.now().date() - magic_date).days
    repo_name = 'wombats'
    vcs = 'git'
    jc = connect_to_jenkins(STANDARD_CONFIG)
    assert jc.connect()
    jc.validate()
    jobs = jc.inventory.jobs
    assert next((job for job in jobs if job.name == target_job))
    jc.views = []
    jc.jobs  = []
    del jc.folders[1]
    assert jc.folders

    t = datetime.now() - timedelta(days=days_offset)
    ref_time = t.utctimetuple()
    builds = jc.getRecentBuilds(ref_time)
    for build_info in builds.values():
        for builds in build_info.values():
            for build in builds:
                if build.number != magic_number or build.name != target_job:
                    continue
                #print(build)
                print (build.repository)
                assert build.repository == repo_name
                assert build.changeSets
                assert build.changeSets[0].vcs == vcs
                # for changeset in build.changeSets:
                #    print(changeset)


def test_validatedArtifacts():
    commit_fid = {
        'chocolate': ['DE1','US1','DE2'],
        'bacon'    : ['US4'],
        'broccoli' : []
    }
    agicen = connect_to_ac('config/buildorama.yml')
    result = agicen.validatedArtifacts(commit_fid)
    assert result['bacon']    == []
    assert result['broccoli'] == []
    valid_chocolates = ['DE1', 'US1']
    assert sorted([a.FormattedID for a in result['chocolate']]) == valid_chocolates

    assert  [art.FormattedID for artifacts in result.values() for art in artifacts if art.FormattedID == 'US1'][0] == 'US1'

    commit_fid['vanilla'] = ['US1', 'US2', 'US12']
    valid_vanillas = ['US1', 'US2']
    result = agicen.validatedArtifacts(commit_fid)
    assert sorted([a.FormattedID for a in result['vanilla']]) == valid_vanillas
    commit_fid['chocolate'] = ['US1', 'US1', 'US1']
    valid_chocolates = ['US1']
    result = agicen.validatedArtifacts(commit_fid)
    assert sorted([a.FormattedID for a in result['chocolate']]) == valid_chocolates
    commit_fid = {}
    result = agicen.validatedArtifacts(commit_fid)
    assert len(result) == 0


def test_changeset_creation_with_artifacts_collection():
    query = '((FormattedID = US1) OR (FormattedID = DE1))'
    agicen_conn = connect_to_ac('config/buildorama.yml')
    response = agicen_conn.agicen.get('Artifact', fetch="Name,ObjectID,FormattedID",query=query,project=None)
    #artifacts = [art.ref for art in response]
    artifacts = [art for art in response]
    scm_repo = agicen_conn.ensureSCMRepositoryExists('wombat', 'git')
    scm_repo = agicen_conn.agicen.get('SCMRepository', fetch="Name,ObjectID", query = '(Name = wombat)', project=None, instance = True)
    dt = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'
    bogus_changeset_payload = {
        'SCMRepository': scm_repo.ref,
        'Revision': 'aa1123',
        'CommitTimestamp': dt, #'2016-12-04',
        'Artifacts': artifacts
    }
    assert bogus_changeset_payload['Artifacts'] is not None
    changeset = agicen_conn.agicen.create('Changeset', bogus_changeset_payload)
    assert changeset is not None
    assert len(changeset.Artifacts) == 2
    print(changeset.oid)

    dt = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'
    bogus_changeset_payload = {
        'SCMRepository': scm_repo.ref,
        'Revision': 'aa1124',
        'CommitTimestamp': dt,  # '2016-12-04',
        'Artifacts': artifacts
    }
    changeset = agicen_conn.agicen.create('Changeset', bogus_changeset_payload)
    assert changeset is not None
    assert len(changeset.Artifacts) == 2
    print(changeset.oid)


def test_ensureSCMRepositoryExists():
    ultimate_repo_name = 'wombat'
    util.delete_scm_repo(ultimate_repo_name)
    agicen_conn = connect_to_ac('config/buildorama.yml')

    name = 'alpha/wombat/.git'
    scm_type = 'git'
    #repo = util.create_scm_repo(name, scm_type)
    item = {
        "commitId": "a7f48eb99ac8064c65a1fde3239cb8094bac8709foobar",
        "timestamp": 1480550939000,
        "msg": "DE1000 wombats stink",
        "date": "2016-11-30 19:08:59 -0500",
        "paths": [{"editType": "edit","file": "foobar"}]
    }
    bogus_raw = {'id':'666','number':'42', 'result':'SUCCESS',
                 '_class'    : 'hudson.model.FreeStyleBuild',
                 'timestamp' : int(time.time()),
                 'duration'  : 1000, 'url': 'http://xyz:8080',
                 'actions'   : [{'remoteUrls': [name]}],
                 'changeSet' : {'kind':'git','items':[item]}}
    build1 = bsh.JenkinsBuild('DownWithCoalaBears', bogus_raw)
    assert build1.repository   == 'wombat'

    #changesets, build_defn = agicen_conn.prepAgileCentralBuildPrerequisites(build1, agicen_conn.project_name)
    repo1 = agicen_conn.ensureSCMRepositoryExists(build1.repository, scm_type)

    name = 'beta/wombat/.git'
    scm_type = 'git'
    bogus_raw = {'id': '123', 'number': '1', 'result': 'SUCCESS',
                 '_class': 'hudson.model.FreeStyleBuild',
                 'timestamp': int(time.time()),
                 'duration': 1000, 'url': 'http://xyz:8080',
                 'actions': [{'remoteUrls': [name]}],
                 'changeSet': {'kind': 'git', 'items': [item]}}
    build2 = bsh.JenkinsBuild('WombatsRUs', bogus_raw)
    assert build2.repository   == 'wombat'
    repo2 = agicen_conn.ensureSCMRepositoryExists(build2.repository, scm_type)
    assert repo1.ObjectID == repo2.ObjectID
    assert build1.repository == build2.repository


# This test used to work with Subversion prior to 1.9.4 and Subversion plugin 1.5.7.
# It no longer works
# def test_build_with_SVN_commit():
#     jc = connect_to_jenkins(SVN_CONFIG)
#     assert jc.connect()
#     folder_job_builds_url = "http://localhost:8080/job/sarajevo/job/parade/api/json?tree=builds[number,id,description,timestamp,duration,result,url,actions[remoteUrls],changeSet[*[*[*]]]]"
#     jenkins_json = requests.get(folder_job_builds_url, auth=jc.creds).json()
#     raw_builds = jenkins_json['builds']
#     some_build_num = 2
#     build = [build for build in raw_builds if build['number'] == some_build_num][0]
#     assert build['changeSet']['kind'] == 'svn'
#     actions   = build['actions']
#     revisions = build['changeSet']['revisions']
#
#     assert     [bld for bld in actions    for k,v in bld.items() if k == '_class']
#     assert not [bld for bld in actions    for k,v in bld.items() if k == 'remoteUrls' ]
#     assert     [rev for rev in revisions  for k,v in rev.items() if k == 'module' ]
#     assert     [rev for rev in revisions  for k,v in rev.items() if k == 'revision']
#
#     assert revisions[0]['revision'] == 2
#     assert revisions[0]['module'] == 'file:///Users/pairing/svn-repo-sarajevo'

def test_build_with_GIT_commit():
    jc = connect_to_jenkins(STANDARD_CONFIG)
    assert jc.connect()
    folder_job_builds_url = "http://tiema03-u183073.ca.com:8080/job/immovable%20wombats/job/Top/api/json?tree=builds[number,id,description,timestamp,duration,result,url,actions[remoteUrls],changeSet[*[*[*]]]]"
    raw_builds = requests.get(folder_job_builds_url, auth=jc.creds).json()['builds']

    some_build_num = raw_builds[-1]['number']
    build = [build for build in raw_builds if build['number'] == some_build_num][0]
    assert build['changeSet']['kind'] == 'git'
    assert 'revisions' not in build['changeSet']
    assert [bld for bld in build['actions'] for k,v in bld.items() if k == 'remoteUrls' ]

def test_pipeline_changesets():
    jc = connect_to_jenkins(PIPE_CONFIG)
    assert jc.connect()
    job_builds_url = "http://tiema03-u183073.ca.com:8080/job/pipe%20dream/api/json?tree=builds[number,id,description,timestamp,duration,result,url,actions[remoteUrls],changeSets[*[*[*]]]]"
    raw_builds = requests.get(job_builds_url, auth=jc.creds).json()['builds']
    some_build_num = 9
    build = [build for build in raw_builds if build['number'] == some_build_num][0]
    for changeset in build['changeSets']:
        assert changeset['kind'] == 'git'

    assert [bld for bld in build['actions'] for k, v in bld.items() if k == 'remoteUrls']


# def test_SVN_changesets():
#     target_job = 'parade'
#     magic_number = 2
#     magic_date   = date(2016,12,8)
#     repo_name = 'svn-repo-sarajevo'
#     vcs = 'svn'
#     days_offset  = (datetime.now().date() - magic_date).days
#     jc = connect_to_jenkins(SVN_CONFIG)
#     assert jc.connect()
#     assert jc.validate()
#     jobs = jc.inventory.jobs
#     assert next((job for job in jobs if job.name == target_job))
#     jc.views = []
#     jc.jobs  = []
#     assert jc.folders
#
#     t = datetime.now() - timedelta(days=days_offset)
#     ref_time = t.utctimetuple()
#     builds = jc.getRecentBuilds(ref_time)
#     for build_info in builds.values():
#         for builds in build_info.values():
#             for build in builds:
#                 if build.number != magic_number or build.name != target_job:
#                     continue
#                 print(build)
#                 print (build.repository)
#                 assert build.repository == repo_name
#                 assert build.changeSets
#                 assert build.changeSets[0].vcs == vcs



