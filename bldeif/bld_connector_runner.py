# 2016 

############################################################################################################
#
#  bld_connector_runner - control machinery that detects builds in a build system and 
#                         reflects those builds in a AC Agile Central subscription.
#
############################################################################################################

import sys, os
import re
import time
import glob
from calendar import timegm

from bldeif.utils.klog       import ActivityLogger
from bldeif.utils.proctbl    import ProcTable
from bldeif.utils.lock_file  import LockFile
from bldeif.utils.time_file  import TimeFile
from bldeif.utils.konfabulus import Konfabulator
from bldeif.bld_connector    import BLDConnector
#from bldeif.utils.auxloader  import ExtensionLoader
from bldeif.utils.eif_exception import ConfigurationError, NonFatalConfigurationError
from bldeif.utils.eif_exception import OperationalError, logAllExceptions

############################################################################################################

ARCHITECTURE_ACRONYM = 'eif'
__version__ = "0.9.8"

EXISTENCE_PROCLAMATION = """
************************************************************************************************************************

     CA Agile Central BuildConnector for %s  version %s  starting at: %s  with pid: %s 
           curdir: %s
          command: %s

************************************************************************************************************************
"""

LOCK_FILE  = 'LOCK.tmp'
STD_TS_FMT = '%Y-%m-%d %H:%M:%S Z'

THREE_DAYS = 3 * 86400

############################################################################################################

