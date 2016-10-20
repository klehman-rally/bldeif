
import sys
import re
import types
import time
from calendar import timegm
import string  # for the digits chars
import urllib  # for the quote function

from bldeif.utils.eif_exception import ConfigurationError, OperationalError
from bldeif.connection import BLDConnection

from pyral import Rally, rallySettings, RallyRESTAPIError

############################################################################################

__version__ = "0.1.2"

VALID_ARTIFACT_PATTERN = None # set after config with artifact prefixes are known

ISO8601_TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

EXTENSION_SPEC_PATTERN = re.compile(r'^(?P<ext_class>[\w\.]+)\s*\((?P<ext_parm>[^\)]+)\)$')

############################################################################################

class MockBuild(object):
    def __init__(self, attr_val):
        for attr_name, value in attr_val.items():
            setattr(self, attr_name, value)

############################################################################################

class AgileCentralConnection(BLDConnection):

    def __init__(self, config, logger):
        super(AgileCentralConnection, self).__init__(logger)
        self.internalizeConfig(config) 
        self.log.info("Rally WSAPI Version %s" % self.rallyWSAPIVersion())
        self.integration_other_version = ""
        self.username_required = True
        self.password_required = True
        self.build_def = {}  # key by Project, then value is in turn a dict keyed by Job name with number and date
                             # of last Build
        self.job_bdf   = {}

    def name(self):
        return "AgileCentral"

    def version(self):
        global __version__
        return __version__

    # Rally Web Services version, do not modify unless tested!
    def rallyWSAPIVersion(self):
        return "v2.0"

    def getBackendVersion(self):
        """
            Conform to Connection subclass protocol which requires the version of 
            the system this instance is "connected" to.
        """
        return "Rally WSAPI %s" % self.rallyWSAPIVersion()

    def internalizeConfig(self, config):
        #super(AgileCentralConnection, self).internalizeConfig(config)
        super().internalizeConfig(config)

        server = config.get('Server', False)
        if not server:
            raise ConfigurationError("AgileCentral spec missing a value for Server")
        if 'http' in server.lower() or '/slm' in server.lower():
            self.log.error(self, "AgileCentral URL should be in the form 'rally1.rallydev.com'")
        self.server = server

        self.url = "https://%s/slm" % server

        self.apikey          = config.get("APIKey", config.get("API_Key", None))
        self.workspace_name  = config.get("Workspace", None)
        self.project_name    = config.get("Project",   None)
        self.restapi_debug   = config.get("Debug", False)
        self.restapi_logger  = self.log
        #self.restapi_logger = self.log if self.restapi_debug else None

    def setSourceIdentification(self, other_name, other_version):
        self.other_name = other_name
        self.integration_other_version  = other_version

    def get_custom_headers(self):
        custom_headers =  {}
        custom_headers['name']    = "AgileCentral Build Connector for %s" % self.other_name
        custom_headers['vendor']  = "Open Source contributors"
        custom_headers['version'] = self.version
        if self.integration_other_version: 
            spoke_versions = "%s - %s " % (self.version, self.integration_other_version)
            custom_headers['version'] = spoke_versions
        return custom_headers


    def connect(self):
####
       #https_proxy = os.environ.get('https_proxy', None) or os.environ.get('HTTPS_PROXY', None)
       #if https_proxy not in ["", None]:
       #    self.log.info("Proxy for HTTPS targets: %s" % https_proxy)
####
    
        self.log.info("Connecting to AgileCentral")
        custom_headers = self.get_custom_headers()

        try:
            before = time.time()
##            print("")
##            print("before call to pyral.Rally(): %s    using workspace name: %s" % (before, self.workspace_name))
##            print("   credentials:  username |%s|  password |%s|  apikey |%s|" % (self.username, self.password, self.apikey))
            self.agicen = Rally(self.server, username=self.username, password=self.password, apikey=self.apikey,
                                workspace=self.workspace_name, project=self.project_name,
                                version=self.rallyWSAPIVersion(), http_headers=custom_headers,
                                logger=self.restapi_logger, warn=False, debug=True)
            after = time.time()
