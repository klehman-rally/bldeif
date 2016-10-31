import pytest
import spec_helper as sh
import re


# def test_bad_ac_projects():
#     filename = "wallace_gf.yml"
#     jenkin_struct = {
#         'Jobs': [{'Job': 'Wendolene Ramsbottom', 'AgileCentral_Project': 'Close Shave'},
#                  {'Job': 'Lady Tottington', 'AgileCentral_Project': 'The Curse of the Were-Rabbit'},
#                  {'Job': 'Piella Bakewell', 'AgileCentral_Project': 'A Matter of Loaf and Death'}]
#     }
#
#     logger, konf = sh.setup_config(filename, jenkin_struct)
#     assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
#     jenk_conf = konf.topLevel('Jenkins')
#     build_connector = sh.BLDConnector(konf, logger)


def test_default_config_spoke_validation():
    filename = "wallace_gf.yml"
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
    filename = "wallace_gf.yml"

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
    filename = "wallace_gf.yml"
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
    filename = "wallace_gf.yml"
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
    filename = "wallace_gf.yml"
    logger, konf = sh.setup_config(filename)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    expectedErrPattern = "projects mentioned in the config were not located in AgileCentral Workspace"
    with pytest.raises(Exception) as excinfo:
        sh.BLDConnector(konf, logger)
    assert excinfo.typename == 'ConfigurationError'
    log_output = of.readlines()
    error_line = [line for line in log_output if 'ERROR' in line][0]
    assert re.search(expectedErrPattern, error_line) is not None



