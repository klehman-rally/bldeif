import sys, os
import pytest
import time
from datetime import datetime, timedelta

import re

from test_basics import *
from test_config_fodder import *

from pprint import pprint



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



