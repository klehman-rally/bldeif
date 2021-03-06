import sys, os
import datetime
import urllib
import socket
import re
import time

import requests
from collections import Counter

from bldeif.connection import BLDConnection
from bldeif.utils.eif_exception import ConfigurationError, OperationalError

quote = urllib.parse.quote

############################################################################################

__version__ = "1.0.0"

ACTION_WORD_PATTERN = re.compile(r'[A-Z][a-z]+')
ARTIFACT_IDENT_PATTERN = re.compile(r'(?P<art_prefix>[A-Z]{1,4})(?P<art_num>\d+)')
VALID_ARTIFACT_ABBREV = None  # set later after config values for artifact prefixes are known

BUILD_ATTRS = "number,id,fullDisplayName,timestamp,duration,result,url,actions[remoteUrls],changeSet[*[*[*]]]"
FOLDER_JOB_BUILD_ATTRS = "number,id,description,timestamp,duration,result,url,actions[remoteUrls],changeSet[*[*[*]]]"
FOLDER_JOB_BUILDS_MINIMAL_ATTRS = "number,id,timestamp,result"

JENKINS_URL           = "{prefix}/api/json"
ALL_JOBS_URL          = "{prefix}/api/json?tree=jobs[displayName,name,url,jobs[displayName,name,url]]"
#VIEW_JOBS_URL         = "{prefix}/view/{view}/api/json?depth=0&tree=jobs[name]"
#VIEW_JOBS_ENDPOINT    = "/api/json?depth=0&tree=jobs[name]"
VIEW_FOLDERS_URL      = "{prefix}/view/{view}/api/json?tree=jobs[displayName,name,url,jobs[displayName,name,url]]"
JOB_BUILDS_URL        = "{prefix}/view/{view}/job/{job}/api/json?tree=builds[%s]" % BUILD_ATTRS
FOLDER_JOBS_URL       = "{prefix}/job/{folder_name}/api/json?tree=jobs[displayName,name,url]"
FOLDER_JOB_BUILDS_URL = "{prefix}/job/{folder_name}/jobs/{job_name}/api/json?tree=builds[%s]" % FOLDER_JOB_BUILD_ATTRS
FOLDER_JOB_BUILD_URL  = "{prefix}/job/{folder_name}/jobs/{job_name}/{number}/api/json"


############################################################################################

