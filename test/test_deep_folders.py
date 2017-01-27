import os
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
import re
from bldeif.bld_connector_runner import BuildConnectorRunner
from bldeif.bld_connector    import BLDConnector

SOME_CONFIG    = 'kangaroo.yml'
OTHER_CONFIG   = 'nebuchadnezzar.yml'
SHALLOW_CONFIG = 'shallow.yml'
DSF_CONFIG     = 'deepstatefolders.yml'
DSFN_CONFIG    = 'dsfn.yml'
DOS_WOMBATS_CONFIG = 'two_wombats.yml'
BANG_CONFIG    = 'bangladesh.yml'
POLPOT_CONFIG  = 'polpot.yml'
LONG_JOHN_CONFIG = 'long-john-silver.yml'

def connect_to_jenkins(config_file):
    #config_file = 'config/honey-badger.yml'
    config_file = "config/{}".format(config_file)
    jenk_conf = {}
    with open(config_file, 'r') as cf:
        content = cf.read()
        all_conf = yaml.load(content)
        jenk_conf = all_conf['JenkinsBuildConnector']['Jenkins']

    jc = bsh.JenkinsConnection(jenk_conf, ActivityLogger('log/inventory.log'))
    return jc

def get_bld_connector(config_file):
    try:
        config_path = 'config/%s' % config_file
        config_name = config_path.replace('config/', '')
        args = [config_name]
        runner = BuildConnectorRunner(args)
        config = runner.getConfiguration(config_path)
        connector = BLDConnector(config, runner.log)
        return connector
    except Exception as msg:
        print ('Oh noes! %s' % msg)
        raise


def test_folder_full_path_specified():
    connector = get_bld_connector(SOME_CONFIG)
    jenk_conf = connector.config.topLevel('Jenkins')
    assert jenk_conf.get('FullFolderPath', None)

def test_abacab_bontamy_folder():
    connector = get_bld_connector(DSF_CONFIG)
    jenk_conf = connector.config.topLevel('Jenkins')
    assert jenk_conf.get('FullFolderPath', None)

def test_folder_no_full_path_specified():
    connector = get_bld_connector(OTHER_CONFIG)
    bld_conn = connector.bld_conn
    assert bld_conn.full_folder_path == False

def test_check_max_depth():
    log_file = 'log/%s.log' % SHALLOW_CONFIG.replace('.yml', '')
    os.path.exists(log_file) and os.remove(log_file)
    open(log_file, 'a').close()
    of = sh.OutputFile(log_file)

    expectedErrPattern = "Validation failed"
    with pytest.raises(Exception) as excinfo:
        get_bld_connector(SHALLOW_CONFIG)
    actualErrVerbiage = excinfo.value.args[0]
    assert expectedErrPattern in actualErrVerbiage

    log_output = of.readlines()
    error_lines = [line for line in log_output if 'ERROR' in line][1]
    error = "Check if MaxDepth value .* in config is sufficient to reach these folders"
    mo = re.search(error, error_lines)
    assert mo is not None

def test_top_level_folder_unqualified_is_ok():
    """
        FullFolderPath is True and Jenkins section has a valid first level folder name which is not fully qualified

        This should be OK if the folder name actually exists
    """
    connector = get_bld_connector(SOME_CONFIG)
    jenk_conf = connector.config.topLevel('Jenkins')
    assert jenk_conf.get('FullFolderPath') == True
    target_folder = 'immovable wombats'
    folders = connector.bld_conn.inventory.folders
    assert folders['/%s' % target_folder]


def test_get_inventory():
    jc = connect_to_jenkins(DSF_CONFIG)
    assert jc.connect()
    jc.showFolderJobs()


def test_getFullyQualifiedFolderKeys():
    folders_keys = ['/Doofus', '/Junkpile/westhalf/lights']
    folders_from_config = ['Doofus' , 'Junkpile // westhalf // lights']

    fookey = {" // ".join(re.split(r'\/', key)[1:]) : key for key in folders_keys}
    assert 'Doofus' in fookey.keys()
    assert 'Junkpile // westhalf // lights' in fookey.keys()
    assert fookey['Junkpile // westhalf // lights'] == '/Junkpile/westhalf/lights'