##            print("after  call to pyral.Rally(): %s" % after)
##            print("initial Rally connect elapsed time: %6.3f  seconds" % (after - before))
##            sys.stdout.flush()
##
            if self.restapi_debug:
                self.agicen.enableLogging('agicen_builds.log')
        except Exception as msg:
            self.log.debug(msg)
            raise ConfigurationError("Unable to connect to Agile Central at %s as user %s" % \
                                         (self.server, self.username))
        self.log.info("Connected to Agile Central server: %s" % self.server)    

##        before = time.time()
        # verify the given workspace name exists
##        print("")
##        print("before call to agicen.getWorkspaces: %s" % before)
        all_workspaces = self.agicen.getWorkspaces()
##        after = time.time()
##        print("after  call to agicen.getWorkspaces: %s" % after)
##        print("agicen.getWorkspaces elapsed time: %6.3f  seconds" % (after - before))

        valid = [wksp for wksp in all_workspaces if wksp.Name == self.workspace_name]
        if not valid:
            problem = "Specified Workspace: '%s' not in list of workspaces " + \
                      "available for your credentials as user: %s" 
            raise ConfigurationError(problem % (self.workspace_name, self.username))
        self.log.info("    Workspace: %s" % self.workspace_name)
        self.log.info("    Project  : %s" % self.project_name)
        wksp = self.agicen.getWorkspace()
        prjt  = self.agicen.getProject()
        self.workspace_ref = wksp.ref
        self.project_ref   = prjt.ref

        # find all of the Projects under the AgileCentral_Project
##        before = time.time()
##        print("")
##        print("before call to agicen get Project: %s" % before)
        response = self.agicen.get('Project', fetch='Name', workspace=self.workspace_name, 
                                   project=self.project_name,
                                   projectScopeDown=True,
                                   pagesize=200)
        if response.errors or response.resultCount == 0:
            raise ConfigurationError('Unable to locate a Project with the name: %s in the target Workspace' % self.project_name)

        project_names = [proj.Name for proj in response]
