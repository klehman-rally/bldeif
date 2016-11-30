import sys, os
import spec_helper as sh
import yaml

def test_simple_config_loading():
    logger, conf = sh.setup_config('config/buildorama.yml')
    assert conf.topLevel('AgileCentral')['Server'] == sh.DEFAULT_AGILE_CENTRAL_SERVER


def test_config_file():
    logger, conf = sh.setup_config('config/trumpkin.yaml')
    assert conf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = conf.topLevel('Jenkins')
    assert jenk_conf['AgileCentral_DefaultBuildProject'] != None
    assert jenk_conf['AgileCentral_DefaultBuildProject'] == 'Jenkins'
    jenk_jobs = jenk_conf['Jobs']
    assert len(jenk_jobs) == 2
    for job in jenk_jobs:
        assert 'AgileCentral_Project' in job
        assert job['AgileCentral_Project'] in ['Salamandra', 'Refusnik']


def test_vcs_data_flag():
    logger, conf = sh.setup_config('config/trumpkin.yaml')
    assert conf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    service_conf = conf.topLevel('Service')
    service_conf['VCSData'] = True
    assert service_conf.get('VCSData', False)