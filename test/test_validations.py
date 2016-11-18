import pytest
import spec_helper as sh
import build_spec_helper as bsh
from bldeif.utils.eif_exception import ConfigurationError, OperationalError
#from bldeif.agicen_bld_connection import AgileCentralConnection
import re




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
    filename = "config/templ.yml"
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