##        after = time.time()
##        print("after  call to agicen get Project: %s" % after)
##        print("agicen.get Project  elapsed time: %6.3f  seconds  for  %d Projects" % ((after - before), len(project_names)))
##        print("")
        self.log.info("    %d sub-projects" % len(project_names))

        return True


    def disconnect(self):
        """
            Just reset our agicen instance variable to None
        """
        self.agicen = None


    def set_integration_header(self, header_info):
        self.integration_name    = header_info['name']
        self.integration_vendor  = header_info['vendor']
        self.integration_version = header_info['version']
        if 'other_version' in header_info:
            self.integration_other_version = header_info['other_version']

    def getRecentBuilds(self, ref_time):
        """
            Obtain all Builds created in Agile Central at or after the ref_time parameter
            (which is a struct_time object)
             in Python, ref_time will be a struct_time item:
               (tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst)
        """
        ref_time_readable = time.strftime("%Y-%m-%d %H:%M:%S Z", ref_time)
        ref_time_iso      = time.strftime("%Y-%m-%dT%H:%M:%SZ",  ref_time)
        self.log.info("Detecting recently added Agile Central Builds")
        selectors = ['CreationDate >= %s' % ref_time_iso]
        log_msg = '   recent Builds query: %s' %  ' and '.join(selectors)
        self.log.info(log_msg) 

        fetch_fields = "ObjectID,CreationDate,Number,Start,Status,Duration,BuildDefinition,Name," +\
                       "Workspace,Project,Uri,Message,Changesets"

        try:
            response = self.agicen.get('Build', 
                                       fetch=fetch_fields, 
                                      #fetch=True,
                                       query=selectors, 
                                       workspace=self.workspace_name, 
                                       project=self.project_name,
                                       projectScopeDown=True,
                                       order="CreationDate",
                                       pagesize=200, limit=2000 
                                      )
            self._checkForProblems(response)
        except Exception as msg:
            excp_type, excp_value, tb = sys.exc_info()
            mo = re.search(r"'(?P<ex_name>.+)'", str(excp_type))
            if mo:
                excp_type = mo.group('ex_name').replace('exceptions.', '')
                msg = '%s: %s\n' % (excp_type, str(excp_value))
            raise OperationalError(msg)

        log_msg = "  %d recently added Agile Central Builds detected"
        self.log.info(log_msg % response.resultCount)
        builds = {}
        for build in response:
            project    = build.BuildDefinition.Project.Name
            build_name = build.BuildDefinition.Name
            if project not in builds:
                builds[project] = {}
            if build_name not in builds[project]:
                builds[project][build_name] = []
            builds[project][build_name].append(build)
        return builds
    
    def _checkForProblems(self, response):
        """
            Examine the response to see if there is any content for the 'Errors' or 'Warnings' keys.
            and raise an Exception in that case.

            TODO: Maybe detection of errors/warnings should result in an OperationalError instead
        """
        if response.errors:
            raise Exception(response.errors[0][:80])
        if response.warnings:
            raise Exception(response.warnings[0][:80])
        return False

    
    def _fillHeavyCache(self):
        response = self.agicen.get('BuildDefinition', 
                                  #fetch=True,
                                  fetch='ObjectID,Name,Project,LastBuild,Uri', 
                                  query='Name != "Default Build Definition"',
                                  #workspace=self.workspace_ref, 
                                  workspace=self.workspace_name, 
                                  #project=None,
                                  project=self.project_name,
                                  projectScopeUp=False, projectScopeDown=True, 
                                  order='Project.Name,Name')

        if response.errors:
            raise OperationalError(str(response.errors))

        for build_defn in response:
##
           #print("_fillHeavyCache:  BuildDefinition  Project: %s  JobName: %s" % \
           #        (build_defn.Project.Name, build_defn.Name))