class JenkinsConnection(BLDConnection):
    def __init__(self, config, logger):
        super().__init__(logger)
        self.jenkins = None
        self.internalizeConfig(config)
        self.backend_version = ""
        self.username_required = False
        self.password_required = False

    def name(self):
        return "Jenkins"

    def version(self):
        global __version__
        return __version__

    def getBackendVersion(self):
        """
            Conform to Connection subclass protocol and provide the version of the system
            we are "connecting" to.
        """
        return self.backend_version

    def internalizeConfig(self, config):
        super().internalizeConfig(config)
        self.protocol   = config.get('Protocol', 'http')
        self.server     = config.get('Server', socket.gethostname())
        self.port       = config.get('Port', 8080)
        self.prefix     = config.get("Prefix", '')
        #self.user       = config.get("Username", '')
        #self.password   = config.get("Password", '')
        self.api_token  = config.get("API_Token", '')
        self.debug      = config.get("Debug", False)
        self.max_items  = config.get("MaxItems", 1000)
        self.full_folder_path = config.get("FullFolderPath", False)
        self.ac_project = config.get("AgileCentral_DefaultBuildProject", None)
        self.views      = config.get("Views", [])
        self.jobs       = config.get("Jobs", [])
        self.folders    = config.get("Folders", [])
        self.base_url   = "{0}://{1}:{2}".format(self.protocol, self.server, self.port)
        self.all_views  = []
        self.all_jobs   = []
        self.view_folders = {}
        self.maxDepth   = config.get('MaxDepth', 1) + 2
        if self.username:
            if self.api_token:
                cred = self.api_token
            else:
                cred = self.password
            self.creds = (self.username, cred)
        else:
            self.creds = None

        #https_proxy = os.environ.get('https_proxy', None) or os.environ.get('HTTPS_PROXY', None)
        #if https_proxy not in ["", None]:
        #    self.log.info("Proxy for Jenkins connection:  %s" % https_proxy)

        self.http_proxy = {}
        if self.proxy_server:
            proxy  = "%s://%s:%s" % (self.proxy_protocol, self.proxy_server, self.proxy_port)
            if self.proxy_username and self.proxy_password:
                proxy  = "%s://%s:%s@%s:%s" % (self.proxy_protocol, self.proxy_username, self.proxy_password, self.proxy_server, self.proxy_port)
            self.http_proxy = {self.protocol : proxy}
            self.log.info("Proxy for Jenkins connection:  %s" % proxy)

        valid_config_items = ['Server', 'Protocol', 'Prefix', 'Port', 'API_Token', 'MaxItems',
                              'Username', 'User', 'Password',
                              'ProxyProtocol', 'ProxyServer', 'ProxyPort', 'ProxyUser', 'ProxyUsername',
                              'ProxyPassword',
                              'Debug', 'Lookback',
                              'AgileCentral_DefaultBuildProject',
                              'MaxDepth', 'FullFolderPath',
                              'Views', 'Jobs', 'Folders',
                             ]

        invalid_config_items = [item for item in config.keys() if item not in valid_config_items]
        if invalid_config_items:
            problem = "Jenkins section of the config contained these invalid entries: %s" % ", ".join(
                invalid_config_items)
            raise ConfigurationError(problem)

    def connect(self):
        """
        """
        self.log.info("Connecting to Jenkins")

        self.backend_version = self._getJenkinsVersion()
        self.log.info("Connected to Jenkins server: %s running at version %s" % (self.server, self.backend_version))
        self.log.info("Url: %s" % self.base_url)
        self.job_class_exists = self._checkJenkinsJobClassProp()
        if not self.job_class_exists:
            msg = "The Jenkins REST API doesn't return a _class property in the response. Update to Jenkins 2.2 or greater to use this connector"
            raise ConfigurationError(msg)
        self.obtainJenkinsInventory()
        return True

    def _getJenkinsVersion(self):
        version = None
        jenkins_url = "%s/manage" % self.base_url
        self.log.debug(jenkins_url)
        try:
            response = requests.get(jenkins_url, auth=self.creds, proxies=self.http_proxy)
        except Exception as msg:
            self.log.error(msg)
        if response.status_code >= 300:
            mo = re.search(r'<title>.*?</title>', response.text)
            msg = mo.group(0) if mo else 'Connection error to Jenkins'
            raise ConfigurationError('%s  status_code: %s' % (msg, response.status_code))

        # self.log.debug(response.headers)
        extract = [value for key, value in response.headers.items() if key.lower() == 'x-jenkins']
        if extract:
            version = extract.pop(0)
        return version

    def _checkJenkinsJobClassProp(self):
        class_exists = False
        jenkins_url = "%s/api/json" %self.base_url
        self.log.debug(jenkins_url)
        response = requests.get(jenkins_url, auth=self.creds, proxies=self.http_proxy)
        extract = [key for key in response.json() if key == '_class']
        if extract:
            class_exists = True
        return class_exists

    def disconnect(self):
        """
            Just reset our jenkins instance variable to None
        """
        self.jenkins = None

    def makeFieldsString(self, depth):
        basic_fields = '_class,name,displayName,views[name,jobs[name]],jobs'
        detailed_fetch = basic_fields[:]
        if depth <= 1:
            return basic_fields

        for i in range(1, depth):
            detailed_fetch = "%s[%s]" % (basic_fields, detailed_fetch)
        return detailed_fetch

    def obtainJenkinsInventory(self):
        """
             Utilize the Jenkins REST API endpoint to obtain all visible/accessible Jenkins Jobs/Views/Folders
        """
        urlovals = {'prefix': self.base_url}
        jenkins_url = JENKINS_URL.format(**urlovals)
        self.log.info("Jenkins initial query url: %s" % jenkins_url)
        urlovals = {'prefix': self.base_url}

        fields = self.makeFieldsString(self.maxDepth)
        jenkins_url = "%s?depth=%d&tree=%s" % (JENKINS_URL.format(**urlovals), self.maxDepth, fields)
        response = requests.get(jenkins_url, auth=self.creds, proxies=self.http_proxy)
        status = response.status_code
        jenkins_info = response.json()

        job_bucket = []
        folder_bucket = {}
        view_bucket = {}
        base_views  = [view for view in jenkins_info['views'] if not view['_class'].endswith('AllView')]
        for view in base_views:
            view_bucket['/%s' % view['name']] = JenkinsView(view, base_url=self.base_url)
        job_bucket, folder_bucket, view_bucket = self.fill_buckets(jenkins_info['jobs'], self.base_url, job_bucket, folder_bucket, view_bucket)
        self.inventory = JenkinsInventory(self.base_url, job_bucket, folder_bucket, view_bucket)

    def fill_buckets(self, jobs, container, job_bucket, folder_bucket, view_bucket, level=1):

        non_folders = [job for job in jobs if 'name' in job.keys() and not job['_class'].endswith('.Folder')]
        folders     = [job for job in jobs if 'name' in job.keys() and     job['_class'].endswith('.Folder')]

        for job in non_folders:
            job_bucket.append(JenkinsJob(job, container=container, base_url=self.base_url))
        for folder in folders:
            name = folder.get('name', 'NO-NAME-FOLDER')
            fcon = self.get_folder_full_path(container, name)
            folder_bucket[fcon] = JenkinsJobsFolder(folder, container, folder_url="%s/job/%s" % (container, name))
            folder_views = [view for view in folder['views'] if not view['_class'].endswith('AllView')]
            for folder_view in folder_views:
                full_view_path = self.get_view_full_path(container, name, folder_view['name'])
                view_bucket[full_view_path] = JenkinsView(folder_view, '%s/job/%s' % (container, name), base_url="%s/job/%s" % (container, name))
            self.fill_buckets(folder['jobs'], '%s/job/%s' % (container, name), job_bucket, folder_bucket, view_bucket, level + 1)

        return job_bucket, folder_bucket, view_bucket

    def get_view_full_path(self, container, folder_name, view_name):
        """
            Strip off the self.base_url prefix from container,
            then split by 'job/' and reconstruct the result, append / folder_name / view_name
        """
        container = re.sub(r'%s/?' % self.base_url, '', container)
        elements = [el for el in re.split('/?job/?', container) if el] #removed leading space
        path = "/".join(elements)
        if not container:
            fqp = "/%s/%s" % (folder_name, view_name)
        else:
            fqp = "/%s/%s/%s" % (path, folder_name, view_name)

        return fqp


    def get_folder_full_path(self, container, folder_name):
        """
            Strip off the self.base_url prefix from container,
            then split by 'job/' and reconstruct the result, append / folder_path / folder_name
        """
        container = re.sub(r'%s/?' % self.base_url, '', container)
        elements = [el for el in re.split('/?job/?', container) if el] #removed leading space
        path = "/".join(elements)
        if not container:
            fqp = "/%s" % (folder_name)
        else:
            fqp = "/%s/%s" % (path, folder_name)

        #print("gfp container: %-20.20s  folder_name: %-20.20s  path: %-20.20s result --> %s" % (container, folder_name, path, fqp))

        return fqp


    def showQualifiedViewJobs(self):
        """
            Consult self.views and get all the jobs associated with those views
        """
        print("\n  Configured Views and Qualified Jobs \n  ---------------\n")
        views = sorted(self.inventory.views.keys(), key=lambda s: s.lower())

        qualified_views = [view for view in views if view in self.views]
        for vk in qualified_views:
            print('    %s' % vk)
            jenkins_view = self.inventory.views[vk]
            for job in jenkins_view.jobs:
                # look in self.views[vk] to get the include and exclude regex patts
                # disqualify the job if it doesn't match an explicit include pattern or it matches an exclude pattern
                print('        %s' % job.name)
            print("")

    def showViewJobs(self, target='All'):
        """
           view/path/foo
               job 1
               job 2
        """
        print("\n  Views and Jobs \n  ---------------\n")
        views = sorted(self.inventory.views.keys(), key=lambda s: s.lower())
        if target != 'All':
            views = [v for v in views if v == target]
        for vk in views:
            print('    %s' % vk)
            jenkins_view = self.inventory.views[vk]
            for job in jenkins_view.jobs:
                print('        %s' % job.name)
            print("")

    def showFolderJobs(self, target='All'):
        """
            folder/path/foo
               job 1
               job 2
        """
        print("\n  Folders and Jobs \n  ---------------\n")
        folders = sorted(self.inventory.folders.keys(), key=lambda s: s.lower())
        if target != 'All':
            folders = [f for f in folders if f == target]
        for fn in folders:
            print('    %s' % fn)


    def validate(self):
        """
            Make sure any requisite conditions are satisfied.
            Are credentials needed and supplied?
            Are the Jenkins Job/Views/Folders targets accurately identified?
        """
        satisfactory = True
        if not self.username:
            self.username = 'username'
            self.log.info("Literal 'username' is used")
        else:
            self.log.debug(
                '%s - user entry "%s" detected in config file' % (self.__class__.__name__, self.username))

        # if self.password_required:
        if not self.password:
            if not self.api_token:
                self.password = 'password'
                self.log.info("Literal 'password' is used")
            else:
                self.password = self.api_token
        else:
            self.log.debug('%s - password entry detected in config file' % self.__class__.__name__)

        if not self.ac_project:
            self.log.error("No AgileCentral_DefaultBuildProject value was provided in your configuration in the Jenkins section")
            return False

        if not (self.views or self.folders or self.jobs):
            self.log.error("No Jobs, Views, or job Folders were provided in your configuration")
            return False

        if self.duplicate_items_found():
            return False

        if self.full_folder_path:
            vetted = self.fullyPathedConfigItemsVetted()
        else:
            vetted =  self.nonFullyPathedConfigItemsVetted()

        if not vetted:
            self.log.error("Some Jobs, Views, or Job Folders were invalid in your configuration")
            satisfactory = False

        return satisfactory

    def duplicate_items_found(self):
        job_names    = [j['Job'] for j in self.jobs]
        dupe_jobs    = [name for name, count in Counter(job_names).items() if count > 1]

        folder_names = [f['Folder'] for f in self.folders]
        dupe_folders = [name for name, count in Counter(folder_names).items() if count > 1]

        view_names   = [v['View'] for v in self.views]
        dupe_views   = [name for name, count in Counter(view_names).items() if count > 1]

        has_dupes = False

        if dupe_jobs:
            self.log.error("Duplicated job names: %s" % ", ".join(dupe_jobs))
            has_dupes = True

        if dupe_folders:
            self.log.error("Duplicated folder names: %s" % ", ".join(dupe_folders))
            has_dupes = True

        if dupe_views:
            self.log.error("Duplicated view names: %s" % ", ".join(dupe_views))
            has_dupes = True

        if has_dupes:
            self.log.error('You should use the FullFolderPath : True config specification to be able to process duplicately named elements.')

        return has_dupes


    def fullyPathedConfigItemsVetted(self):
        """
            Mash the self.jobs, self.views and self.folders
            against what is in our self.inventory.  If there are items/sub-items in
            the config structure that aren't in the self.inventory, call a foul and get out.
            Otherwise declare a Trump-like victory!

            The config items for folder and view have to be fully qualified.
        """
        self.vetted_jobs        = []
        self.vetted_view_jobs   = {}
        self.vetted_folder_jobs = {}

        if self.jobs:
            job_names = [job.name.replace('::','') for job in self.inventory.jobs]
            config_job_names = [job['Job'] for job in self.jobs]
            diff = set(config_job_names) - set(job_names)
            if diff:
                villains = ', '.join(["'%s'" % d for d in diff])
                self.log.error("these jobs: %s  were not present in the Jenkins inventory of Jobs" % villains)
                return False

            self.vetted_jobs = [job for job in self.inventory.jobs if job.name in config_job_names]

        if self.views:
            #view_names = [view_name.rsplit('/', 1)[-1] for view_name in self.inventory.views.keys()]
            view_map = self.inventory.getFullyQualifiedViewMapping()

            config_view_names = [view['View'] for view in self.views]
            # other means of detecting things in config_view_names that are not in view_names
            diff = [name for name in config_view_names if name not in view_map.keys()]
            if diff:
                villains = ', '.join(["'%s'" % d for d in diff])
                self.log.error("these views: %s  were not present in the Jenkins inventory of Views" % villains)
                max_depth_comment = "Check if MaxDepth value %s in config is sufficient to reach these views" % self.config['MaxDepth']
                self.log.error(max_depth_comment)
                if self.config['FullFolderPath']:
                    fqp_comment = "Check if your View entries use the fully qualified path syntax"
                    self.log.error(fqp_comment)
                return False

            for view in self.views:
                view_name = view['View']
                ac_project  = view.get('AgileCentral_Project', self.ac_project)
                key = '%s::%s' % (view_name, ac_project)
                view_jobs = self.getMatchingFullyQualifiedViewPathJobs(view)
                self.vetted_view_jobs[key] = view_jobs

        if self.folders:
            #folder_names = [folder_name.rsplit('/', 1)[-1] for folder_name in self.inventory.folders.keys()]
            folder_map = self.inventory.getFullyQualifiedFolderMapping()

            config_folder_names = [folder['Folder'] for folder in self.folders]
            # other means of detecting things in config_folder_names that are not in folder_names
            diff = [name for name in config_folder_names if name not in folder_map.keys()]
            if diff:
                villains = ', '.join(["'%s'" % d for d in diff])
                self.log.error("these folders: %s  were not present in the Jenkins inventory of Folders" % villains)
                max_depth_comment = "Check if MaxDepth value %s in config is sufficient to reach these folders" % self.config['MaxDepth']
                self.log.error(max_depth_comment)
                if self.config['FullFolderPath']:
                    fqp_comment = "Check if your Folder entries use the fully qualified path syntax"
                    self.log.error(fqp_comment)
                return False

            for folder in self.folders:
                folder_name = folder['Folder']
                ac_project  = folder.get('AgileCentral_Project', self.ac_project)
                key = '%s::%s' % (folder_name, ac_project)
                folder_jobs = self.getMatchingFullyQualifiedFolderPathJobs(folder)
                self.vetted_folder_jobs[key] = folder_jobs

        return True


    def getMatchingFullyQualifiedFolderPathJobs(self, folder):
        folder_path = folder['Folder']
        jenkins_folder = self.inventory.getFolderByPath(folder_path)
        all_folder_jobs = jenkins_folder.jobs

        included_jobs = all_folder_jobs[:]
        if 'include' in folder:
            inclusions = folder.get('include', '*')
            inclusions = inclusions.replace('*', '\.*')
            include_patt = "(%s)" % '|'.join(re.split(', ?', inclusions))
            included_jobs = [job for job in all_folder_jobs if re.search(include_patt, job.name) != None]

        excluded_jobs = []
        if 'exclude' in folder and folder['exclude']:
            exclusions = folder.get('exclude')
            exclusions = exclusions.replace('*', '\.*')
            exclude_patt = "(%s)" % '|'.join(re.split(', ?', exclusions))
            excluded_jobs = [job for job in all_folder_jobs if re.search(exclude_patt, job.name) != None]

        qualifying_jobs = list(set(included_jobs) - set(excluded_jobs))
        return qualifying_jobs

    def getMatchingFullyQualifiedViewPathJobs(self, view):
        view_path = view['View']
        jenkins_view = self.inventory.getViewByPath(view_path)
        all_view_jobs = jenkins_view.jobs

        included_jobs = all_view_jobs[:]
        if 'include' in view:
            inclusions = view.get('include', '*')
            inclusions = inclusions.replace('*', '\.*')
            include_patt = "(%s)" % '|'.join(re.split(', ?', inclusions))
            included_jobs = [job for job in all_view_jobs if re.search(include_patt, job.name) != None]

        excluded_jobs = []
        if 'exclude' in view and view['exclude']:
            exclusions = view.get('exclude')
            exclusions = exclusions.replace('*', '\.*')
            exclude_patt = "(%s)" % '|'.join(re.split(', ?', exclusions))
            excluded_jobs = [job for job in all_view_jobs if re.search(exclude_patt, job.name) != None]

        qualifying_jobs = list(set(included_jobs) - set(excluded_jobs))
        return qualifying_jobs


    def nonFullyPathedConfigItemsVetted(self):
        """
            Mash the self.jobs, self.views and self.folders
            against what is in our self.inventory.  If there are items/sub-items in
            the config structure that aren't in the self.inventory, call a foul and get out.
            Otherwise declare a Trump-like victory!
        """
        self.vetted_jobs        = []
        self.vetted_view_jobs   = {}
        self.vetted_folder_jobs = {}

        if self.jobs:
            job_names = [job.name.replace('::','') for job in self.inventory.jobs]
            config_job_names = [job['Job'] for job in self.jobs]
            diff = set(config_job_names) - set(job_names)
            if diff:
                villains = ', '.join(["'%s'" % d for d in diff])
                self.log.error("these jobs: %s  were not present in the Jenkins inventory of Jobs" % villains)
                return False

            self.vetted_jobs = [job for job in self.inventory.jobs if job.name in config_job_names]

        if self.views:
            view_names = [view_name.rsplit('/', 1)[-1] for view_name in self.inventory.views.keys()]
            config_view_names = [view['View'] for view in self.views]
            diff = [name for name in  config_view_names if name not in view_names]
            if diff:
                villains = ', '.join(["'%s'" % d for d in diff])
                self.log.error("these views: %s  were not present in the Jenkins inventory of Views" % villains)
                return False

            for view in self.views:
                view_name  = view['View']
                ac_project = view.get('AgileCentral_Project', self.ac_project)
                key = '%s::%s' % (view_name, ac_project)
                view_jobs = self.getQualifyingViewJobs(view)
                self.vetted_view_jobs[key] = view_jobs

        if self.folders:
            folder_names = [folder_name.rsplit('/', 1)[-1] for folder_name in self.inventory.folders.keys()]
            config_folder_names = [folder['Folder'] for folder in self.folders]
            # other means of detecting things in config_folder_names that are not in folder_names
            diff = [name for name in config_folder_names if name not in folder_names]
            if diff:
                villains = ', '.join(["'%s'" % d for d in diff])
                max_depth_comment = "Check if MaxDepth value %s in config is sufficient to reach these folders" % self.config['MaxDepth']
                self.log.error("these folders: %s  were not present in the Jenkins inventory of Folders" % villains)
                self.log.error(max_depth_comment)
                return False

            for folder in self.folders:
                folder_name = folder['Folder']
                ac_project  = folder.get('AgileCentral_Project', self.ac_project)
                key = '%s::%s' % (folder_name, ac_project)
                folder_jobs = self.getQualifyingFolderJobs(folder)
                self.vetted_folder_jobs[key] = folder_jobs

        return True


    def dumpTargets(self):
        for job in self.jobs:
            self.log.debug('Job: %s' % job)
        for view in self.views:
            self.log.debug('View: %s' % view)
        for folder in self.folders:
            self.log.debug('Folder: %s' % folder)


    def getQualifyingFolderJobs(self, folder):
        jenkins_folder = self.inventory.getFolder(folder['Folder'])
        all_folder_jobs = jenkins_folder.jobs

        included_jobs   = all_folder_jobs[:]
        if 'include' in folder:
            inclusions = folder.get('include', '*')
            inclusions = inclusions.replace('*', '\.*')
            include_patt = "(%s)" % '|'.join(re.split(', ?', inclusions))
            included_jobs = [job for job in all_folder_jobs if re.search(include_patt, job.name) != None]

        excluded_jobs = []
        if 'exclude' in folder and folder['exclude']:
            exclusions = folder.get('exclude')
            exclusions = exclusions.replace('*', '\.*')
            exclude_patt = "(%s)" % '|'.join(re.split(', ?', exclusions))
            excluded_jobs = [job for job in all_folder_jobs if re.search(exclude_patt, job.name) != None]

        qualifying_jobs = list(set(included_jobs) - set(excluded_jobs))
        return qualifying_jobs


    def getQualifyingViewJobs(self, view):

        jenkins_view = self.inventory.getView(view['View'])
        all_view_jobs = jenkins_view.jobs

        include_patt = view.get('include', '*')
        include_patt = include_patt.replace('*', '\.*')
        included_jobs = [job for job in all_view_jobs if re.search(include_patt, job.name) != None]
        excluded_jobs = []
        if 'exclude' in view:
            exclusions = re.split(',\s*', view['exclude'])
            for job in included_jobs:
                for exclusion in exclusions:
                    exclusion = exclusion.replace('*', '\.*')
                    if re.search(exclusion, job.name):
                        excluded_jobs.append(job)
                        break

        qualifying_jobs = list(set(included_jobs) - set(excluded_jobs))
        return qualifying_jobs

    def showQualifiedJobs(self):
        self.log.debug('Configured top level Jobs')
        for job in self.jobs:
            #jenkins_job = self.inventory.getJob(job['Job'])
            self.log.debug("    %s" % job['Job']) # used to be jenkins_job.name

        self.log.debug('Configured Views and Jobs')
        for view_name, jobs in self.vetted_view_jobs.items():
            self.log.debug("    View: %s" % view_name)
            for job in jobs:
                self.log.debug("        %s" % job.name)
        self.log.debug('Configured Folders and Jobs')
        for folder_name, jobs in self.vetted_folder_jobs.items():
            self.log.debug("    Folder: %s" % folder_name)
            for job in jobs:
                self.log.debug("        %s" % job.name)


    def getRecentBuilds(self, ref_time):
        """
            Obtain all Builds created in Jenkins at or after the ref_time parameter
            which is a struct_time object of:
               (tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst)

            Construct a dict keyed by Jenkins-View-Name::AgileCentral_ProjectName
            with a list of JenkinsBuild items for each key
        """
        zulu_ref_time = time.localtime(time.mktime(ref_time))  # ref_time is already in UTC, so don't convert again (hence use of time.localtime()
        ref_time_readable = time.strftime("%Y-%m-%d %H:%M:%S Z", zulu_ref_time)
        pending_operation = "Detecting recently added Jenkins Builds (added on or after %s)"
        self.log.info(pending_operation % ref_time_readable)

        builds = {}
        recent_builds_count = 0

        for folder_conf in self.folders:
            folder_name = folder_conf['Folder']
            ac_project  = folder_conf.get('AgileCentral_Project', self.ac_project)
            key = '%s::%s' % (folder_name, ac_project)
            builds[key] = {}
            for job in self.vetted_folder_jobs[key]:
                builds[key][job] = self.getFolderJobBuildHistory(folder_name, job, zulu_ref_time)
                self.log.debug("retrieved %d builds for Job %s that occured after %s" % (len(builds[key][job]), job.fully_qualified_path(), ref_time_readable))
                recent_builds_count += len(builds[key][job])

        for view_conf in self.views:
            view_name  = view_conf['View']
            ac_project = view_conf.get('AgileCentral_Project', self.ac_project)
            key = '%s::%s' % (view_name, ac_project)
            builds[key] = {}
            for job in self.vetted_view_jobs[key]:
                builds[key][job] = self.getBuildHistory(view_name, job, zulu_ref_time)
                self.log.debug("retrieved %d builds for View Job %s that occured after %s" % (len(builds[key][job]), job.fully_qualified_path(), ref_time_readable))
                recent_builds_count += len(builds[key][job])

        for job in self.jobs:
            jenkins_job = self.inventory.getJob(job['Job'])
            ac_project = job.get('AgileCentral_Project', self.ac_project)
            key = 'All::%s' % ac_project
            if key not in builds:
                builds[key] = {}
            builds[key][jenkins_job] = self.getBuildHistory('All', jenkins_job, zulu_ref_time)
            self.log.debug("retrieved %d builds for Folder Job %s that occured after %s" % (len(builds[key][jenkins_job]), jenkins_job.fully_qualified_path(), ref_time_readable))
            recent_builds_count += len(builds[key][jenkins_job])

        log_msg = "recently added Jenkins Builds detected: %s"
        self.log.info(log_msg % recent_builds_count)

        if self.debug:
            jbf = open('jenkins.blds.hist', 'w+')
            jbf.write((log_msg % recent_builds_count) + "\n")
            jbf.close()

        return builds

    def getBuildHistory(self, view, job, ref_time):
        JOB_BUILDS_ENDPOINT = "/api/json?tree=builds[%s]" % BUILD_ATTRS
        urlovals = {'prefix': self.base_url, 'view': quote(view), 'job': quote(job.name)}
        job_builds_url = job.url + (JOB_BUILDS_ENDPOINT.format(**urlovals))
        if job._type == 'WorkflowJob':
            job_builds_url = job_builds_url.replace('changeSet', 'changeSets')
        self.log.debug("view: %s  job: %s  req_url: %s" % (view, job, job_builds_url))
        raw_builds = requests.get(job_builds_url, auth=self.creds, proxies=self.http_proxy).json()['builds']
        qualifying_builds = self.extractQualifyingBuilds(job.name, None, ref_time, raw_builds)
        return qualifying_builds

    def getFolderJobBuildHistory(self, folder_name, job, ref_time):
        folder_job_builds_url = job.url + ('/api/json?tree=builds[%s]' % FOLDER_JOB_BUILD_ATTRS)
        if job._type == 'WorkflowJob':
            folder_job_builds_url = folder_job_builds_url.replace('changeSet', 'changeSets')
        self.log.debug("folder: %s  job: %s  req_url: %s" % (folder_name, job.name, folder_job_builds_url))
        raw_builds = requests.get(folder_job_builds_url, auth=self.creds, proxies=self.http_proxy).json()['builds']
        qualifying_builds = self.extractQualifyingBuilds(job.name, folder_name, ref_time, raw_builds)
        return qualifying_builds

    def extractQualifyingBuilds(self, job_name, folder_name, ref_time, raw_builds):
        builds = []
        for brec in raw_builds:
            # print(brec)
            build = JenkinsBuild(job_name, brec, job_folder=folder_name)
            if build.id_as_ts < ref_time:  # when true build time is older than ref_time, don't consider this job
                break
            builds.append(build)
        return builds[::-1]


