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

SOME_CONFIG    = 'wombat.yml'
OTHER_CONFIG   = 'nebuchadnezzar.yml'
SHALLOW_CONFIG = 'shallow.yml'
DSF_CONFIG     = 'deepstatefolders.yml'
DSFN_CONFIG    = 'dsfn.yml'

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

# def test_vetting():
#     base_url = 'http://foobar.com'
#     folders_keys = ['http://foobar.com/job/Doofus', 'http://foobar.com/job/Junkpile/job/westhalf/job/lights']
#     folders_from_config = ['Doofus', 'Junkpile // westhalf // lights', 'Junkpile // wrong // lights']
#
#     fqks = [" // ".join(re.split(r'\/job\/', key.replace(base_url, ''))[1:]) for key in folders_keys]

# 5) FullFolderPath False/missing and Jenkins section has Folder name that appears more than once in the config



#
# 2) FullFolderPath True and Jenkins section has valid second level folder expressed as FullFolderPath
#
# 3) FullFolderPath True and Jenkins section has name of existing folder at second level but not expressed as FullFolderPath
#
# 4) FullFolderPath False/missing and Jenkins section has Folder name that appears more than once in the inventory
#

#
# 6) FullFolderPath True and Jenkins section has two different paths ending with same leaf name (valid folder names)
#
# 9) FullFolderPath True and Jenkins section has Folder entry as fully qualified that doesn't exist
#
# 7) FullFolderPath True and Jenkins section has two different folder paths ending with same leaf name but only one path actually exists
#
# 10) FullFolderPath True and Jenkins section has Folder with n path components where n = (jc.maxDepth)

