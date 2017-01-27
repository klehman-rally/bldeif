import pytest
import yaml
import datetime
from collections import OrderedDict
import spec_helper as sh
import build_spec_helper as bsh
from bldeif.utils.eif_exception import ConfigurationError, OperationalError, logAllExceptions
from bldeif.utils.klog       import ActivityLogger
from bldeif.utils.konfabulus import Konfabulator
from bldeif.agicen_bld_connection import AgileCentralConnection
import build_spec_helper   as bsh
from bldeif.bld_connector_runner import BuildConnectorRunner
import re

PLATYPUS_JENKINS_STRUCTURE="""
        Jobs:
            - Job: centaur-mordant
              AgileCentral_Project: Jenkins // Salamandra

        Folders:
            - Folder : frozique
              AgileCentral_Project: Jenkins // Corral // Salamandra
"""
PLATYPUS_SERVICES="""
    Preview       : False
    LogLevel      : DEBUG
    MaxBuilds     : 50
    ShowVCSData   : True
"""

def test_default_config_spoke_validation():
    filename = "config/wallace_gf.yml"
    logger, konf = sh.setup_config(filename)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    ac_conf = konf.topLevel('AgileCentral')
    ac_workspace = ac_conf['Workspace']
    jenk_conf = konf.topLevel('Jenkins')
    expectedErrPattern = "Validation failed"
    with pytest.raises(Exception) as excinfo:
        build_connector = sh.BLDConnector(konf, logger)
    actualErrVerbiage = excinfo.value.args[0]
    assert re.search(expectedErrPattern, actualErrVerbiage) is not None
    assert excinfo.typename == 'ConfigurationError'


def test_bad_workspace_with_default_config():
    filename = "config/wallace_gf.yml"

    logger, konf = sh.setup_config(filename)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    ac_conf = konf.topLevel('AgileCentral')
    ac_workspace = ac_conf['Workspace']
    wrong_ac_workspace = "Dunderhead"
    ac_conf['Workspace'] = wrong_ac_workspace
    jenk_conf = konf.topLevel('Jenkins')

    expectedErrPattern = "Specified workspace of '.*' either does not exist or the user does not have permission to access that workspace"
    with pytest.raises(Exception) as excinfo:
        sh.BLDConnector(konf, logger)
    actualErrVerbiage = excinfo.value.args[0]
    assert re.search(expectedErrPattern, actualErrVerbiage) is not None

def test_jenkins_struct_with_bad_projects():
    of = sh.OutputFile('test.log')
    filename = "config/wallace_gf.yml"
    jenkins_struct = {
        'Jobs': [{'Job': 'Wendolene Ramsbottom', 'AgileCentral_Project': 'Close Shave'},
                 {'Job': 'Lady Tottington', 'AgileCentral_Project': 'The Curse of the Were-Rabbit'},
                 {'Job': 'Piella Bakewell', 'AgileCentral_Project': 'A Matter of Loaf and Death'}]
    }

    logger, konf = sh.setup_config(filename, jenkins_struct)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    expectedErrPattern = "These projects mentioned in the config were not located in AgileCentral Workspace %s" % konf.topLevel('AgileCentral')['Workspace']
    with pytest.raises(Exception) as excinfo:
        sh.BLDConnector(konf, logger)
    assert excinfo.typename == 'ConfigurationError'
    log_output = of.readlines()
    error_line = [line for line in log_output if 'ERROR' in line][0]
    assert re.search(expectedErrPattern, error_line) is not None


def test_project_validation_queries():
    """
    we expect someting like this:
        ((((Name = "AC Engineering") OR (Name = "Alligator Tiers")) OR (Name = "O.U.T.S")) OR (Name = "2016 Q4"))
        returns 5 because there are two projects with Name = "2016 Q4"
    """
    filename = "config/wallace_gf.yml"
    logger, konf = sh.setup_config(filename)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    ac_conf = konf.topLevel('AgileCentral')
    acc = sh.AgileCentralConnection(ac_conf, logger)

    figmentary_projects = ['Ambition', 'Epsilorg', 'Philo', 'Zebra']
    cranky = acc._construct_ored_Name_query(figmentary_projects)
    assert cranky.count(' OR ') == 3
    assert cranky.count('(') == cranky.count(")")
    noneski_projects = []
    cranky = acc._construct_ored_Name_query(noneski_projects)
    assert len(cranky) == 0
    assert cranky.count(' OR ') == 0

