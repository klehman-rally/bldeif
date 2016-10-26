import sys, os
import time
import yaml
import pytest
import spec_helper         as  sh
import build_spec_helper   as bsh
#import jenkins_spec_helper as jsh
from datetime import datetime, timedelta
from collections import OrderedDict


@pytest.fixture
def setup_config(filename, simple=True):
    aci = sh.AC_Creds_Inflator(sh.DEFAULT_AGILE_CENTRAL_SERVER, sh.DEFAULT_AC_API_KEY, None, None,
                               sh.DEFAULT_AC_WORKSPACE)

    if simple:
        config_raw = sh.SIMPLE_CONFIG_STRUCTURE.replace('<!AC_CREDS_INFO!>', str(aci))
    else:
        config_raw = sh.CONFIG_STRUCTURE_WITH_FOLDERS.replace('<!AC_CREDS_INFO!>', str(aci))
    with open(filename, 'w') as out:
        out.write(config_raw)

    logger = sh.ActivityLogger('test.log')
    konf = sh.Konfabulator(filename, logger)
    return logger, konf


def test_me():
    assert(1) == 1


def test_create_build_with_no_commits():
    filename = "../config/intwin7.yml"
    logger, konf = setup_config(filename, False)

    konf.topLevel('AgileCentral')['Project'] = 'Sandbox'
    agicen = bsh.AgileCentralConnection(konf.topLevel('AgileCentral'), logger)
    agicen.other_name = 'Jenkins'
    agicen.connect()
    build_start = int((datetime.now() - timedelta(minutes=60)).timestamp())
    build_name = 'Willy Wonka stirs the chocolate'
    job_name, build_number, status  = '%s' %build_name, 532, 'SUCCESS'
    started, duration = build_start, 231
    commits = []
    build = bsh.MockJenkinsBuild(job_name, build_number, status, started, duration, commits)
    build.url = "http://jenkey.dfsa.com:8080/job/bashfulmonkies/532"
    build_job_uri = "/".join(build.url.split('/')[:-2])

    build_defn = agicen.ensureBuildDefinitionExistence(job_name, 'Sandbox', True, build_job_uri)
    assert build_defn is not None

    changesets = agicen.matchToChangesets(commits)
    assert len(changesets) == 0

    binfo = OrderedDict(build.as_tuple_data())
    binfo['BuildDefinition'] = build_defn
    agicen_build = agicen.createBuild(binfo)
    assert agicen_build is not None
    assert int(agicen_build.Number) == 532

    query = 'BuildDefinition.Name = "%s"' % build_name
    workspace = konf.topLevel('AgileCentral')['Workspace']
    response = agicen.agicen.get('Build', fetch='ObjectID,Name,BuildDefinition,Number', query=query, workspace=workspace, project=None)
    assert response.resultCount > 0
    a_build = response.next()
    assert a_build.BuildDefinition.Name == build_name
    assert int(a_build.Number) == 532

def test_create_build_having_commits():
    ref_time = datetime.now().utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    # get a konf and a logger,
    filename = "../config/intwin7.yml"
    logger, konf = setup_config(filename, False)
    konf.topLevel('AgileCentral')['Project'] = 'Sandbox'   # specify the Workspace

    # get an AgileCentralConnection
    agicen = bsh.AgileCentralConnection(konf.topLevel('AgileCentral'), logger)
    agicen.other_name = 'Jenkins'
    agicen.connect()

    # mock up a Build
    build_start = int((datetime.now() - timedelta(minutes=60)).timestamp())
    build_name = 'Hungry kids devour our tasty product'
    job_name, build_number, status  = '%s' %build_name, 74, 'SUCCESS'
    started, duration = build_start, 43
    # use some SHA values corresponding to some actual Agile Central Changeset items in our target Workspace
    commits = ['CHOCOLATE', 'MORE CHOCOLATE']
    build = bsh.MockJenkinsBuild(job_name, build_number, status, started, duration, commits)
    build.url = "http://jenkey.dfsa.com:8080/job/hugrycats/%s" % build_number
    build_job_uri = "/".join(build.url.split('/')[:-2])


    # run the same code as above to matchToChangesets
    # assert that some were found
    build_defn = agicen.ensureBuildDefinitionExistence(job_name, 'Sandbox', True, build_job_uri)
    assert build_defn is not None

    changesets = agicen.matchToChangesets(commits)
    assert len(changesets) == 2

    # confabulate a build_info dict with Changesets = list of matching AgileCentral Changesets
    # call agicen.createBuild(build_info)
    binfo = OrderedDict(build.as_tuple_data())
    binfo['BuildDefinition'] = build_defn
    binfo['Changesets'] = changesets
    agicen_build = agicen.createBuild(binfo)
    # assert that the Build was created
    assert agicen_build is not None
    # assert that the build number is correct
    assert int(agicen_build.Number) == build_number

    # use agicen.agicen.get('Build',...) to find the newly created Build item
    query = ['BuildDefinition.Name = "%s"' % build_name]
    query.append('Number = "%s"' % build_number)
    query.append('CreationDate >= %s' % ref_time)
    workspace = konf.topLevel('AgileCentral')['Workspace']
    response = agicen.agicen.get('Build', fetch='ObjectID,Name,BuildDefinition,Number,Changesets', query=query,
                                 workspace=workspace, project=None)

    # assert that the build has a Changesets attribute value that has a collection attribute
    assert response.resultCount > 0
    a_build = response.next()
    assert a_build.BuildDefinition.Name == build_name
    assert int(a_build.Number) == build_number

    # assert that the Changesets returned are indeed the target Changesets (no more, no less)
    changesets = [cs for cs in a_build.Changesets]
    assert len(changesets) >= 2
    assert ('MORE CHOCOLATE' in [cs.Revision for cs in changesets]) == True
    print("loons are crazy %s" % len(changesets))


