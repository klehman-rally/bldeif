
# This is the "large stone" level operation of the bldeif infrastructure,
# wherein the two connections held by the connector get instantiated, 
# connected to their respective systems and exercised.

import sys, os, platform
import time
import re
from collections import OrderedDict

from bldeif.utils.eif_exception   import FatalError, ConfigurationError, OperationalError
from bldeif.utils.claslo          import ClassLoader

##############################################################################################

__version__ = "1.0.0"

PLUGIN_SPEC_PATTERN       = re.compile(r'^(?P<plugin_class>\w+)\s*\((?P<plugin_config>[^\)]*)\)\s*$')
PLAIN_PLUGIN_SPEC_PATTERN = re.compile(r'(?P<plugin_class>\w+)\s*$')

ARCHITECTURE_PKG = 'bldeif'

##############################################################################################

class BLDConnector:

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

        if not self.validate():  # basically just calls validate on both connection instances
            raise ConfigurationError("Validation failed")
        self.log.info("Initialization complete: Delegate connections operational, ready for scan/reflect ops")


    def internalizeConfig(self, config):
        self.agicen_conf = config.topLevel('AgileCentral')
        self.bld_conf    = config.topLevel(self.bld_name)
        if not 'AgileCentral_DefaultBuildProject' in self.bld_conf:
            msg = "The Jenkins section of the config is missing AgileCentral_DefaultBuildProject property"
            raise ConfigurationError(msg)
        if not self.bld_conf['AgileCentral_DefaultBuildProject']:  # but no value exists for this...
            msg = "The Jenkins section of the config is missing a value for AgileCentral_DefaultBuildProject property"
            raise ConfigurationError(msg)
        self.agicen_conf['Project'] = self.bld_conf['AgileCentral_DefaultBuildProject']
        self.svc_conf    = config.topLevel('Service')
        self.max_builds  = self.svc_conf.get('MaxBuilds', 20)
        default_project = self.agicen_conf['Project']

        valid_config_items = ['Preview', 'LogLevel', 'MaxBuilds', 'ShowVCSData' ]
        svc_conf = config.topLevel('Service')
        invalid_config_items = [item for item in svc_conf.keys() if item not in valid_config_items]
        if invalid_config_items:
            problem = "Service section of the config contained these invalid entries: %s" % ", ".join(invalid_config_items)
            raise ConfigurationError(problem)

        # create a list of AgileCentral_Project values, start with the default project value
        # and then add add as you see overrides in the config.
        # eventually, we'll strip out any duplicates
        self.target_projects = [default_project]  # the default project always is considered for obtaining build info

        if "Views" in self.bld_conf:
            self.views = self.bld_conf["Views"]
            if not self.views:
                msg = "Views section of the config is empty"
                raise ConfigurationError(msg)
            for view in self.views:
                view_name = view['View']
                self.target_projects.append(view.get('AgileCentral_Project', default_project))

        if "Folders" in self.bld_conf:
            self.folders = self.bld_conf["Folders"]
            if not self.folders:
                msg = "Folders section of the config is empty"
                raise ConfigurationError(msg)
            for folder_conf in self.folders:
                folder_display_name = folder_conf['Folder']
                self.target_projects.append(folder_conf.get('AgileCentral_Project', default_project))

        if "Jobs" in self.bld_conf:
            self.jobs = self.bld_conf["Jobs"]
            if not self.jobs:
                msg = "Jobs section of the config is empty"
                raise ConfigurationError(msg)
            for job in self.jobs:
                job_name = job['Job']
                self.target_projects.append(job.get('AgileCentral_Project', default_project))
        self.target_projects = list(set(self.target_projects))  # to obtain unique project names


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
        if not self.agicen_conn.validateProjects(self.target_projects):
            self.log.info("AgileCentralConnection validation for Projects failed")
            return False
        self.log.info("AgileCentralConnection validation succeeded")

        if not self.bld_conn.validate():
            self.log.info("%sConnection validation failed" % self.bld_name)
            return False
        self.log.info("%sConnection validation succeeded" % self.bld_name)
        self.bld_conn.dumpTargets()
        self.bld_conn.showQualifiedJobs()

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
        recent_agicen_builds = agicen.getRecentBuilds(agicen_ref_time, self.target_projects)
        recent_bld_builds    =    bld.getRecentBuilds(bld_ref_time)
        unrecorded_builds = self._identifyUnrecordedBuilds(recent_agicen_builds, recent_bld_builds)
        self.log.info("unrecorded Builds count: %d" % len(unrecorded_builds))
        self.log.info("no more than %d builds per job will be recorded on this run" % self.max_builds)
        if self.svc_conf.get('ShowVCSData', False):
            self.dumpChangesetInfo(unrecorded_builds)

        recorded_builds = OrderedDict()
        builds_posted = {}
        # sort the unrecorded_builds into build chrono order, oldest to most recent, then project and job
        unrecorded_builds.sort(key=lambda build_info: (build_info[1].timestamp, build_info[2], build_info[1]))
        self.log.debug("About to process %d unrecorded builds" % len(unrecorded_builds))
        for job, build, project, view in unrecorded_builds:
            if build.result == 'None':
                self.log.warn("%s #%s job/build was not processed because is still running" % (job, build.number))
                continue
            #self.log.debug("current job: %s  build: %s" % (job, build))
            if not job in builds_posted:
                builds_posted[job] = 0
            if builds_posted[job] >= self.max_builds:
                continue
            if preview_mode:
                continue

            try:
                changesets, build_definition = agicen.prepAgileCentralBuildPrerequisites(job, build, project)
            except Exception as msg:
                self.log.error('OperationalException prepACBuildPrerequisites - %s' % msg)
                continue

            try:
                agicen_build, status = self.postBuildToAgileCentral(build_definition, build, changesets, job)
            except Exception as msg:
                self.log.error('OperationalException postingACBuild - %s' % msg)
                continue

            if agicen_build and status == 'posted':
                builds_posted[job] += 1
                if job not in recorded_builds:
                    recorded_builds[job] = []
                recorded_builds[job].append(agicen_build)
            status = True

        return status, recorded_builds

    def postBuildToAgileCentral(self, build_defn, build, changesets, job):
        desc = '%s %s #%s | %s | %s  not yet reflected in Agile Central'
        # add that "collection" as the Build's Changesets collection                                                                 bts = time.strftime("%Y-%m-%d %H:%M:%S Z", time.gmtime(build.timestamp / 1000.0))
        # self.log.debug(desc % (pm_tag, job, build.number, build.result, bts))
        build_data = build.as_tuple_data()
        info = OrderedDict(build_data)
        info['BuildDefinition'] = build_defn
        if changesets:
            info['Changesets'] = changesets
        existing_agicen_build = self.agicen_conn.buildExists(build_defn, build.number)
        if existing_agicen_build:
            self.log.debug('Build #{0} for {1} already recorded, skipping...'.format(build.number, job))
            return existing_agicen_build, 'skipped'
        agicen_build = self.agicen_conn.createBuild(info)
        return agicen_build, 'posted'

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


    def _showBuildInformation(self, agicen_builds, bld_builds):
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


    def _identifyUnrecordedBuilds(self, agicen_builds, bld_builds):
        """
            If there are items in the agicen_builds for which there is  a counterpart in 
            the bld_builds, the information has already been reflected in Agile Central.  --> NOOP

            If there are items in the bld_builds   for which there is no counterpart in
            the agicen_builds, those items are candidates to be reflected in Agile Central --> REFLECT

            If there are items in the agicen_builds for which there is no counterpart in 
            the bld_builds, information has been lost,  dat would be some bad... --> ERROR
        """
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
                        job_fqp = job.fully_qualified_path()
                        if job_fqp in job_builds:
                            ac_build_nums = [int(bld.Number) for bld in job_builds[job_fqp]]
                            if build.number in ac_build_nums:
                                reflected_builds.append((job, build, project, view))
                                continue
                    unrecorded_builds.append((job, build, project, view))
                    
        return unrecorded_builds


    def dumpChangesetInfo(self, builds):
        for job, build, project, view in builds:
            if not build.changeSets:
                continue
            self.log.debug(build)
            for cs in build.changeSets:
                self.log.debug(str(cs))


    def detectCommitsForJenkinsBuild(self, build):
        shas = set([cs.id for cs in build.changeSets])

        bacs = []
        for sha in shas:
            ac_changeset = self.agicen_conn.retrieveChangeset(sha)
            if ac_changeset:
                bacs.append(ac_changeset)

        return bacs

####################################################################################
