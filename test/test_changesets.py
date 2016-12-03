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
from bldeif.utils.konfabulus import Konfabulator
from bldeif.agicen_bld_connection import AgileCentralConnection

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
    repo_name = 'wombats'
    vcs = 'git'
    jc = connect_to_jenkins(STANDARD_CONFIG)
    assert jc.connect()
    jobs = jc.inventory.jobs
    assert next((job for job in jobs if job.name == target_job))
    jc.views = []
    jc.jobs  = []
    del jc.folders[1]
    assert jc.folders

    t = datetime.now() - timedelta(days=1)
    ref_time = t.utctimetuple()
    builds = jc.getRecentBuilds(ref_time)
    for build_info in builds.values():
        for builds in build_info.values():
            for build in builds:
                if build.number != magic_number:
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
        'chocolate': ['DE1','US1','DE3'],
        'bacon'    : ['US4'],
        'broccoli' : []
    }

    logger = ActivityLogger('kublakhan.log')
    konf = Konfabulator('config/buildorama.yml', logger)
    jenk_conf = konf.topLevel('Jenkins')
    ac_conf = konf.topLevel('AgileCentral')
    ac_conf['Project'] = jenk_conf['AgileCentral_DefaultBuildProject'] #leak proj from jenkins section to ac section
    agicen = AgileCentralConnection(ac_conf, logger)
    agicen.other_name = 'FoobarRulz'
    assert agicen.connect()
    result = agicen.validatedArtifacts(commit_fid)
    assert result['bacon']    == []
    assert result['broccoli'] == []
    #assert result['chocolate'][0].FormattedID == 'DE1'
    valid_chocolates = ['DE1', 'US1']
    assert sorted([a.FormattedID for a in result['chocolate']]) == valid_chocolates

    assert  [art.FormattedID for artifacts in result.values() for art in artifacts if art.FormattedID == 'US1'][0] == 'US1'
    # teeny more complex...
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
    artifacts = [art.ref for art in response]
    #artifacts = [art for art in response]
    scm_repo = agicen_conn.agicen.get('SCMRepository', fetch="Name,ObjectID", query = '(Name =  wombat)', instance = True)
    bogus_changeset_payload = {
        'SCMRepository': scm_repo.ref,
        'Revision': 'aa1123',
        'CommitTimestamp': '2016-12-04',
        'Artifacts': artifacts
    }
    assert bogus_changeset_payload['Artifacts'] is not None
    changeset = agicen_conn.agicen.create('Changeset', bogus_changeset_payload)
    assert changeset is not None
    assert len(changeset.Artifacts) == 2
    print(changeset.oid)


