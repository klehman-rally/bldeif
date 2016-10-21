
# This is the "large stone" level operation of the bldeif infrastructure,
# wherein the two connections held by the connector get instantiated, 
# connected to their respective systems and exercised.

import sys, os, platform
import time
import re
from datetime    import datetime
from collections import OrderedDict

import bldeif

from bldeif.connection            import BLDConnection
from bldeif.utils.klog            import ActivityLogger
from bldeif.utils.eif_exception   import FatalError, ConfigurationError, OperationalError
from bldeif.utils.claslo          import ClassLoader

##############################################################################################

__version__ = "0.3.6"

PLUGIN_SPEC_PATTERN       = re.compile(r'^(?P<plugin_class>\w+)\s*\((?P<plugin_config>[^\)]*)\)\s*$')
PLAIN_PLUGIN_SPEC_PATTERN = re.compile(r'(?P<plugin_class>\w+)\s*$')

ARCHITECTURE_PKG = 'bldeif'

##############################################################################################

class BLDConnector(object):

    def __init__(self, config, logger):
        self.config = config
        self.log    = logger

        conn_sections = []
        try:
            conn_sections = [section for section in config.topLevels()
                                      if section not in ['Service']]
            if len(conn_sections) != 2:
                raise ConfigurationError('Config does not contain two connection sections')
        except Exception:
            raise ConfigurationError('Config file lacks sufficient information for BLDConnector')

        self.agicen_conn = None
        self.bld_conn    = None

        self.bld_name   = [name for name in conn_sections if not name.startswith('AgileCentral')][0]
        self.log.info("Agile Central BLD Connector for %s, version %s" % (self.bld_name, __version__))
        uname_fields = platform.uname()
        self.log.info("Python platform: %s %s" % (uname_fields[0], uname_fields[2]))
        self.log.info("Python  version: %s" % sys.version.split()[0])

        self.internalizeConfig(config)

        droid = ClassLoader()
        agicen_conn_class_name = config.connectionClassName('AgileCentral')
        bld_conn_class_name    = config.connectionClassName(self.bld_name)

        try:
            self.agicen_conn_class = droid.loadConnectionClass(agicen_conn_class_name, pkgdir=ARCHITECTURE_PKG)
        except Exception as msg:
            raise FatalError('Unable to load AgileCentralBLDConnection class, %s' % msg)
        try:
            self.bld_conn_class = droid.loadConnectionClass(bld_conn_class_name, pkgdir=ARCHITECTURE_PKG)
        except Exception as msg:
            raise FatalError('Unable to load %sConnection class, %s' % (self.bld_name, msg))

        self.establishConnections()

        self.validate()  # basically just calls validate on both connection instances
        self.log.info("Initialization complete: Delegate connections operational, ready for scan/reflect ops")


    def internalizeConfig(self, config):
        self.agicen_conf = config.topLevel('AgileCentral')
        self.bld_conf    = config.topLevel(self.bld_name)
        self.agicen_conf['Project'] = self.bld_conf['AgileCentral_DefaultBuildProject']
        self.svc_conf    = config.topLevel('Service')

        self.strict_project = self.svc_conf.get('StrictProject', False)
        self.max_builds     = self.svc_conf.get('MaxBuilds', 20)

    def establishConnections(self):
        self.agicen_conn = self.agicen_conn_class(self.agicen_conf, self.log)
        self.bld_conn    =    self.bld_conn_class(self.bld_conf,    self.log)

        self.bld_conn.connect()  # we do this before agicen_conn to be able to get the bld backend version
        bld_backend_version = self.bld_conn.getBackendVersion()

        if self.agicen_conn and self.bld_conn and getattr(self.agicen_conn, 'set_integration_header'):
            agicen_headers = {'name'    : 'Agile Central BLDConnector for %s' % self.bld_name,
                              'version' : __version__,
                              'vendor'  : 'Open Source contributors',
                              'other_version' : bld_backend_version
                            }
            self.agicen_conn.set_integration_header(agicen_headers)
        self.agicen_conn.setSourceIdentification(self.bld_conn.name(), self.bld_conn.backend_version)
        self.agicen_conn.connect()  # so we can use it in our X-Rally-Integrations header items here


    def validate(self):
        """
            This calls the validate method on both the Agile Central and the BLD connections
        """
        self.log.info("Connector validation starting")

        if not self.agicen_conn.validate():
            self.log.info("AgileCentralConnection validation failed")
            return False
        self.log.info("AgileCentralConnection validation succeeded")

        if not self.bld_conn.validate():
            self.log.info("%sConnection validation failed" % self.bld_name)
            return False
        self.log.info("%sConnection validation succeeded" % self.bld_name)

        self.log.info("Connector validation completed")

        return True


    def run(self, last_run, extension):
        """
            The real beef is in the call to reflectBuildsInAgileCentral.
            The facility for extensions is not yet implemented for BLD connectors,
            so the pre and post batch calls are currently no-ops.
        """
        self.preBatch(extension)
        status, builds = self.reflectBuildsInAgileCentral(last_run)
        self.postBatch(extension, status, builds)
        return status, builds


    def preBatch(self, extension):
        """
        """
        if extension and 'PreBatchAction' in extension:
            preba = extension['PreBatchAction']
            preba.service()


    def postBatch(self, extension, status, builds):
        """
        """
        if extension and 'PostBatchAction' in extension:
            postba = extension['PostBatchAction']
            postba.service(status, builds)


    def reflectBuildsInAgileCentral(self, last_run):
        """
            The last run time is passed to Connection objects in UTC;
            they are responsible for converting if necessary. 
            Time in log messages is always reported in UTC (aka Z or Zulu time).
        """
        status = False
        agicen = self.agicen_conn
        bld    = self.bld_conn

        preview_mode = self.svc_conf.get('Preview', False)

        pm_tag = ''
        action = 'adding'
        if preview_mode:
            pm_tag = "Preview: "
            action = "would add"
            self.log.info('***** Preview Mode *****   (no Builds will be created in Agile Central)')


        agicen_ref_time, bld_ref_time = self.getRefTimes(last_run)
        recent_agicen_builds = agicen.getRecentBuilds(agicen_ref_time)
        recent_bld_builds    =    bld.getRecentBuilds(bld_ref_time)
        unrecorded_builds    = self._identifyUnrecordedBuilds(recent_agicen_builds,
                                                                recent_bld_builds,
                                                                bld_ref_time)
        self.log.info("unrecorded Builds count: %d" % len(unrecorded_builds))
        self.log.info("no more than %d builds per job will be recorded on this run" % self.max_builds)

        recorded_builds = OrderedDict()
        builds_posted = {}
        # sort the unrecorded_builds into build chrono order, oldest to most recent, then project and job
        unrecorded_builds.sort(key=lambda build_info: (build_info[1].timestamp, build_info[2], build_info[1]))
        for job, build, project, view in unrecorded_builds:
            if build.result == 'None':
                #stragglers.append(build)
                self.log.warn("%s #%s job/build was not processed because is still running" %(job, build.number))
                continue
            #self.log.debug("current job: %s  build: %s" % (job, build))
            if not job in builds_posted:
                builds_posted[job] = 0
            if builds_posted[job] >= self.max_builds:
                continue

            desc = '%s %s #%s | %s | %s  not yet reflected in Agile Central'
            cts = time.strftime("%Y-%m-%d %H:%M:%S Z", time.gmtime(build.timestamp/1000.0))
            #self.log.debug(desc % (pm_tag, job, build.number, build.result, cts))
            job_uri = bld.constructJobUri(job)
            job_url = bld.constructJobBuildUrl(job, build.number)
            start_time = datetime.utcfromtimestamp(build.timestamp / 1000.0).strftime('%Y-%m-%dT%H:%M:%SZ')
            build_data = [ ('Number', build.number), ('Status', str(build.result)), ('Start', start_time), ('Duration', build.duration / 1000.0), ('Uri', job_url) ]
            info = OrderedDict(build_data)

            if preview_mode:
                continue

            build_defn = agicen.ensureBuildDefinitionExistence(job, project, self.strict_project, job_uri)
            if not agicen.buildExists(build_defn, build.number):
                info['BuildDefinition'] = build_defn
                agicen_build = agicen.createBuild(info)
                if job not in recorded_builds:
                    recorded_builds[job] = []
                recorded_builds[job].append(agicen_build)
                builds_posted[job] += 1
            else:
                self.log.debug('Build #{0} for {1} already recorded, skipping...'.format(build.number, job))

            status = True

        return status, recorded_builds


    def getRefTimes(self, last_run):
        """
            last_run is provided as an epoch seconds value. 
            Return a two-tuple of the reference time to be used for obtaining the 
            recent Builds in AgileCentral and the reference time to be used for 
            obtaining the recent builds in the target BLD system.
        """
        agicen_lookback = self.agicen_conn.lookback
        bld_lookback    = self.bld_conn.lookback 
        agicen_ref_time = time.gmtime(last_run - agicen_lookback)
        bld_ref_time    = time.gmtime(last_run - bld_lookback)
        return agicen_ref_time, bld_ref_time


    def _identifyUnrecordedBuilds(self, agicen_builds, bld_builds, ref_time):
        """
            If there are items in the agicen_builds for which there is  a counterpart in 
            the bld_builds, the information has already been reflected in Agile Central.  --> NOOP

            If there are items in the bld_builds   for which there is no counterpart in
            the agicen_builds, those items are candidates to be reflected in Agile Central --> REFLECT

            If there are items in the agicen_builds for which there is no counterpart in 
            the bld_builds, information has been lost,  dat would be some bad... --> ERROR
        """
##
        for project, job_builds in agicen_builds.items():
            print("Agile Central project: %s" % project)
            for job, builds in job_builds.items():
                print("    %-36.36s : %3d build items" % (job, len(builds)))
        print("")

##
        for view, job_builds in bld_builds.items():
            print("Jenkins View: %s" % view)
            for job, builds in job_builds.items():
                print("    %-36.36s : %3d build items" % (job, len(builds)))
        print("")
##
        reflected_builds   = []
        unrecorded_builds  = []

        for view_and_project, jobs in bld_builds.items():
            view, project = view_and_project.split('::', 1)
            for job, builds in jobs.items():
                for build in builds:
                    # look first for a matching project key in agicen_builds
                    if project in agicen_builds:
                        job_builds = agicen_builds[project]
                        # now look for a matching job in job_builds
                        if job in job_builds:
                            ac_build_nums = [int(bld.Number) for bld in job_builds[job]]
                            if build.number in ac_build_nums:
                                reflected_builds.append((job, build, project, view))
                                continue
                    unrecorded_builds.append((job, build, project, view))
                    
        return unrecorded_builds

####################################################################################