def test_validate_projects():
    of = sh.OutputFile('test.log')
    filename = "config/wallace_gf.yml"
    logger, konf = sh.setup_config(filename)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    expectedErrPattern = "projects mentioned in the config were not located in AgileCentral Workspace"
    with pytest.raises(Exception) as excinfo:
        sh.BLDConnector(konf, logger)
    assert excinfo.typename == 'ConfigurationError'
    log_output = of.readlines()
    error_line = [line for line in log_output if 'ERROR' in line][0]
    assert re.search(expectedErrPattern, error_line) is not None


def test_detect_same_name_projects():
    of = sh.OutputFile('test.log')
    filename = ('config/temp.yml')
    logger, tkonf = sh.setup_test_config(filename)
    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    tkonf.remove_from_container({'View': 'Shoreline'})
    tkonf.remove_from_container({'Job': 'truculent elk medallions'})
    assert not tkonf.has_item('View', 'Shoreline')
    assert not tkonf.has_item('Job', 'truculent elk medallions')
    ac_conf = tkonf.topLevel('AgileCentral')
    jenk_conf = tkonf.topLevel('Jenkins')
    bc = bsh.BLDConnector(tkonf, logger)
    agicen = bc.agicen_conn.agicen
    workspace_name = ac_conf['Workspace']
    project_name  = jenk_conf['AgileCentral_DefaultBuildProject']
    response = agicen.get('Project', fetch='Name', workspace=workspace_name, projectScopeDown=True, pagesize=200)
    if response.errors or response.resultCount == 0:
        raise ConfigurationError(
            'Unable to locate a Project with the name: %s in the target Workspace' % project_name)

    assert bc.agicen_conn.duplicated_project_names[0] == 'Salamandra'

def test_project_path_separators():
    filename = "config/temp.yml"
    logger, tkonf = sh.setup_test_config(filename)
    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = tkonf.topLevel('Jenkins')
    item = {'View': 'Prairie'}
    new_item = {'View': 'Prairie',
                'include': '^blue*',
                'exclude':'^stem,fumar,launch',
                'AgileCentral_Project': 'Jenkins // Salamandra'}
    tkonf.replace_in_container(item, new_item)
    projects = []
    if jenk_conf['Jobs']:
        for element in jenk_conf['Jobs']:
            if 'AgileCentral_Project' in element:
                projects.append(element['AgileCentral_Project'])
    if jenk_conf['Views']:
        for element in jenk_conf['Views']:
            if 'AgileCentral_Project' in element:
                projects.append(element['AgileCentral_Project'])

    if jenk_conf['Folders']:
        for element in jenk_conf['Folders']:
            if 'AgileCentral_Project' in element:
                projects.append(element['AgileCentral_Project'])

    print(projects)
    project_path = []

    for project in projects:
        if project.find("//") != -1:
            project_path.append(project)

    assert project_path[0] == 'Jenkins // Salamandra'



