import pytest
import spec_helper as sh
import re

def test_default():
    filename = "default.yml"
    logger, konf = sh.setup_config(filename)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = konf.topLevel('Jenkins')
    job_name = 'troglodyte'
    assert jenk_conf['Jobs'][0]['Job'] == job_name


def test_structure_non_default():
    filename = "wallace_gf.yml"
    jenkin_struct = {
        'Jobs': [{'Job': 'Wendolene Ramsbottom', 'AgileCentral_Project': 'Close Shave'},
                 {'Job': 'Lady Tottington', 'AgileCentral_Project': 'The Curse of the Were-Rabbit'},
                 {'Job': 'Piella Bakewell', 'AgileCentral_Project': 'A Matter of Loaf and Death'}]

    }
    logger, konf = sh.setup_config(filename, jenkin_struct, 'DEFAULT_SERVICES')
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = konf.topLevel('Jenkins')
    project_name = 'A Matter of Loaf and Death'
    assert jenk_conf['Jobs'][1]['Job'] == 'Lady Tottington'
    assert jenk_conf['Jobs'][2]['AgileCentral_Project'] == project_name

def test_services_non_default():
    filename = "wallace_gf.yml"
    service_struct = {
        'Preview': False,
        'LogLevel': 'INFO',
        'VCSData': False
    }
    logger, konf = sh.setup_config(filename, 'DEFAULT_JENKINS_STRUCTURE', service_struct)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    service_conf = konf.topLevel('Service')
    assert service_conf['Preview'] == False

def test_non_default_services():
    filename = "wallace_gf.yml"
    jenkin_struct = {
        'Jobs': [{'Job': 'Wendolene Ramsbottom', 'AgileCentral_Project': 'Close Shave'},
                 {'Job': 'Lady Tottington', 'AgileCentral_Project': 'The Curse of the Were-Rabbit'},
                 {'Job': 'Piella Bakewell', 'AgileCentral_Project': 'A Matter of Loaf and Death'}]

    }
    service_struct = {
        'Preview': False,
        'LogLevel': 'INFO',
        'VCSData': False
    }
    logger, konf = sh.setup_config(filename, jenkin_struct, service_struct)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = konf.topLevel('Jenkins')
    project_name = 'Close Shave'
    assert jenk_conf['Jobs'][0]['Job'] == 'Wendolene Ramsbottom'
    assert jenk_conf['Jobs'][0]['AgileCentral_Project'] == project_name
    service_conf = konf.topLevel('Service')
    assert service_conf['Preview'] == False
    jenkins_jobs = jenk_conf['Jobs']
    assert len(jenkins_jobs) == 3



def test_bad_structure_config():
    filename = "wallace_gf.yml"
    jenkin_struct = {
        'Jobs': [{'Girlfriend': 'Wendolene Ramsbottom', 'Allergies': 'Cheese'},
                 {'Girlfriend': 'Lady Tottington'},
                 {'Girlfriend': 'Piella Bakewell'}]

    }
    expectedErrPattern = "Missing 'Job'"
    with pytest.raises(Exception) as excinfo:
        logger, konf = sh.setup_config(filename, jenkin_struct)
    actualErrVerbiage = excinfo.value.args[0]
    assert expectedErrPattern in actualErrVerbiage


def test_bad_services_config():
    filename = "wallace_gf.yml"
    service_struct = {
        'Purview': False,
        'LogChains': 'INFO',
        'VenusRising': False
    }
    expectedErrPattern = 'Supplied services .* contain bogus items'
    with pytest.raises(Exception) as excinfo:
        logger, konf = sh.setup_config(filename, 'DEFAULT_JENKINS_STRUCTURE', service_struct)
    actualErrVerbiage = excinfo.value.args[0]
    assert re.match(expectedErrPattern, actualErrVerbiage) is not None


def test_bad_containers():
    filename = "wallace_gf.yml"
    jenkin_struct = {
        'Vistas': [{'Vista': 'Wendolene Ramsbottom', 'Allergies': 'Cheese'},
                   {'View': 'Lady Tottington'},
                   {'Job': 'Piella Bakewell'}]

    }
    expectedErrPattern = "Missing 'Vista'"
    with pytest.raises(Exception) as excinfo:
        logger, konf = sh.setup_config(filename, jenkin_struct)
    actualErrVerbiage = excinfo.value.args[0]
    assert expectedErrPattern in actualErrVerbiage