##
            project  = build_defn.Project.Name
            job_name = build_defn.Name
            if not project in self.build_def:
                self.build_def[project] = {}
            self.build_def[project][job_name] = build_defn


    def ensureBuildDefinitionExistence(self, job, project, strict_project, job_uri):
        """
            use the self.build_def dict keyed by project at first level, job name at second level
            to determine if the job has a BuildDefinition for it.

            Returns a pyral BuildDefinition instance corresponding to the job (and project)
        """
        # consult the "quick lookup" cache
        if job in self.job_bdf:
            return self.job_bdf[job]

        # do we have a "heavy cache" populated?  If not, do it now...
        if not self.build_def:
            self.log.debug("Detected build definition heavy cache is empty, populating ...")
            self._fillHeavyCache()

        no_entry = False
        # OK, the job is not in the "quick lookup" cache
        # so look in the "heavy cache" to see if the job exists for the given project
        if project in self.build_def:
            if job in self.build_def[project]:
                self.job_bdf[job] = self.build_def[project][job] 
                return self.job_bdf[job]

        # Determine whether it is permitted for the project to exist under another project
        # if strict_project == True then at this point we'll have to create a BuildDefinintion
        # for this project-job pair
        # if strict_project == False, then if the job exists in the "heavy cache" for some project (not the project parm)
        # then we'd grab the BuildDefinition ObjectID that exists in the "heavy cache" for the 
        # other project and this job name,  and stick it in the "quick lookup" cache
        """
        if strict_project == False:
            # and we find a job name match in the "heavy cache", use it and update the "quick lookup" cache, and return
            hits = []
            try:
                for proj in self.build_def.keys():
                    for job_name in self.build_def[proj]:
                        if job_name == job:
                            hits.append(self.build_def[proj][job_name])
                if hits: # there could be multiple, so we'll take the one having the most recent build
                    hits.sort(key=lambda build_defn: build_defn.LastBuild)
            except Exception as msg:
                print ("U-u-uge problem #6")
                raise OperationalError(msg)

            if hits:
                build_defn = hits[-1] # this will be the BuildDefinition with the most recent build
                self.job_bdf[job] = build_defn
                return build_defn
        """

        # At this point we haven't found a match for the job in the "heavy cache".
        # So, create a BuildDefinition for the job with the given project
        bdf_info = {'Workspace' : self.workspace_ref,
                    'Project'   : self.project_ref,
                    'Name'      : job,
                    'Uri'       : job_uri
                    #'Uri'      : maybe something like {base_url}/job/{job} where base_url comes from other spoke conn
                   }
        try:
            self.log.debug("Would be creating a BuildDefinition for job '%s' in Project '%s' ..." % (job, project))
            build_defn = self.agicen.create('BuildDefinition', bdf_info)
        except Exception as msg:
            self.log.error("Unable to create a BuildDefinition for job: '%s';  %s" % (job, msg))
            raise OperationalError("Unable to create a BuildDefinition for job: '%s';  %s" % (job, msg))        
        # Put the freshly minted BuildDefinition in the "heavy" and "quick lookup" cache and return it
        try:
            if project not in self.build_def:
                self.build_def[project] = {}
        except Exception as msg:
            print('Way bad iter problem?  %s' % msg)

        self.build_def[project][job] = build_defn
        self.job_bdf[job] = build_defn
        return build_defn


    def preCreate(self, int_work_item):
        """
        """
        # transform the CommitTimestamp from epoch seconds into ISO-8601'ish format
        #timestamp = int_work_item['CommitTimestamp']
        #iso8601_ts = time.strftime(ISO8601_TS_FORMAT, time.gmtime(timestamp))
        #int_work_item['CommitTimestamp'] = iso8601_ts

        # BuildDefinition has to be a ref
        # Number  is a string
        # Status  is a string
        # get Start in to iso8601 format
        # Duration is in seconds.milliseconds format
        # Uri is link to the originating build system job number page

        int_work_item['Workspace']       = self.workspace_ref 
        int_work_item['BuildDefinition'] = int_work_item['BuildDefinition'].ref

        return int_work_item


    def _createInternal(self, int_work_item):

        # snag the base Uri from the int_work_item['Uri'] burning off any ending '/' char
        base_uri = int_work_item['Uri']
        base_uri = base_uri[:-1] if base_uri and base_uri.endswith('/') else base_uri

        try:
            build = self.agicen.create('Build', int_work_item)
            self.log.debug("  Created Build: %-26.26s #%5s  %-8.8s %s" % (build.BuildDefinition.Name, build.Number, build.Status, build.Start))
        except Exception as msg:
            print("abc._createInternal detected an Exception, {0}".format(sys.exc_info()[1]))
            excp_type, excp_value, tb = sys.exc_info()
            mo = re.search(r"'(?P<ex_name>.+)'", str(excp_type))
            if mo:
                excp_type = mo.group('ex_name').replace('exceptions.', '')
                msg = '%s: %s\n' % (excp_type, str(excp_value))
            raise OperationalError(msg)

        return build


    def buildExists(self, build_defn, number):
        """
            Issue a query against Build to obtain the Build identified by build_defn.Name and number.
            Return a boolean indication of whether such an item exists.
        """
        criteria = ['BuildDefinition.Name = %s' % build_defn.Name, 'Number = %s' % number]
        response = self.agicen.get('Build', fetch="CreationDate,Number,Name,BuildDefinition", query=criteria,
                                            workspace=self.workspace_name, project=self.project_name, projectScopeDown=True)
        return response.status_code == 200 and response.resultCount > 0

