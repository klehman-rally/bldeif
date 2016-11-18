
__doc__ = """
This module contains a class and a couple of functions.
The Konfabulator class handles loading up a config file (which must be in YAML format)
and checks for basic structure validity.
The class also allows a caller to specify the loading of specific connection classes 
for use in the BLDConnector.
"""

#################################################################################################

import sys, os
import re
import shutil

import yaml

from bldeif.utils.eif_exception import ConfigurationError, NonFatalConfigurationError
from bldeif.utils.claslo import ClassLoader
from bldeif.utils.fuzzer import Fuzzer

#################################################################################################

class Konfabulator(object):
    """
        An instance of this class provides a means to read a configuration file
        in YAML format and separate the various sections out for easy consumption by
        holders of a Konfabulator instance.
        An instance also offers the capability to "fuzz" clear-text passwords in a
        config file into an encoded (but not encrypted) form and to be able to handle
        defuzzing those encoded passwords for holders of the instance when they access
        those values via a dict like access.
    """

    def __init__(self, config_file_name, logger):
        self.config_file_name = config_file_name
        self.log = logger
        self.top_level_sequence = []

        # check for existence, file-ness, readability of config_file_name
        if not os.path.exists(config_file_name):
            raise ConfigurationError('config file: %s not found' % config_file_name)
        if not os.path.isfile(config_file_name):
            raise ConfigurationError('config file: %s is not a file' % config_file_name)
        if not os.access(config_file_name, os.F_OK | os.R_OK):
            raise ConfigurationError('config file: %s not a readable file' % config_file_name)

        content = []
        try:
            cf = open(config_file_name, 'r')
        except IOError as msg:
            raise ConfigurationError('Unable to open %s for reading, %s' % (config_file_name, msg))
        content = cf.read()
        self.content = content
        cf.close()

        try:
            complete_config = yaml.load(content)
            top_key = list(complete_config.keys())[0]
            self.config = complete_config[top_key]
        except Exception as msg:
            raise ConfigurationError('Unable to parse %s successfully, %s' % (config_file_name, msg))

        conf_lines = [line for line in content.split('\n') if line and not re.search(r'^\s*#', line)]
        connector_header = [line for line in conf_lines if re.search(r'^[A-Z][A-Za-z_]+.+\s*:', line)]
        section_headers  = [line for line in conf_lines if re.search(r'^    [A-Z][A-Za-z_]+.+\s*:', line)]
##
        #print(repr(self.config))
##
        if len(section_headers) < 2:
            raise ConfigurationError('Insufficient content in config file: %s' % config_file_name)
        if len(section_headers) > 3:
            raise NonFatalConfigurationError('Excess content in config file: %s' % config_file_name)

        self.agicen_header = section_headers.pop(0).strip().replace(':', '')
        if not self.agicen_header.startswith('AgileCentral'):
            raise ConfigurationError('First section in config file must be AgileCentral section')
        self.top_level_sequence.append('AgileCentral')

        self.bld_header = section_headers.pop(0).strip().replace(':', '')
        if self.bld_header not in ['Jenkins']:
            raise ConfigurationError('Second section in config file must identify a known BLD identifier')
        self.top_level_sequence.append(self.bld_header)

        # set up defaults for the Service section if that section isn't in the config file
        if 'Service' not in self.config:
            self.config['Service'] = {}
            self.config['Service']['LogLevel'] = 'Info'
            self.config['Service']['Preview']  = False
            self.config['Service']['StrictProject']  = False
            self.config['Service']['PostBatchExtension']  = None

        while section_headers:
            header = section_headers.pop(0).replace(':', '').strip()
            try:
                if header not in ['Service']:
                    problem = 'config section header "%s" not recognized, ignored...' % header
                    raise ConfigurationError(problem)
                else:
                    self.top_level_sequence.append(header)
            except ConfigurationError as msg:
                pass

        # defuzz the passwords if they are fuzzed, and if they are not, fuzz them in the file
        self.defuzzPasswords()


    def topLevels(self):
        return self.top_level_sequence

    def topLevel(self, section_name):
        if section_name == 'BLD':
            section_name = [name for name in self.top_level_sequence 
                                  if name not in ['AgileCentral', 'Service']][0]
            
        if section_name in self.top_level_sequence and section_name in self.config:
            return self.config[section_name]
        else:
            problem = 'Attempt to retrieve non-existent top level config section for %s'
            raise ConfigurationError(problem  % section_name)


    def connectionClassName(self, section_name):
        if section_name not in self.config:
            raise ConfigurationError('Attempt to identify connection class name for %s, operation not supported'% section_name)
        if section_name not in ['AgileCentral', self.bld_header]:
            raise ConfigurationError('Candidate connection class name "%s" not viable for operation'% section_name)
        section = self.config[section_name]
        if 'Class' in section:
            class_name = section['Class']
        else:
            class_name = 'AgileCentralConnection' 
            if section_name != 'AgileCentral':
                class_name = '%sConnection' % self.bld_header

        return class_name

       
    def defuzzPasswords(self):
        acpw = self.config['AgileCentral'].get('Password', None)
        if Fuzzer.isEncoded(acpw):
            self.config['AgileCentral']['Password'] = Fuzzer.defuzz(acpw)
        else:
            self.fuzzPassword('AgileCentral', acpw)
      
        # in many cases, there isn't a requirement that the BLD section have a Password entry
        bpw = self.config[self.bld_header].get('Password', None)
        if bpw:
            if Fuzzer.isEncoded(bpw):
                self.config[self.bld_header]['Password'] = Fuzzer.defuzz(bpw)
            else:
                self.fuzzPassword(self.bld_header, bpw)


    def fuzzPassword(self, conn_section, clear_text_password):
        """
            check to see whether or not the Password entries in one or both of the connection
            sections are not encoded.  If not, encode them and write out the config file
            changing *only* those two entries:
        """
        if Fuzzer.isEncoded(clear_text_password):
            return False

        encoded_password = Fuzzer.encode(clear_text_password)
            
        conf_lines = []
        try:
            cf = open(self.config_file_name, 'r')
        except IOError as msg:
            raise ConfigurationError('Unable to open %s for reading, %s' % (self.config_file_name, msg))
        conf_lines = cf.readlines()
        cf.close()

        out_lines = []
        ix = 0

        # objective:   Find index of conn_section entry in conf_lines
        #              then find index of next occurring Password : xxxx entry
        #              substitute entry for Password : current with Password : encoded_password
