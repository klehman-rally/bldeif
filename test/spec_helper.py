import sys, os

import time
from datetime import datetime, timedelta

import re
import yaml

from pprint import pprint

from bldeif.utils.konfabulus import Konfabulator
from bldeif.utils.test_konfabulus import TestKonfabulator

from bldeif.utils.klog       import ActivityLogger
from bldeif.bld_connector    import BLDConnector
from bldeif.agicen_bld_connection import AgileCentralConnection

import jenkins_spec_helper as jsh
import build_spec_helper   as bsh

DEFAULT_AGILE_CENTRAL_SERVER = 'rally1.rallydev.com'
DEFAULT_AC_API_KEY   = '_2QFAQA0wQoSKiORUOsVlMjeQfFr1JkawtItGFHtrtx8'
DEFAULT_AC_WORKSPACE = 'Alligators BLD Unigrations'
DEFAULT_AC_PROJECT   = 'Jenkins'
DEFAULT_JENKINS_PROTOCOL = 'http'
DEFAULT_JENKINS_SERVER = 'tiema03-u183073.ca.com'
DEFAULT_JENKINS_PORT = 8080
#DEFAULT_JENKINS_CREDENTIALS = 'jenkins/rallydev'
DEFAULT_JENKINS_USERNAME = 'jenkins'
DEFAULT_JENKINS_PASSWORD = 'rallydev'
DEFAULT_JENKINS_API_TOKEN = 'e008e30c73820b7eeb097ae1f1fa1dd8'
DEFAULT_JENKINS_MAX_DEPTH = 5
DEFAULT_JENKINS_STRUCTURE = """
        Views:
            - View: Prairie
              include: ^blue*
              exclude: ^stem,fumar,launch
              AgileCentral_Project: Salamandra

            - View: Shoreline
              include: Bra*wogs
              exclude: ^feature-*,burnin
              AgileCentral_Project: Brazen Milliwogs

        Jobs:
            - Job: troglodyte
              AgileCentral_Project: Salamandra

            - Job: truculent elk medallions
              AgileCentral_Project: Refusnik

        Folders:
            - Folder : Parkour
              AgileCentral_Project: Salamandra
              exclude: angela merkel,
"""

DEFAULT_SERVICES = """
        Preview       : True
        LogLevel      : DEBUG
        MaxBuilds     : 50
        ShowVCSData   : True
"""

SIMPLE_CONFIG_TEMPLATE = """
---
JenkinsBuildConnector:

    AgileCentral:
        <!AC_CREDS_INFO!>

    Jenkins:
        <!JENKINS_CREDS_INFO!>
        <!JENKINS_MAX_DEPTH!>
        <!AC_DEFAULT_BUILD_PROJECT!>

        <!JENKINS_STRUCTURE_SPECS!>

    Service:
        <!BLDEIF_SERVICE!>
...

"""

class AC_Creds_Inflator:

    indent = " " * 8

    def __init__(self, server, api_key, username, password, workspace):
        self.server    = server
        self.api_key   = api_key
        self.username  = username
        self.password  = password
        self.workspace = workspace

    def server_conf(self): return    'Server    :  %s' % self.server    if self.server    else ''
    def api_key_conf(self): return   'APIKey    :  %s' % self.api_key   if self.api_key   else ''
    def username_conf(self): return  'Username  :  %s' % self.username  if self.username  else ''
    def password_conf(self): return  'Password  :  %s' % self.password  if self.password  else ''
    def workspace_conf(self): return 'Workspace :  %s' % self.workspace if self.workspace else ''

    def __str__(self):
        all_items = [self.server_conf(), self.api_key_conf(),
                     self.username_conf(), self.password_conf(),
                     self.workspace_conf()]
        populated = [item for item in all_items if item]
        return  ("\n%s" % self.indent).join(populated)