def test_namesake_projects():
    # have a config that mentions m-e-p Project for the AgileCentral_Project
    # inhale the config
    # mock up a build for the 'australopithicus' Job which will trigger the necessity of creating an AC BuildDefinition record for it
    filename = "config/platypus.yml"
    logger, konf = sh.setup_config(filename, jenkins_structure=PLATYPUS_JENKINS_STRUCTURE, services=PLATYPUS_SERVICES)
    bc = bsh.BLDConnector(konf, logger)
    agiconn = bc.agicen_conn
    # use agiconn.agicen to clear out any Builds/BuildDefinition that match our intended actions
    jobs_projs = {'centaur-mordant': agiconn.agicen.getProject('Jenkins // Salamandra').oid,
                  'australopithicus': agiconn.agicen.getProject('Jenkins // Corral // Salamandra').oid,
                 }
    for job, project_oid in jobs_projs.items():
        criteria = ['BuildDefinition.Name = "%s"' % job, 'BuildDefinition.Project.ObjectID = %d' % project_oid]
        response = agiconn.agicen.get('Build', fetch="ObjectID,Name", query=criteria)
        for build in response:
            agiconn.agicen.delete('Build', build)
        criteria = ['Name = "%s"' % job, 'Project.ObjectID = %d' % project_oid]
        response = agiconn.agicen.get('BuildDefinition', fetch="ObjectID,Name", query=criteria)
        for buildef in response:
            agiconn.agicen.delete('BuildDefinition', buildef)

    assert 'Jenkins'                         in agiconn._project_cache.keys()
    assert 'Jenkins // Salamandra'           in agiconn._project_cache.keys()
    assert 'Jenkins // Corral // Salamandra' in agiconn._project_cache.keys()

    target_project = "Jenkins // Corral // Salamandra"
    tp = agiconn.agicen.getProject(target_project)
    assert target_project in bc.target_projects

    # create some mock builds for associated with the mep Projects
    # throw those against
    #builds = createMockBuilds(['centaur-mordant', 'australopithicus'])
    job_name = 'australopithicus'
    build_start = int((datetime.datetime.now() - datetime.timedelta(minutes=60)).timestamp())
    build_number, status = 532, 'SUCCESS'
    started, duration = build_start, 231
    commits = []
    build = bsh.MockJenkinsBuild(job_name, build_number, status, started, duration, commits)
    build.changeSets = []
    build.url = "http://jenkey.dfsa.com:8080/job/bashfulmonkies/532"

    build_data = build.as_tuple_data()
    info = OrderedDict(build_data)
    assert 'Project' not in info

    build_job_uri = "/".join(build.url.split('/')[:-2])
    build_defn = agiconn.ensureBuildDefinitionExists(job_name, 'Jenkins // Corral // Salamandra', build_job_uri)
    assert build_defn.Name == job_name
    assert build_defn.Project.ObjectID == tp.oid

    if agiconn.buildExists(build_defn, build.number):
        agiconn.log.debug('Build #{0} for {1} already recorded, skipping...'.format(build.number, job_name))

    # pull out any build.changeSets commit IDs and see if they match up with AgileCentral Changeset items Revision attribute
    # if so, get all such commit IDs and their associated Changeset ObjectID, then
    # add that "collection" as the Build's Changesets collection

    agicen_build, status = bc.postBuildToAgileCentral(build_defn, build, [], job_name)
    assert agicen_build.BuildDefinition.ref == build_defn.ref

    # build_defn = agiconn.agicen.ensureBuildDefinitionExistence(job, 'Jenkins', True, build_job_uri)
    # #assert build_defn is not None

def test_without_project():
    config_file = ('missing-project.yml')
    ymlfile = open("config/{}".format(config_file), 'r')
    y = yaml.load(ymlfile)
    logger = ActivityLogger('log/missing-project.log')
    logger.setLevel('DEBUG')
    logAllExceptions(True, logger)
    konf = Konfabulator('config/missing-project.yml', logger)
    jenk_conf = konf.topLevel('Jenkins')
    ac_conf = konf.topLevel('AgileCentral')
    #expectedErrPattern = 'The Jenkins section of the config is missing AgileCentral_DefaultBuildProject property'
    expectedErrPattern = 'The Jenkins section of the config is missing a value for AgileCentral_DefaultBuildProject property'
    with pytest.raises(Exception) as excinfo:
        bc = bsh.BLDConnector(konf, logger)
    actualErrVerbiage = excinfo.value.args[0]
    assert re.search(expectedErrPattern, actualErrVerbiage) is not None
    assert excinfo.typename == 'ConfigurationError'

def test_ac_for_invalid_items():
    config_file = ('bad_ac_items.yml')
    runner = BuildConnectorRunner([config_file])
    runner.run()

    log = "log/{}.log".format(config_file.replace('.yml', ''))
    with open(log, 'r') as f:
        log_content = f.readlines()

    target_line = "AgileCentral section of the config contained these invalid entries"
    match = [line for line in log_content if target_line in line][0]
    assert re.search(r'%s' % target_line, match)