##############################################################################################

class JenkinsInventory:
    def __init__(self, base_url, job_bucket, folder_bucket, view_bucket):
        self.base_url = base_url
        self.jobs     = job_bucket
        self.folders  = folder_bucket
        self.views    = view_bucket

    def getFolder(self, name):
        target = name if name.startswith('/') else '/%s' % name
        folder = next((self.folders[folder] for folder in self.folders.keys() if folder.endswith(target)), None)
        return folder

    def getView(self, view_path):
        view_path = '/%s' % view_path if view_path[0] != '/' else view_path
        target_view = next((self.views[vp] for vp in self.views.keys() if vp.endswith(view_path)), None)
        return target_view

    def getJob(self, job_name):
        first_level_jobs = [job for job in self.jobs if job.name == job_name]
        if first_level_jobs:
            return first_level_jobs[0]

        jobs = []
        for folder_path in self.folders.keys():
           matching_jobs = [job for job in self.folders[folder_path].jobs if job.name == job_name]
           if matching_jobs: jobs.extend(matching_jobs)
        for view_path in self.views.keys():
            matching_jobs = [job for job in self.views[view_path].jobs if job.name == job_name]
            if matching_jobs: jobs.extend(matching_jobs)

        return jobs[0]

    def getFullyQualifiedFolderMapping(self):
        # maps folder's path representation from the config file to the folder's path
        #fm = {" // ".join(re.split(r'\/', key)[1:]) : key for key in self.folders.keys()}
        fm = {}
        for fk in sorted(self.folders.keys()):
            #tfk = fk.replace(self.base_url,'')
            path_components = re.split(r'\/', fk)[1:]
            fqpath = " // ".join(path_components)
            #print(fqpath)
            fm[fqpath] = fk

        return fm

    def getFolderByPath(self, folder_path):
        folder_map = self.getFullyQualifiedFolderMapping()
        if folder_path in folder_map:
            folder = self.folders[folder_map[folder_path]]
            return folder
        return None


    def getFullyQualifiedViewMapping(self):
        # maps view's path representation from the config file to the view's path
        #vm = {" // ".join(re.split(r'\/', key)[1:]) : key for key in self.views.keys()}
        vm = {}
        for vk in sorted(self.views.keys()):
            path_components = re.split(r'\/', vk)[1:]
            fqpath = " // ".join(path_components)
            #print(fqpath)
            vm[fqpath] = vk

        return vm

    def getViewByPath(self, view_path):
        view_map = self.getFullyQualifiedViewMapping()
        if view_path in view_map:
            folder = self.views[view_map[view_path]]
            return folder
        return None


