
import sys,os
import re
import time
from datetime import datetime
import bldeif.utils.ac_prefixes  as utils

from bldeif.utils.eif_exception import ConfigurationError, OperationalError
from bldeif.connection import BLDConnection

from pyral import Rally, rallySettings, RallyRESTAPIError

############################################################################################

__version__ = "1.0.0"

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
        super().__init__(logger)
        self.internalizeConfig(config) 
        self.log.info("Rally WSAPI Version %s" % self.rallyWSAPIVersion())
        self.integration_other_version = ""
        self.username_required = True
        self.password_required = True
        self.build_def = {}  # key by Project, then value is in turn a dict keyed by Job name with number and date
                             # of last Build

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
        super().internalizeConfig(config)

        server = config.get('Server', 'rally1.rallydev.com')
        if 'http' in server.lower() or '/slm' in server.lower():
            self.log.error(self, "AgileCentral URL should be in the form 'rally1.rallydev.com'")
        self.server = server

        self.url = "https://%s/slm" % server
        self.port = config.get('Port', '443')
        self.apikey          = config.get("APIKey", config.get("API_Key", None))
        self.workspace_name  = config.get("Workspace", None)
        self.project_name    = config.get("Project",   None)  # This gets bled in by the BLDConnector
        self.restapi_debug   = config.get("Debug", False)
        self.restapi_logger  = self.log

        self.proxy = None
        if self.proxy_server:
            self.proxy  = "%s://%s:%s" % (self.proxy_protocol, self.proxy_server, self.proxy_port)
            if self.proxy_username and self.proxy_password:
                self.proxy  = "%s://%s:%s@%s:%s" % (self.proxy_protocol, self.proxy_username, self.proxy_password, self.proxy_server, self.proxy_port)

        valid_config_items = ['Server', 'Port', 'APIKey','Workspace','Project','Username','Password','ProxyProtocol', 'ProxyServer','ProxyPort','ProxyUser','ProxyUsername', 'ProxyPassword','Debug', 'Lookback']
        invalid_config_items = [item for item in config.keys() if item not in valid_config_items]
        if invalid_config_items:
            problem = "AgileCentral section of the config contained these invalid entries: %s" % ", ".join(invalid_config_items)
            raise ConfigurationError(problem)

    def validate(self):
        satisfactory = True

        if self.username_required:
            if not self.username and not self.apikey:
                self.log.error("<Username> is required in the config file")
                satisfactory = False
            #else:
            #    self.log.debug(
            #        '%s - user entry "%s" detected in config file' % (self.__class__.__name__, self.username))

        if self.password_required:
            if not self.password and not self.apikey:
                self.log.error("<Password> is required in the config file")
                satisfactory = False
            #else:
            #    self.log.debug('%s - password entry detected in config file' % self.__class__.__name__)

        return satisfactory

    def validateProjects(self, target_projects):
        """
            make requests to AgileCentral to retrieve basic info for each project in target_projects.
            If any project name in target_projects does NOT have a corresponding project in AgileCentral
            raise and Exception naming the offending project.
        """
        try:
            mep_projects     = list(set([project for project in target_projects if ' // '     in project]))
        except Exception as msg:
            raise OperationalError("%s %s" % ("error in agicen_bld_connection.py for getting mep_projects", msg))
        try:
            non_mep_projects = list(set([project for project in target_projects if ' // ' not in project]))
        except Exception as msg:
            raise OperationalError("%s %s" % ("error in agicen_bld_connection.py for getting non_mep_projects", msg))
        query = self._construct_ored_Name_query(non_mep_projects)
        response = self.agicen.get('Project', fetch='Name,ObjectID', query=query, workspace=self.workspace_name,
                                   project=None, projectScopeDown=True, pagesize=200)
        if response.errors or response.resultCount == 0:
            raise ConfigurationError(
                'Unable to locate a Project with the name: %s in the target Workspace: %s' % (self.project_name, self.workspace_name))

        found_projects = [project for project in response]
        try:
            found_project_names = list(set([p.Name for p in found_projects]))
        except Exception as msg:
            raise OperationalError("%s %s" % ("error in agicen_bld_connection.py for getting found_project_names", msg))
        bogus = [name for name in target_projects if name not in found_project_names]
        try:
            real_bogus = set(bogus) - set(mep_projects)
        except Exception as msg:
            raise OperationalError("%s %s" % ("error in agicen_bld_connection.py for getting real_bogus", msg))
        if real_bogus:
            problem = "These projects mentioned in the config were not located in AgileCentral Workspace %s: %s" % (self.workspace_name, ",".join(real_bogus))
            self.log.error(problem)
            return False

        #deal with the mep_projects
        for mep in mep_projects:
            proj = self.agicen.getProject(mep)
            if proj:
                found_projects.append(proj)

        self._project_cache = {proj.Name : proj.ref for proj in found_projects}
        return True


    def _construct_ored_Name_query(self, target_projects):
        if not target_projects: return ''
        initial = '(Name = "%s")' % target_projects[0]
        or_string = initial
        for project in target_projects[1:]:
            or_string = '(%s OR (Name = "%s"))' % (or_string, project)
        return or_string

        #return "(%s)" % or_string[1:-1]

    def setSourceIdentification(self, other_name, other_version):
        self.other_name = other_name
        self.integration_other_version  = other_version

    def get_custom_headers(self):
        custom_headers =  {}
        custom_headers['name']    = "AgileCentral Build Connector for %s" % self.other_name
        custom_headers['vendor']  = "CA Technologies"
        custom_headers['version'] = self.version
        if self.integration_other_version: 
            spoke_versions = "%s - %s " % (self.version, self.integration_other_version)
            custom_headers['version'] = spoke_versions
        return custom_headers


    def connect(self):
        if self.proxy:
            self.log.info("Proxy for AgileCentral connection:  %s" % self.proxy)
            os.environ['HTTPS_PROXY'] = self.proxy

        self.log.info("Connecting to AgileCentral")
        custom_headers = self.get_custom_headers()

        try:
            before = time.time()
