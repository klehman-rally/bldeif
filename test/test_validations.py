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
    build_connector = sh.BLDConnector(konf, logger)
    assert build_connector is not None
    assert build_connector.validate() is True
    assert build_connector.agicen_conn.workspace_name ==  ac_workspace

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
    filename = "wallace_gf.yml"
    jenkins_struct = {
        'Jobs': [{'Job': 'Wendolene Ramsbottom', 'AgileCentral_Project': 'Close Shave'},
                 {'Job': 'Lady Tottington', 'AgileCentral_Project': 'The Curse of the Were-Rabbit'},
                 {'Job': 'Piella Bakewell', 'AgileCentral_Project': 'A Matter of Loaf and Death'}]
    }

    logger, konf = sh.setup_config(filename, jenkins_struct)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    ac_conf = konf.topLevel('AgileCentral')
    jenk_conf = konf.topLevel('Jenkins')
    expectedErrPattern = "bad juju in town..."
    with pytest.raises(Exception) as excinfo:
        sh.BLDConnector(konf, logger)
    actualErrVerbiage = excinfo.value.args[0]
    assert re.search(expectedErrPattern, actualErrVerbiage) is not None


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
    print(cranky)
    assert cranky.count(' OR ') == 3
    assert cranky.count('(') == cranky.count(")")
    noneski_projects = []
    cranky = acc._construct_ored_Name_query(noneski_projects)
    print(cranky)
    assert len(cranky) == 0
    assert cranky.count(' OR ') == 0

def test_validate_projects():
    filename = "wallace_gf.yml"
    logger, konf = sh.setup_config(filename)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    ac_conf = konf.topLevel('AgileCentral')
    #acc = sh.AgileCentralConnection(ac_conf, logger)
    #acc.connect()
    expectedErrPattern = "projects mentioned in the config were not located in AgileCentral Workspace"
    with pytest.raises(Exception) as excinfo:
        sh.BLDConnector(konf, logger)
    actualErrVerbiage = excinfo.value.args[0]
    assert re.search(expectedErrPattern, actualErrVerbiage) is not None

    # target_projects = ['Jenkins','Salamandra','Refusnik']
    # assert acc.validateProjects(target_projects) is True
    # target_projects = ['X', '5th Amendment Rights overuse']
    # assert acc.validateProjects(target_projects) is False


