import sys, os
import time
import yaml
import pytest
import spec_helper as sh
import build_spec_helper as bsh
import jenkins_spec_helper as jsh
from datetime import datetime, timedelta
import time


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


def test_mock_build():
    two_days_ago = bsh.epochSeconds("-2d")
    mock = bsh.MockJenkinsBuild("fukebane", 13, "Yuge Disaxter", two_days_ago, 34)

    assert(mock.name)   == "fukebane"
    assert(mock.status) == "Yuge Disaxter"


def test_compare_regular_build_time():
    two_days_ago = bsh.epochSeconds("-2d")
    mock_build = bsh.MockJenkinsBuild("fukebane", 13, "Yuge Disaxter", two_days_ago, 34)
    ref_time = time.strptime("2015-10-23T10:23:45Z", '%Y-%m-%dT%H:%M:%SZ')
    logger = bsh.ActivityLogger('test.log')
    konf = bsh.Konfabulator('trumpkin.yaml', logger)
    jenkins_conf = konf.topLevel('Jenkins')
    jc = bsh.JenkinsConnection(jenkins_conf, logger)
    result = jc.jobBeforeRefTime(mock_build, ref_time)
    assert result == False


def test_simple_config():
    t = datetime.now() - timedelta(minutes=60)
    ref_time = t.utctimetuple()
    job_name = 'troglodyte'

    r1 = jsh.create_job(job_name)
    assert r1.status_code == 200

    r2 = jsh.build(job_name)
    assert r2.status_code == 200

    filename = "trumpkin.yaml"

    logger, konf = setup_config(filename)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = konf.topLevel('Jenkins')

    jenk_conf['Jobs'][0] = {'Job':job_name}
    assert jenk_conf['Jobs'][0]['Job'] == job_name
    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)
    assert (job_name in builds["All::%s" % jenk_conf['AgileCentral_DefaultBuildProject']]) == True

    r3 = jsh.delete_job(job_name)
    assert r3.status_code == 200


def test_folder_config():
    t = datetime.now() - timedelta(minutes=1440)
    ref_time = t.utctimetuple()
    job_folder, job_name = 'ALM', 'alm'

    filename = "../config/almci.yml"

    logger, konf = setup_config(filename, False)
    assert konf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    jenk_conf = konf.topLevel('Jenkins')

    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()
    builds = jc.getRecentBuilds(ref_time)
    print("ok")
    assert (job_name in builds["%s::%s" % (job_folder, jenk_conf['AgileCentral_DefaultBuildProject'])]) == True