##            print("")
##            print("before call to pyral.Rally(): %s    using workspace name: %s" % (before, self.workspace_name))
##            print("   credentials:  username |%s|  password |%s|  apikey |%s|" % (self.username, self.password, self.apikey))
            self.agicen = Rally(self.server, user=self.username, password=self.password, apikey=self.apikey,
                                workspace=self.workspace_name, project=self.project_name,
                                version=self.rallyWSAPIVersion(), http_headers=custom_headers,
                                server_ping=False, isolated_workspace=True,
                                logger=self.restapi_logger, warn=False, debug=True)
            after = time.time()
##            print("after  call to pyral.Rally(): %s" % after)
##            print("initial Rally connect elapsed time: %6.3f  seconds" % (after - before))
##            sys.stdout.flush()
##
            if self.restapi_debug:
                self.agicen.enableLogging('agicen_builds.log')
        except Exception as msg:
            raise ConfigurationError("Unable to connect to Agile Central at %s: %s" % \
                                         (self.server, msg))
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

        # detect any duplicate project names
        self.project_bucket = {}
        for proj in response:
            if proj.Name not in self.project_bucket:
                self.project_bucket[proj.Name] = 0
            self.project_bucket[proj.Name] += 1
        self.duplicated_project_names = [p for p,c in self.project_bucket.items() if c != 1]

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


    def getRecentBuilds(self, ref_time, projects):
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
        builds = {}

        for project in projects:
            response = self._retrieveBuilds(project, selectors)
            log_msg = "  %d recently added Agile Central Builds detected for project: %s"
            self.log.info(log_msg % (response.resultCount, project))

            for build in response:
                build_name = build.BuildDefinition.Name
                if project not in builds:
                    builds[project] = {}
                if build_name not in builds[project]:
                    builds[project][build_name] = []
                builds[project][build_name].append(build)
        return builds


    def _retrieveBuilds(self, project, selectors):
        fetch_fields = "ObjectID,CreationDate,Number,Start,Status,Duration,BuildDefinition,Name," +\
                       "Workspace,Project,Uri,Message,Changesets"
        try:
            response = self.agicen.get('Build',
                                       fetch=fetch_fields,
                                       query=selectors,
                                       workspace=self.workspace_name,
                                       project=project,
                                       projectScopeDown=False,
                                       projectScopeUp=False,
                                       order="CreationDate",
                                       pagesize=1000
                                      )
        except Exception as msg:
            excp_type, excp_value, tb = sys.exc_info()
            mo = re.search(r"'(?P<ex_name>.+)'", str(excp_type))
            if mo:
                excp_type = mo.group('ex_name').replace('exceptions.', '')
                msg = '%s: %s\n' % (excp_type, str(excp_value))
            raise OperationalError(msg)

        # Examine the response to see if there is any content for the 'Errors' or 'Warnings' keys.
        # and raise an Exception in that case.
        if response.errors:
            raise Exception(response.errors[0][:80])
        if response.warnings:
            raise Exception(response.warnings[0][:80])

        return response

    def retrieveChangeset(self, sha):
        query = 'Revision = %s' % sha
        response = self.agicen.get('Changeset', fetch='ObjectID', query=query,
                                    workspace=self.workspace_name,project=None)
        # should we check for errors or warnings?
        if response.resultCount > 0:
            return response.next()
        return None

    def _fillBuildDefinitionCache(self, project):
        response = self.agicen.get('BuildDefinition',
                                  fetch='ObjectID,Name,Project,LastBuild,Uri', 
                                  query='Name != "Default Build Definition"',
                                  workspace=self.workspace_name,
                                  project=project,
                                  projectScopeUp=False, projectScopeDown=False,
                                  order='Project.Name,Name')

        if response.errors:
            raise OperationalError(str(response.errors))

        for build_defn in response:
