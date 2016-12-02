import sys, os
import time
import yaml
import pytest
import spec_helper         as  sh
import build_spec_helper   as bsh
#import jenkins_spec_helper as jsh
from datetime import datetime, timedelta
from collections import OrderedDict


def test_create_build_with_no_commits():
    #filename = "../config/buildorama.yml"
    filename = "config/buildorama.yml"
    logger, konf = sh.setup_config(filename)

    konf.topLevel('AgileCentral')['Project'] = 'Jenkins'
    agicen = bsh.AgileCentralConnection(konf.topLevel('AgileCentral'), logger)
    agicen.other_name = 'Jenkins'
    agicen.connect()
    agicen.validateProjects(['Jenkins'])
    build_start = int((datetime.now() - timedelta(minutes=60)).timestamp())
    build_name = 'Willy Wonka stirs the chocolate'
    job_name, build_number, status  = '%s' %build_name, 532, 'SUCCESS'
    started, duration = build_start, 231
    commits = []
    build = bsh.MockJenkinsBuild(job_name, build_number, status, started, duration, commits)
    build.url = "http://jenkey.dfsa.com:8080/job/bashfulmonkies/532"
    build_job_uri = "/".join(build.url.split('/')[:-2])

    build_defn = agicen.ensureBuildDefinitionExists(job_name, 'Jenkins', build_job_uri)
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
    filename = "config/buildorama.yml"
    logger, konf = sh.setup_config(filename)
    konf.topLevel('AgileCentral')['Project'] = 'Jenkins'

    # get an AgileCentralConnection
    agicen = bsh.AgileCentralConnection(konf.topLevel('AgileCentral'), logger)
    agicen.other_name = 'Jenkins'
    agicen.connect()
    agicen.validateProjects(['Jenkins'])

    # mock up a Build
    build_start = int((datetime.now() - timedelta(minutes=60)).timestamp())
    build_name = 'Hungry kids devour our tasty product'
    job_name, build_number, status  = '%s' %build_name, 74, 'SUCCESS'
    started, duration = build_start, 43
    # use some SHA values corresponding to some actual Agile Central Changeset items in our target Workspace
    commits = ['CHOCOLATE', 'MORE CHOCOLATE'] # these are actual shas
    random_scm_repo_name = "Velocirat"
    random_scm_type = "abacus"


    #scm_repo = create_scm_repo(agicen, random_scm_repo_name, random_scm_type)
    scm_repo = agicen.ensureSCMRepositoryExists(random_scm_repo_name, random_scm_type)
    for sha in commits:
        changeset_payload = {
            'SCMRepository': scm_repo.ref,
            'Revision': sha,
            'CommitTimestamp': '2016-12-31'
        }
        try:
            changeset = agicen.agicen.create('Changeset', changeset_payload)
        except Exception as msg:
            raise Exception("Could not create Changeset  %s" % msg)

    build = bsh.MockJenkinsBuild(job_name, build_number, status, started, duration, commits)
    build.url = "http://jenkey.dfsa.com:8080/job/hugrycats/%s" % build_number
    build_job_uri = "/".join(build.url.split('/')[:-2])


    # run the same code as above to matchToChangesets
    # assert that some were found
    build_defn = agicen.ensureBuildDefinitionExists(job_name, 'Jenkins', build_job_uri)
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