##############################################################################################

class JenkinsJob:
    def __init__(self, info, container='Root', base_url=''):
        self.container = container
        self.name      = info.get('name', 'UNKNOWN-ITEM')
        self._type     = info['_class'].split('.')[-1]
        self.url       = "%s/job/%s" % (container, self.name)
        # job_path is really only for dev purposes of displaying a short, readable job path, e.g. "/frozique::australopithicus"
        self.job_path  = "%s::%s" % (re.sub(r'%s/?' % base_url, '', container), self.name)
        self.job_path  = '/'.join(re.split('/?job/?', self.job_path))

    def fully_qualified_path(self):
        return re.sub('https?://', '', self.url)

    def __str__(self):
        vj = "%s::%s" % (self.container, self.name)
        return "%s  %s" % (vj, self._type)

    def __repr__(self):
        return str(self)

#############################################################################################

class JenkinsView:
    def __init__(self, info, container='/', base_url=''):
        self.name = '/%s' % info['name']
        if container == '/':
            job_container  = "%s/view%s" % (base_url, self.name)
        else:
            job_container = "%s/view%s" % (container, self.name)

        self.url  = job_container
        self.jobs = [JenkinsJob(job, job_container, base_url=base_url) for job in info['jobs'] if not job['_class'].endswith('.Folder')]

    def __str__(self):
        vj = "%s::%s" % (self.container, self.name)
        return "%-80.80s  %s" % (vj, self._type)

    def __repr__(self):
        return str(self)