##
           #print("_fillBuildDefinitionCache:  BuildDefinition  Project: %s  JobName: %s" % \
           #        (build_defn.Project.Name, build_defn.Name))
##
            job_name = build_defn.Name
            if not project in self.build_def:
                self.build_def[project] = {}
            self.build_def[project][job_name] = build_defn


    def prepAgileCentralBuildPrerequisites(self, job, target_build, project):
        """
            Given a target_build which has information about a build that has been completed on
             some target build system, accommodate/create the following:
                SCMRepository    based on the target_build.repo value
                Changesets       based on the target_build.changeSets
                BuildDefinition  based on the target_build.job  (which is the job name)
             Any or all or none of these things may already be present in AgileCentral, and if
             not create what is necessary.
             Return back the SCMRepository, Changesets, and BuildDefinition.
             These will be a  pyral entity for each or a list of pyral entities in the case of Changesets
        """
        changesets = None
        if target_build.changeSets:
            ac_changesets, missing_changesets = self.getCorrespondingChangesets(target_build)
            # check for ac_changesets, if present take the SCMRepository of the first in the list (very arbitrary!)
            if ac_changesets:
                first_changeset = list(ac_changesets)[0]
                criteria = 'Name = "%s"' % first_changeset.SCMRepository.Name
                scm_repo = self.agicen.get('SCMRepository', fetch="Name", query=criteria, instance=True)
            else:
                scm_repo = self.ensureSCMRepositoryExists(target_build.repository, target_build.vcs)

            changesets = self.ensureChangesetsExist(scm_repo, project, ac_changesets, missing_changesets)

        build_defn = self.ensureBuildDefinitionExists(job.fully_qualified_path(), project, target_build.vcs)
        return changesets, build_defn


    def getCorrespondingChangesets(self, build) :
        build_changesets = build.changeSets
        if not build_changesets:
            return [], []
        ids = [cs.commitId for cs in build_changesets]
        scm_repository_name = ''
        for id in ids:
            criteria = '(Revision = "{0}")'.format(id)
            response = self.agicen.get('Changeset', fetch="ObjectID,Revision,SCMRepository,Name", query=criteria)
            if response.resultCount:
                hits = [item for item in response]
                scm_repository_name = hits[0].SCMRepository.Name
                break

        if scm_repository_name:
            fields = "ObjectID,Revision,SCMRepository,Name"
            query = "(SCMRepository.Name = {})".format(scm_repository_name)

            response = self.agicen.get('Changeset', fetch=fields, query=query, order="CreationDate", pagesize=200)
            if response.resultCount:
                changesets = [item for item in response]

            build_changesets_revisions = [bc.commitId for bc in build_changesets]
            ac_changesets_revisions    = [cs.Revision for cs in changesets]

            try:
                missing = [bc for bc in build_changesets if bc.commitId not in ac_changesets_revisions]
            except Exception as msg:
                raise OperationalError("%s %s" % ("error in agicen_bld_connection.py for getting missing", msg))
            try:
                present = [cs for cs in changesets if cs.Revision in build_changesets_revisions]
            except Exception as msg:
                raise OperationalError("%s %s" % ("error in agicen_bld_connection.py for getting present", msg))
            return present, missing
        else:
            vcs_type = build_changesets[0].vcs
            self.ensureSCMRepositoryExists(build.repository, vcs_type)
            return [], build_changesets


    def ensureSCMRepositoryExists(self, repo_name, vcs_type):
        """
            Use the WSAPI case-insensitive Name contains ... syntax so that we can "match" a name like 'wombat' to 'Wombat'
            in case the users have manually already created a 'Wombat' SCMRepository either manually or via VCS Connector
        """
        repo_name = repo_name.replace('\\','/')
        name = repo_name.split('/')[-1]
        criteria = '(Name contains "{0}")'.format(name)
        response = self.agicen.get('SCMRepository', fetch="Name,ObjectID", query = criteria, project=None)
        if response.resultCount:
            scm_repos = [item for item in response]
            exact_matches = [scm_repo for scm_repo in scm_repos if scm_repo.Name.lower() == repo_name.lower()]
            if exact_matches:
                return exact_matches[0]

        scm_repo_payload = {'Name': repo_name, 'SCMType': vcs_type}
        try:
            scm_repo = self.agicen.create('SCMRepository', scm_repo_payload)
            self.log.info("Created SCMRepository %s (%s)" % (scm_repo.Name, scm_repo.ObjectID))
        except RallyRESTAPIError as msg:
            self.log.error('Error detected on attempt to create SCMRepository %s' % msg)
            raise OperationalError("Could not create SCMRepository %s" % repo_name)

        return scm_repo


    def ensureChangesetsExist(self, scm_repo, project, ac_changesets, missing_changesets):
        all_mentioned_artifact_fids = {mc.commitId: self.parseForArtifacts(mc.message) for mc in missing_changesets}
        valid_artifact_fids         = self.validatedArtifacts(all_mentioned_artifact_fids)
        for mc in missing_changesets:
            valid_artifacts = valid_artifact_fids[mc.commitId]
            changeset_payload = {
                'SCMRepository'   : scm_repo.ref,
                'Revision'        : mc.commitId,
                'CommitTimestamp' : datetime.utcfromtimestamp(mc.timestamp / 1000).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'Message'         : mc.message,
                'Uri'             : mc.uri,
                'Artifacts'       : valid_artifacts
            }
            try:
                changeset = self.agicen.create('Changeset', changeset_payload)
                self.log.debug("Created Changeset %s" % changeset.ObjectID)
            except RallyRESTAPIError as msg:
                self.log.error('Error detected on attempt to create Changeset %s' % msg)
                raise OperationalError("Could not create Changeset  %s" % msg)
            ac_changesets.append(changeset)

        return ac_changesets

    def parseForArtifacts(self, commit_message):
        prefixes = [prefix for item in utils.get_all_prefixes(self.agicen) for prefix in item.values()]
        fid_pattern = r'((%s)\d+)' % '|'.join(prefixes)
        result = re.findall(fid_pattern, commit_message, re.IGNORECASE)
        return [item[0].upper() for item in result]


    def validatedArtifacts(self, commit_fid):
        # commit_fid is a dict
        # commit_fid = {commitID: [S123,DE123], ...}
        try:
            fids = list(set([fid for fids in commit_fid.values() for fid in fids]))
        except Exception as msg:
            self.log.error("Cannot get a list of formatted ids of artifacts in the commit messages, in validatedArtfacts")
            raise OperationalError(msg)
        query = self.makeOrQuery("FormattedID", fids)
        response = self.agicen.get('Artifact', fetch="FormattedID,ObjectID", query=query, project=None, pagesize=200, start=1)
        found_arts = [art for art in response]
        va = {}
        for ident in commit_fid.keys():
            va[ident] = []
            matches = [found_art for found_art in found_arts if found_art.FormattedID in commit_fid[ident]]
            if matches:
                va[ident] = matches
                # for art in matches:
                #     if art.Project.oid != targeted_project.oid:
                #         self.log.warning('')
        return va

    def makeOrQuery(self,field, values):
        if not values:
            return None

        values = list(values)
        query = '(%s = "%s")' %(field, values[0])
        if len(values) == 1:
            return query
        else:
            values.pop(0)
            for v in values:
                query = '(%s OR (%s = "%s"))' % (query, field, v)
            return query

    def ensureBuildDefinitionExists(self, job_path, project, job_uri):
        """
            use the self.build_def dict keyed by project at first level, job_path at second level
            to determine if the job_path has a BuildDefinition for it.

            Returns a pyral BuildDefinition instance corresponding to the job (and project)
        """
        # front-truncate the job_path if the string length of that is > 256 chars
        if (len(job_path) > 256):
            job_path = job_path[-256:]
        if project in self.build_def and job_path in self.build_def[project]:
            return self.build_def[project][job_path]

        # do we have the BuildDefinition cache populated?  If not, do it now...
        if project not in self.build_def:  # to avoid build definition duplication
            self.log.debug("Detected build definition cache for the project: {} is empty, populating ...".format(project))
            self._fillBuildDefinitionCache(project)

        # OK, the job_path is not in the BuildDefinition cache
        # so look in the BuildDefinition cache to see if the job_path exists for the given project
        if project in self.build_def:
            if job_path in self.build_def[project]:
                return self.build_def[project][job_path]

        target_project_ref = self._project_cache[project]

        bdf_info = {'Workspace' : self.workspace_ref,
                    'Project'   : target_project_ref,
                    'Name'      : job_path,
                    'Uri'       : job_uri #something like {base_url}/job/{job} where base_url comes from other spoke conn
                   }
        try:
            self.log.debug("Creating a BuildDefinition for job '%s' in Project '%s' ..." % (job_path, project))
            build_defn = self.agicen.create('BuildDefinition', bdf_info, workspace=self.workspace_name, project=project)
        except Exception as msg:
            self.log.error("Unable to create a BuildDefinition for job: '%s';  %s" % (job_path, msg))
            raise OperationalError("Unable to create a BuildDefinition for job: '%s';  %s" % (job_path, msg))

        # Put the freshly minted BuildDefinition in the BuildDefinition cache and return it
        if project not in self.build_def:
            self.build_def[project] = {}

        self.build_def[project][job_path] = build_defn
        return build_defn


    def preCreate(self, int_work_item):
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
        """

        int_work_item['Workspace']       = self.workspace_ref 
        int_work_item['BuildDefinition'] = int_work_item['BuildDefinition'].ref

        if int_work_item.get('Changesets', False):
            collection_payload = [{'_ref': "changeset/%s" % changeset.oid} for changeset in int_work_item['Changesets']]
            int_work_item['Changesets']= collection_payload

        return int_work_item


    def _createInternal(self, int_work_item):

        # snag the base Uri from the int_work_item['Uri'] burning off any ending '/' char
        base_uri = int_work_item['Uri']
        base_uri = base_uri[:-1] if base_uri and base_uri.endswith('/') else base_uri

        try:
            build = self.agicen.create('Build', int_work_item)
            self.log.debug("  Created Build: %-90.90s #%5s  %-8.8s %s" % (build.BuildDefinition.Name, build.Number, build.Status, build.Start))
        except Exception as msg:
            print("AgileCentralConnection._createInternal detected an Exception, {0}".format(sys.exc_info()[1]))
            excp_type, excp_value, tb = sys.exc_info()
            mo = re.search(r"'(?P<ex_name>.+)'", str(excp_type))
            if mo:
                excp_type = mo.group('ex_name').replace('exceptions.', '')
                msg = '%s: %s\n' % (excp_type, str(excp_value))
            raise OperationalError(msg)

        return build


    def buildExists(self, build_defn, number):
        """
            Issue a query against Build to obtain the Build identified by build_defn.ObjectID and number.
            Return a boolean indication of whether such an item exists.
        """
        criteria = ['BuildDefinition.ObjectID = %s' % build_defn.ObjectID, 'Number = %s' % number]
        response = self.agicen.get('Build', fetch="CreationDate,Number,Name,BuildDefinition,Project", query=criteria,
                                            workspace=self.workspace_name, project=None)

        if response.resultCount:
            return response.next()
        return None


    # def populateChangesetsCollectionOnBuild(self, build, changesets):
    #     csrefs = [{ "_ref" : "changeset/%s" % cs.oid} for cs in changesets]
    #     cs_coll_ref = build.Changesets
    #     #self.agicen.addCollection(cs_coll_ref, csrefs)

    def matchToChangesets(self, vcs_commits):
        valid_changesets = []
        for commit in vcs_commits:
            query = ('Revision = "%s"' % commit)
            response = self.agicen.get("Changeset", fetch="ObjectID", query=query, workspace=self.workspace_name, project=None)
            if response.resultCount > 0:
                changeset = response.next()
                valid_changesets.append(changeset)
        return valid_changesets