class BuildConnectorRunner(object):

    def __init__(self, args):
        """
            An instance of this class is responsible for basic command line parsing,
            pulling off the name of the target config file.
            Once that item is taken care of, the instance obtains an instance of a
            Konfabulator, a AuxiliaryClassLoader instance and and instance of an BLDConnector.
            The Konfabulator is delegated the task of reading the config file, the AuxiliaryClassLoader
            is delegated the task of pulling in any Extension classes.
            These instances are then provided to the BuildConnector instance.
            This instance then directs the BuildConnector instance to obtain unrecorded builds 
            from the target Build/CI system and reflect them in the Agile Central server.
        """
        if len(args) < 1:
            problem = ("Insufficient command line args, must be at least a config file name.")
            raise ConfigurationError(problem)

        self.default_log_file_name = True
        
        # this only allows a logfile spec of --logfile=<some_file_name>
        # TODO: consider allowing additional syntax  logfile=foo.log or --logfile foo.log
        log_spec = [arg for arg in args if arg.startswith('--logfile=')]
        if log_spec:
            self.logfile_name = log_spec[0].replace('--logfile=', '')
            self.default_log_file_name = False
            for spec in log_spec:
                args = [arg for arg in args if arg != spec]
        
        self.config_file_names = args
        if self.default_log_file_name:  # set it to first config file minus any '_config.yml' portion
            self.first_config = self.config_file_names[0]
            self.logfile_name = "log/%s.log" % self.first_config.replace('.yml', '').replace('_config', '')
            try:
                if not os.path.exists('log'):
                    os.makedirs('log')
            except Exception as msg:
                sys.stderr.write("Unable to locate or create the log sub-directory, %s\n" % msg)
                raise Exception

        self.log = ActivityLogger(self.logfile_name)
        logAllExceptions(True, self.log)
        self.preview   = False
        self.connector = None
        self.extension = {}


    def proclaim_existence(self, build_system_name):
        proc = ProcTable.targetProcess(os.getpid())
        now = time.strftime(STD_TS_FMT, time.gmtime(time.time()))
        cmd_elements = proc.cmdline.split()
        executable = cmd_elements[0]
        cmd_elements[0] = os.path.basename(executable)
        proc.cmdline = " ".join(cmd_elements)
        self.log.write(EXISTENCE_PROCLAMATION % (build_system_name, __version__, now, proc.pid, os.getcwd(), proc.cmdline))

    def acquireLock(self):
        """
            Check for conditions to proceed based on lock file absence/presence status.
            Acquisition of the lock is a green-light to proceed.
            Failure to acquire the lock prevents any further operation.
        """
        if LockFile.exists(LOCK_FILE):
            self.log.warning("A %s file exists" % LOCK_FILE)
            locker = LockFile.currentLockHolder(LOCK_FILE)
            if not LockFile.lockerIsRunning(LOCK_FILE, locker):
                message = ("A prior connector process (%s) did not clean up "
                           "the lock file on termination, proceeding with this run")
                self.log.warning(message % locker)
            else:
                self.log.error("Another connector process [%s] is still running, unable to proceed" % locker)
                raise ConfigurationError("Simultaneous processes for this connector are prohibited")

        LockFile.createLock(LOCK_FILE)
        return True

    def releaseLock(self):
        LockFile.destroyLock(LOCK_FILE)

    def run(self):
        own_lock = False
        build_system_name = self.identifyBuildSystemName()
        self.proclaim_existence(build_system_name)
        own_lock = self.acquireLock()

        try:
            for config_file in self.config_file_names:
                config_file_path = self.find_config_file(config_file)
                if not config_file_path:
                    raise ConfigurationError("No config file for '%s' found in the config subdir" % config_file)
                lf_name = "log/%s.log" % config_file.replace('.yml', '').replace('_config', '')
                self.log = ActivityLogger(lf_name)
                logAllExceptions(True, self.log)
                self._operateService(config_file_path)
        except Exception as msg:
            self.log.error(msg)
        finally:
            try:
                if own_lock: self.releaseLock()
            except Exception as msg:
                raise OperationalError("ERROR: unable to remove lock file '%s', %s" % (LOCK_FILE, msg))
        self.log.info('run completed')

    def identifyBuildSystemName(self):
        file_name = self.find_config_file(self.first_config)
        if not file_name:
            problem = "Unable to locate any config file for the name: '%s'" % self.first_config
            sys.stderr.write("ERROR: %s.  Correct this and run again.\n" % problem)
            sys.exit(1)

        bsn = 'UNKNOWN'
        limit = 5
        ix = 0
        with open(file_name, 'r', encoding="utf-8") as fcf:
            while ix < limit:
                text_line = fcf.readline()
                ix += 1
                mo = re.match(r'^(?P<bsn>[A-Z][A-Za-z]+)BuildConnector:$', text_line)
                if mo:
                    bsn = mo.group('bsn')
                    break
        if bsn == 'UNKNOWN':
            problem = "The config file for '%s' does not contain a valid Build Connector identifier." % self.first_config
            sys.stderr.write("ERROR: %s.  Correct this and run again.\n" % problem)
            sys.exit(2)

        return bsn

    def find_config_file(self, config_name):
        relative_path = 'config/%s' % config_name
        if os.path.exists(relative_path):
            return relative_path
        else:
            return None
        # valid_targets = ['%s' % config_name, '%s.yml' % config_name]
        # hits = [entry for entry in glob.glob('config/*') if config_name in entry]
        # if hits:
        #     return hits[0]
        # else:
        #     return None

    def _operateService(self, config_file_path):
        config_name = config_file_path.replace('config/', '')
        started = finished = elapsed = None
        self.connector = None
        self.log.info("processing to commence using content from %s" % config_file_path)

        last_conf_mod = time.strftime(STD_TS_FMT, time.gmtime(os.path.getmtime(config_file_path)))
        conf_file_size = os.path.getsize(config_file_path)
        self.log.info("%s last modified %s,  size: %d chars" % (config_file_path, last_conf_mod, conf_file_size))
        config = self.getConfiguration(config_file_path)

        this_run = time.time()     # be optimistic that the reflectBuildsInAgileCentral service will succeed
        now_zulu = time.strftime(STD_TS_FMT, time.gmtime(this_run)) # zulu <-- universal coordinated time <-- UTC

        self.time_file = TimeFile(self.buildTimeFileName(config_name), self.log)
        if self.time_file.exists():
            last_run = self.time_file.read() # the last_run is in Zulu time (UTC) as an epoch seconds value
        else:
            last_run = time.time() - (THREE_DAYS)
        last_run_zulu = time.strftime(STD_TS_FMT, time.gmtime(last_run))
        #self.log.info("Last Run %s --- Now %s" % (last_run_zulu, now_zulu))
        self.log.info("Time File value %s --- Now %s" % (last_run_zulu, now_zulu))

        self.connector = BLDConnector(config, self.log)
        self.log.debug("Got a BLDConnector instance, calling the BLDConnector.run ...")
        status, builds = self.connector.run(last_run, self.extension)
        # builds is an OrderedDict instance, keyed by job name, value is a list of Build instances

        finished = time.time()
        elapsed = int(round(finished - this_run))
        self.logServiceStatistics(config_name, builds, elapsed)

        if self.preview:
            self.log.info("Preview mode in effect, time.file File not written/updated")
            return
        if not status and builds:
            # Not writing the time.file may cause repetitive detection of Builds, 
            # but that is better than missing out on Builds altogether
            self.log.info("There was an error in processing so the time.file was not written")
            return

        if not builds:
            self.log.info('No builds were added during this run, so the time.file NOT updated.')
            return

        # we've added builds successfully, so update the Time File (config/<config>_time.file)
        try:
            #last_build_timestamp = min([v[-1].Start for k,v in builds.items()]).replace('T', ' ')[:19]
            earliest_build_start = min(build_list[-1].Start for job_name, build_list in builds.items())
            time_file_timestamp = earliest_build_start.replace('T', ' ')[:19]
            self.time_file.write(time_file_timestamp)
            self.log.info("time file written with value of %s Z" % time_file_timestamp)
        except Exception as msg:
            raise OperationalError(msg)

    def buildTimeFileName(self, config_file):
        if config_file:
            if config_file.endswith('.yml') or  config_file.endswith('.cfg'):
                time_file_name = config_file[0:-4] + '_time.file'
            else:
                time_file_name =  "%s_time.file" % config_file
        else:
            time_file_name = 'time.file'
        time_file_path = 'log/%s' % time_file_name
        return time_file_path


    def logServiceStatistics(self, config_name, builds, elapsed):
        """
            what we intend to append to the log...  
               bld_conn_config.yml: 32 additional builds reflected in AgileCentral
            and a line with the elapsed time taken in human readable form  
            (elapsed is in seconds (a float value))
        """
        for build in builds:
            preview_reminder = "(Preview Mode)" if self.preview else ""
            factoid = "%3d builds posted for job %s" % (len(builds[build]), build)
            self.log.info("%s: %s %s" % (config_name, factoid, preview_reminder))
        hours, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        if hours > 0:
            duration = "%s hours %s minutes %s seconds" % (hours, mins, secs)
        else:
            if mins > 0:
                duration = "%s minutes %s seconds" % (mins, secs)
            else:
                duration = "%s seconds" % secs
        self.log.info("%s: service run took %s" % (config_name, duration))


    def getConfiguration(self, config_file):
        try:
            config = Konfabulator(config_file, self.log)
        except NonFatalConfigurationError as msg:
            pass # info for this will have already been logged or blurted
        except Exception as msg:
            raise ConfigurationError(msg)
        svc_conf = config.topLevel('Service')
        self.preview = False
        if svc_conf and svc_conf.get('Preview', None) == True:
            self.preview = True
        self.log_level = 'Info'
        if svc_conf:
            ll = svc_conf.get('LogLevel', 'Info').title()
            if ll in ['Fatal', 'Error', 'Warn', 'Info', 'Debug']:
                self.log_level = ll
                self.log.setLevel(self.log_level)
            else:
                pass # bad LogLevel specified
            #if 'PostBatchExtension' in svc_conf:
            #    pba_class_name = svc_conf['PostBatchExtension']
            #    pba_class = ExtensionLoader().getExtension(pba_class_name)
            #    self.extension['PostBatch'] = pba_class()

        return config