#############################################################################################

class JenkinsJobsFolder:
    def __init__(self, info, container='/',  folder_url=''):
        self.name      = '/%s' % info['name']
        job_container  = "%s/job%s" % (container, self.name)
        self.url       = job_container
        self.jobs      = [JenkinsJob(job, job_container, base_url=folder_url) for job in info['jobs'] if not job['_class'].endswith('.Folder')]

    def __str__(self):
        sub_jobs = len(self.jobs)
        return "name: %-24.24s   sub-jobs: %3d   url: %s " % \
               (self.name, sub_jobs, self.url)

    def info(self):
        return str(self)

    ###########################################################################################

class JenkinsBuild(object):
    def __init__(self, name, raw, job_folder=None):
        """
        """
        self.name = name
        self.number = int(raw['number'])
        self.result = str(raw['result'])
        self.actions = raw['actions']
        self.result = 'INCOMPLETE' if self.result == 'ABORTED' else self.result
        cs_label = 'changeSet'
        if str(raw['_class']).endswith('.WorkflowRun'):
            cs_label = 'changeSets'

        self.id_str = str(raw['id'])
        self.Id     = self.id_str
        self.timestamp = raw['timestamp']
        self.url    = str(raw['url'])

        if re.search('^\d+$', self.id_str):
            self.id_as_ts = time.gmtime(self.timestamp / 1000)
            self.id_str = str(self.timestamp)
            self.Id = self.id_str
        else:
            self.id_as_ts = time.strptime(self.id_str, '%Y-%m-%d_%H-%M-%S')

        self.started = time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime(self.timestamp / 1000))
        self.duration = raw['duration']
        whole, millis = divmod(self.duration, 1000)
        hours, leftover = divmod(whole, 3600)
        minutes, secs = divmod(leftover, 60)
        if hours:
            duration = "%d:%02d:%02d.%03d" % (hours, minutes, secs, millis)
        else:
            if minutes >= 10:
                duration = "%02d:%02d.%03d" % (minutes, secs, millis)
            else:
                duration = " %d:%02d.%03d" % (minutes, secs, millis)

        self.elapsed = "%12s" % duration

        total = (self.timestamp + self.duration) / 1000
        self.finished = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(total))

        self.vcs        = 'unknown'
        self.revisions  = ''
        self.repository = ''
        self.changeSets = []
        self.extractChangeSetInformation(raw, cs_label)


    def extractChangeSetInformation(self, json, cs_label):
        """
             A FreestyleJob build has changeset info in the json under the 'changeSet' element, but
             WorkflowRun build has the equivalent changeset info under the 'changeSets' element as a list.
             Here we transform the FreestyleJob changeset info into the one element 'changeSets' list so
             that the processing is conistent.
        """
        try:
            if cs_label == 'changeSet':
                json['changeSets'] = [json['changeSet']]
            if len(json[cs_label]) == 0:
                return
            try:
                self.vcs = json['changeSets'][0]['kind']
            except Exception as msg:
                self.log.warning(
                    'JenkinsBuild constructor unable to determine VCS kind, %s, marking vcs type as unknown' % (msg))
                self.log.warning(
                    "We accessed your job's build JSON with this param %s and did not see 'kind' value" % BUILD_ATTRS)
            self.revisions = json['changeSets'][0]['revisions'] if cs_label in json and 'revisions' in json['changeSets'][0] else None
            getRepoName = {'git': self.ripActionsForRepositoryName,
                           'svn': self.ripRevisionsForRepositoryName,
                           None: self.ripNothing
                           }
            self.repository = getRepoName[self.vcs]()
            if self.vcs != 'unknown':
                for ch in json['changeSets']:
                    self.changeSets.extend(self.ripChangeSets(self.vcs, ch['items']))
            csd = {changeset.commitId: changeset for changeset in self.changeSets}
            self.changeSets = [chgs for chgs in csd.values()]
        except Exception as msg:
            self.log.warning('JenkinsBuild constructor unable to process %s information, %s' % (cs_label, msg))


    def ripActionsForRepositoryName(self):
        repo = ''
        repo_info = [self.makeup_scm_repo_name(item['remoteUrls'][0]) for item in self.actions if 'remoteUrls' in item]
        if repo_info:
            repo = repo_info[0]
        return repo

    def ripRevisionsForRepositoryName(self):
        """ for use with Subversion VCS
        """
        if not self.revisions:
            return ''
        repo_info = self.revisions[0]['module']
        repo_name = repo_info.split('/')[-1]
        return repo_name

    def ripNothing(self):
        return ''

    def makeup_scm_repo_name(self, remote_url):
        remote_url = re.sub(r'\/\.git$', '', remote_url)
        max_length = 256
        return remote_url.split('/')[-1][-max_length:]

    def ripChangeSets(self, vcs, changesets):
        tank = [JenkinsChangeset(vcs, cs_info) for cs_info in changesets]
        return tank

    def as_tuple_data(self):
        start_time = datetime.datetime.utcfromtimestamp(self.timestamp / 1000.0).strftime('%Y-%m-%dT%H:%M:%SZ')
        build_data = [('Number', self.number),
                      ('Status', str(self.result)),
                      ('Start', start_time),
                      ('Duration', self.duration / 1000.0),
                      ('Uri', self.url)]
        return build_data

    def __repr__(self):
        name = "name: %s" % self.name
        ident = "id_str: %s" % self.id_str
        number = "number: %s" % self.number
        result = "result: %s" % self.result
        finished = "finished: %s" % self.finished
        duration = "duration: %s" % self.duration
        nothing = ""
        pill = "  ".join([name, ident, number, result, finished, duration, nothing])
        return pill

    def __str__(self):
        elapsed = self.elapsed[:]
        if elapsed.startswith('00:'):
            elapsed = '   ' + elapsed[3:]
        if elapsed.startswith('   00:'):
            elapsed = '      ' + elapsed[6:]
        bstr = "%s Build # %5d   %-10.10s  Started: %s  Finished: %s   Duration: %s  URL: %s" % \
               (self.name, self.number, self.result, self.started, self.finished, elapsed, self.url)
        return bstr


#############################################################################################

class JenkinsChangeset:
    def __init__(self, vcs, commit):
        self.vcs       = vcs
        self.commitId  = commit['commitId']
        self.timestamp = commit['timestamp']
        self.message   = commit['msg']
        self.uri       = commit['paths'][0]['file'] if commit['paths'] else '.'

    def __str__(self):
        changeset = "   VCS %s  Commit ID # %s  Timestamp: %s  Message: %s " % \
                    (self.vcs, self.commitId, self.timestamp, self.message)
        return changeset


class JenkinsChangesetFile:
    def __init__(self, item):
        self.action    = item['editType']
        self.file_path = item['file']