##
##        print "fuzzPassword, conn_section: %s" % conn_section
##        print "conf_lines:\n%s" % "\n".join(conf_lines)
##        print "-----------------------------------------------------"
##
        hits = [ix for ix, line in enumerate(conf_lines) if re.search('^\s+%s\s*:' % conn_section, line)]
        section_ix = hits[0]
        hits = [ix for ix, line in enumerate(conf_lines) if re.search('^\s+Password\s*:\s*', line) and ix > section_ix]
        if hits:
            pwent_ix = hits[0]
            conf_lines[pwent_ix] = '        Password  :  %s\n' % encoded_password

        enc_file_name = '%s.pwenc' % self.config_file_name
        enf = open(enc_file_name, 'w')
        enf.write(''.join(conf_lines))
        enf.close()
       
        bkup_name = "%s.bak" % self.config_file_name
        try:
            shutil.copy2(self.config_file_name, bkup_name)
        except Exception as msg:
            self.log.warn("Unable to write a temporary backup file '%s' with config info: %s" % (bkup_name, msg))
            return False

        try:
            os.remove(self.config_file_name)
        except Exception as msg:
            self.log.warn("Unable to remove config file prior to replacement with password encoded version of the file: %s" % msg)
            return False

        try:
            os.rename(enc_file_name, self.config_file_name)
        except Exception as msg:
            self.log.error("Unable to rename config file with password encoded to standard config filename of %s: %s" % (self.config_file_name, msg))
            return False

        try:
            os.remove(bkup_name)
        except Exception as msg:
            self.log.warn("Unable to remove temporary backup file for config: %s" % msg)
            return False

        return True
        

    def __priorArt(self):
        conf = self.config
        conf_top_level_keys = conf.keys()
        conns = [key for key in conf.keys() if key not in ['Service']]
        if len(conns) != 2:
            self.log.fatal('Configuration does not specify exactly 2 Connections')
            return None, None

        with open(self.config_file, 'r') as cf:
            lines = cf.readlines()
            conn_lines = []
            for line in lines:
                if line.startswith(' ') or line.startswith('#'):
                    continue
                if line.strip().split(':')[0] in ['Service']:
                    continue
                if ':' not in line.strip():
                    continue
                conn_lines.append(line.strip().split(':')[0])
                
        if len(conn_lines) != 2:
            problem = 'Configuration file does not conform to spec, %d Connection sections found'
            self.log.fatal(problem % len(conn_lines))

        agicen_conn_name = conn_lines[0]
        bld_conn_name    = conn_lines[1]

        if not agicen_conn_name.startswith('AgileCentral'):
            problem = 'Unexpected name for initial connection in config, expected AgileCentral'
            raise ConfigurationError(problem)