class Jenkins_Params_Inflator:
    indent = " " * 8
    def __init__(self, protocol, server, port, username, password, api_token, default_project, max_depth):
        self.protocol  = protocol
        self.server    = server
        self.port      = port
        self.username  = username
        self.password  = password
        self.api_token   = api_token
        self.default_project = default_project
        self.default_max_depth = max_depth

    def protocol_conf(self):return   'Protocol  :  %s' % self.protocol  if self.server      else 'http'
    def port_conf(self): return      'Port      :  %s' % self.port      if self.port        else '8080'
    def server_conf(self): return    'Server    :  %s' % self.server    if self.server      else ''
    def api_token_conf(self): return 'API_Token :  %s' % self.api_token if self.api_token   else ''
    def username_conf(self): return  'Username  :  %s' % self.username  if self.username    else ''
    def password_conf(self): return  'Password  :  %s' % self.password  if self.password    else ''
    def default_project_conf(self): return 'AgileCentral_DefaultBuildProject :  %s' % self.default_project if self.default_project   else ''
    def default_max_depth_conf(self): return 'MaxDepth  :  %s' % self.default_max_depth if self.default_max_depth else 3


    def creds(self):
        #print (self.server_conf())
        all_items = [self.protocol_conf(), self.server_conf(), self.port_conf(), self.api_token_conf(),self.username_conf(), self.password_conf()]
        populated = [item for item in all_items if item]
        return ("\n%s" % self.indent).join(populated)

    def default_project(self):
        return "%s%s" % (self.indent, self.default_project_conf())

    def inflate_structure(self, structure):
        #futz with structure which should be a dict with keys potentially of Jobs, Views, Folders
        if type(structure) == str and structure == 'DEFAULT_JENKINS_STRUCTURE':
            return DEFAULT_JENKINS_STRUCTURE[9:]
        if type(structure) == str:
            structure = yaml.load(structure)

        box = []
        optional_keys = ['include', 'exclude', 'AgileCentral_Project']
        for container, items in structure.items():
            box.append('%s:' % container)
            for item in items:
                item_keys = item.keys()
                container_item = container[:-1]
                if container_item not in item:
                    raise Exception("Missing '%s' in %s" % (container_item, item))
                box.append("    - %s: %s" % (container_item, item[container_item]))
                for k in optional_keys:
                    if k in item:
                        box.append("      %s: %s" % (k, item[k]))
                box.append("")

        first_line = box[0][:]
        box = [first_line] + ["        %s" % line for line in box[1:]]
        blob = "\n".join(box)
        return blob

    def inflate_services(self, services):
        # futz with services which should be a dict with keys potentially of Preview, LogLevel, MaxBuilds, VCSData
        if type(services) == str and services == 'DEFAULT_SERVICES':
            return DEFAULT_SERVICES[9:]
        if type(services) == str:
            services = yaml.load(services)

        legal_settings = ['Preview', 'LogLevel', 'MaxBuilds', 'ShowVCSData']
        bogus_settings = [setting for setting in services if setting not in legal_settings]
        if bogus_settings:
            raise Exception("Supplied services %s contain bogus items: %s" % (services, bogus_settings))

        box = ["    %s: %s" % (service, services[service]) for service in legal_settings if service in services]
        first_line = box[0][:]
        box = [first_line] + ["        %s" % line for line in box[1:]]
        #box = [first_line] + ["    %s" % line for line in box[1:]]
        blob = "\n".join(box)
        return blob

def inflate_config_file(filename, jenkins_structure='DEFAULT_JENKINS_STRUCTURE', services='DEFAULT_SERVICES'):
    aci = AC_Creds_Inflator(DEFAULT_AGILE_CENTRAL_SERVER, DEFAULT_AC_API_KEY, None, None,
                            DEFAULT_AC_WORKSPACE)

    jpi = Jenkins_Params_Inflator(DEFAULT_JENKINS_PROTOCOL, DEFAULT_JENKINS_SERVER, DEFAULT_JENKINS_PORT,
                                  DEFAULT_JENKINS_USERNAME, DEFAULT_JENKINS_PASSWORD,
                                  DEFAULT_JENKINS_API_TOKEN, DEFAULT_AC_PROJECT, DEFAULT_JENKINS_MAX_DEPTH)


    config_raw = SIMPLE_CONFIG_TEMPLATE.replace('<!AC_CREDS_INFO!>', str(aci))
    config_raw = config_raw.replace('<!JENKINS_CREDS_INFO!>',       jpi.creds())
    config_raw = config_raw.replace('<!AC_DEFAULT_BUILD_PROJECT!>', jpi.default_project_conf())
    config_raw = config_raw.replace('<!JENKINS_STRUCTURE_SPECS!>',  jpi.inflate_structure(jenkins_structure))
    config_raw = config_raw.replace('<!BLDEIF_SERVICE!>',           jpi.inflate_services(services))
    config_raw = config_raw.replace('<!JENKINS_MAX_DEPTH!>',        jpi.default_max_depth_conf())

    with open(filename, 'w') as out:
        out.write(config_raw)
    return filename


def setup_config(filename, jenkins_structure='DEFAULT_JENKINS_STRUCTURE', services='DEFAULT_SERVICES'):
    filename = inflate_config_file(filename, jenkins_structure, services)
    logger = ActivityLogger('test.log')
    konf   = Konfabulator(filename, logger)
    return logger, konf

def setup_test_config(filename, jenkins_structure='DEFAULT_JENKINS_STRUCTURE', services='DEFAULT_SERVICES'):
    filename = inflate_config_file(filename, jenkins_structure, services)
    logger = ActivityLogger('test.log')
    tkonf   = TestKonfabulator(filename, logger)
    return logger, tkonf

class OutputFile:
    def __init__(self, file_name):
      self.file_name = file_name
      self.marker = os.stat(file_name).st_size

    def readlines(self):
        content = []
        with open(self.file_name, 'r') as lf:
            lf.seek(self.marker)
            content = lf.readlines()
        return content


def build_immovable_wombats(folder, jobs):

    config = "config/buildorama.yml"
    logger, tkonf = setup_test_config(config)
    assert tkonf.topLevels() == ['AgileCentral', 'Jenkins', 'Service']
    agicen_konf = tkonf.topLevel('AgileCentral')
    jenk_conf = tkonf.topLevel('Jenkins')
    jenkins_url = jsh.construct_jenkins_url(jenk_conf)
    tkonf.add_to_container({'Folder': folder, 'AgileCentral_Project': 'Static', 'exclude': jobs[1]})
    tkonf.remove_from_container({'Folder': 'Parkour'})
    tkonf.remove_from_container({'View': 'Prairie'})
    tkonf.remove_from_container({'View': 'Shoreline'})
    tkonf.remove_from_container({'Job': 'troglodyte'})
    tkonf.remove_from_container({'Job': 'truculent elk medallions'})
    assert folder in [folder_rec['Folder'] for folder_rec in jenk_conf['Folders']]

    for job in jobs:
        r = jsh.build(jenk_conf, jenkins_url, job, folder=folder)

    jc = bsh.JenkinsConnection(jenk_conf, logger)
    jc.connect()

    return jc