def test_jenkins_for_invalid_items():
    config_file = ('bad_jenk_items.yml')
    runner = BuildConnectorRunner([config_file])
    runner.run()

    log = "log/{}.log".format(config_file.replace('.yml', ''))
    with open(log, 'r') as f:
        log_content = f.readlines()
    target_line = "Jenkins section of the config contained these invalid entries"
    match = [line for line in log_content if target_line in line][0]
    assert re.search(r'%s' % target_line, match)

def test_service_for_invalid_items():
    config_file = ('bad_service_items.yml')
    runner = BuildConnectorRunner([config_file])
    runner.run()

    log = "log/{}.log".format(config_file.replace('.yml', ''))
    with open(log, 'r') as f:
        log_content = f.readlines()

    target_line = "Service section of the config contained these invalid entries"
    match = [line for line in log_content if target_line in line][0]
    assert re.search(r'%s' % target_line, match)

def test_jenkins_for_empty_jobs():
    config_file = ('bad_jenk_empty_jobs.yml')
    runner = BuildConnectorRunner([config_file])
    runner.run()

    log = "log/{}.log".format(config_file.replace('.yml', ''))
    with open(log, 'r') as f:
        log_content = f.readlines()

    target_line = "Jobs section of the config is empty"
    match = [line for line in log_content if target_line in line][0]
    assert re.search(r'%s' % target_line, match)

def test_jenkins_for_empty_views():
    config_file = ('bad_jenk_empty_views.yml')
    runner = BuildConnectorRunner([config_file])
    runner.run()

    log = "log/{}.log".format(config_file.replace('.yml', ''))
    with open(log, 'r') as f:
        log_content = f.readlines()

    target_line = "Views section of the config is empty"
    match = [line for line in log_content if target_line in line][0]
    assert re.search(r'%s' % target_line, match)

def test_jenkins_for_empty_folders():
    config_file = ('bad_jenk_empty_folders.yml')
    runner = BuildConnectorRunner([config_file])
    runner.run()

    log = "log/{}.log".format(config_file.replace('.yml', ''))
    with open(log, 'r') as f:
        log_content = f.readlines()

    target_line = "Folders section of the config is empty"
    match = [line for line in log_content if target_line in line][0]
    assert re.search(r'%s' % target_line, match)

def test_config_defaults():
    #config_file = ('defaults.yml')
    logger = ActivityLogger('log/defaults.log')
    konf = Konfabulator('config/defaults.yml', logger)
    jenk_conf = konf.topLevel('Jenkins')
    ac_conf = konf.topLevel('AgileCentral')
    srv_config = konf.topLevel('Service')
    assert not ac_conf.get('Server', None)
    assert not jenk_conf.get('Server', None)

    # runner = BuildConnectorRunner([config_file])
    # runner.run()

    agicen = bsh.AgileCentralConnection(konf.topLevel('AgileCentral'), logger)
    agicen.other_name = 'Jenkins'
    agicen.project_name = jenk_conf['AgileCentral_DefaultBuildProject']
    agicen.connect()
    assert agicen.server == 'rally1.rallydev.com'
    assert not agicen.proxy

    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    assert jc.server == 'coyotepair.ca.com'
    assert jc.port   == 8080
    assert jc.protocol == 'http'

def test_bad_yml():
    logger = ActivityLogger('log/bad_yml.log')
    expectedErrPattern = "The file does not contain consistent indentation for the sections and section contents"
    unexpectedErrPattern = "Oh noes!"
    with pytest.raises(Exception) as excinfo:
        konf = Konfabulator('config/bad_yml.yml', logger)
    actualErrVerbiage = excinfo.value.args[0]
    assert re.search(expectedErrPattern, actualErrVerbiage)
    assert not re.search(unexpectedErrPattern, actualErrVerbiage)

def test_tab_yml():
    logger = ActivityLogger('log/bad_tab.log')
    expectedErrPattern = "Your config file contains tab characters which are not allowed in a YML file."
    with pytest.raises(Exception) as excinfo:
        konf = Konfabulator('config/bad_tab.yml', logger)
    actualErrVerbiage = excinfo.value.args[0]
    assert re.search(expectedErrPattern, actualErrVerbiage)

