import sys, os
import spec_helper as sh
import yaml

def test_simple_config_loading():
    aci = sh.AC_Creds_Inflator(sh.DEFAULT_AGILE_CENTRAL_SERVER, sh.DEFAULT_AC_API_KEY, None, None, sh.DEFAULT_AC_WORKSPACE)

    config_raw = sh.SIMPLE_CONFIG_STRUCTURE.replace('<!AC_CREDS_INFO!>', str(aci))
    assert(len(config_raw)) > 1
    conf = yaml.load(config_raw)
    assert(conf['JenkinsBuildConnector']['AgileCentral']['Server'] == sh.DEFAULT_AGILE_CENTRAL_SERVER)


def test_config_file():
    aci = sh.AC_Creds_Inflator(sh.DEFAULT_AGILE_CENTRAL_SERVER, sh.DEFAULT_AC_API_KEY, None, None, sh.DEFAULT_AC_WORKSPACE)
    filename = "trumpkin.yaml"
    config_raw = sh.SIMPLE_CONFIG_STRUCTURE.replace('<!AC_CREDS_INFO!>', str(aci))
    with open(filename, 'w') as out:
        out.write(config_raw)

    logger = sh.ActivityLogger('test.log')
    konf   = sh.Konfabulator(filename, logger)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = konf.topLevel('Jenkins')
    assert jenk_conf['AgileCentral_DefaultBuildProject'] != None
    assert jenk_conf['AgileCentral_DefaultBuildProject'] == 'Sandbox'
    jenk_jobs = jenk_conf['Jobs']
    assert len(jenk_jobs) == 3
    for ix, job in enumerate(jenk_jobs):
        if ix == 0:
            assert 'AgileCentral_Project' not in job
        else:
            assert 'AgileCentral_Project' in job
            assert job['AgileCentral_Project'] in ['Dynamic', 'Static']


def test_vcs_data_flag():
    aci = sh.AC_Creds_Inflator(sh.DEFAULT_AGILE_CENTRAL_SERVER, sh.DEFAULT_AC_API_KEY, None, None,
                               sh.DEFAULT_AC_WORKSPACE)
    filename = "trumpkin.yaml"
    config_raw = sh.SIMPLE_CONFIG_STRUCTURE.replace('<!AC_CREDS_INFO!>', str(aci))
    with open(filename, 'w') as out:
        out.write(config_raw)

    logger = sh.ActivityLogger('test.log')
    konf = sh.Konfabulator(filename, logger)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    service_conf = konf.topLevel('Service')
    service_conf['VCSData'] = True
    assert service_conf.get('VCSData', False) == True