def test_folder_name_referenced_multiple_times_with_no_full_folder_path_config():
    log_file = 'log/%s.log' % DOS_WOMBATS_CONFIG.replace('.yml', '')
    os.path.exists(log_file) and os.remove(log_file)
    open(log_file, 'a').close()
    of = sh.OutputFile(log_file)
    expectedErrPattern = 'Validation failed'
    with pytest.raises(Exception) as excinfo:
        get_bld_connector(DOS_WOMBATS_CONFIG)
    actualErrVerbiage = excinfo.value.args[0]
    assert expectedErrPattern in actualErrVerbiage

    log_output = of.readlines()
    error_lines = [line for line in log_output if 'ERROR' in line]
    dupe_folder_line = [line for line in error_lines if 'Duplicated folder names: immovable wombats' in line][0]
    full_path_line = [line for line in error_lines if 'You should use the FullFolderPath' in line][0]
    assert dupe_folder_line
    assert full_path_line

def test_config_uses_full_folder_path_with_second_level_folder_specified():
    connector = get_bld_connector(DSF_CONFIG)
    jenk_conf = connector.config.topLevel('Jenkins')
    assert jenk_conf.get('FullFolderPath', None)
    jenk = connector.bld_conn
    assert jenk.vetted_folder_jobs
    bontamies = [k for k in jenk.vetted_folder_jobs.keys() if 'bontamy' in k]
    assert bontamies
    assert len(bontamies) == 2

def test_improperly_specified_folder_name_in_full_folder_path_env():
    log_file = 'log/%s.log' % BANG_CONFIG.replace('.yml', '')
    os.path.exists(log_file) and os.remove(log_file)
    open(log_file, 'a').close()
    of = sh.OutputFile(log_file)
    expectedErrPattern = 'Validation failed'
    with pytest.raises(Exception) as excinfo:
        get_bld_connector(BANG_CONFIG)
    actualErrVerbiage = excinfo.value.args[0]
    assert expectedErrPattern in actualErrVerbiage

    log_output = of.readlines()
    error_lines = [line for line in log_output if 'ERROR' in line][2]
    error = "Check if your Folder entries use the fully qualified path syntax"
    mo = re.search(error, error_lines)
    assert mo is not None

def test_invalid_folder_path():
    log_file = 'log/%s.log' % POLPOT_CONFIG.replace('.yml', '')
    os.path.exists(log_file) and os.remove(log_file)
    open(log_file, 'a').close()
    of = sh.OutputFile(log_file)
    expectedErrPattern = 'Validation failed'
    with pytest.raises(Exception) as excinfo:
        get_bld_connector(POLPOT_CONFIG)
    actualErrVerbiage = excinfo.value.args[0]
    assert expectedErrPattern in actualErrVerbiage

    log_output = of.readlines()
    error_lines = [line for line in log_output if 'ERROR' in line][0]
    error = "were not present in the Jenkins inventory of Folders"
    mo = re.search(error, error_lines)
    assert mo is not None

def test_too_long_folder_path_for_small_maxDepth():
    log_file = 'log/%s.log' % LONG_JOHN_CONFIG.replace('.yml', '')
    os.path.exists(log_file) and os.remove(log_file)
    open(log_file, 'a').close()
    of = sh.OutputFile(log_file)
    expectedErrPattern = 'Validation failed'
    with pytest.raises(Exception) as excinfo:
        get_bld_connector(LONG_JOHN_CONFIG)
    actualErrVerbiage = excinfo.value.args[0]
    assert expectedErrPattern in actualErrVerbiage

    log_output = of.readlines()
    error_lines = [line for line in log_output if 'ERROR' in line][1]
    error = "Check if MaxDepth value .* in config is sufficient to reach these folders"
    mo = re.search(error, error_lines)
    assert mo is not None
