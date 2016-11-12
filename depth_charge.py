
import sys
import time
import urllib
import re
import requests
quote = urllib.parse.quote

sys.path.insert(0, 'bldeif')

from bldeif.utils.klog import ActivityLogger
from bldeif.utils.eif_exception import ConfigurationError

from pprint import pprint

ACTION_WORD_PATTERN    = re.compile(r'[A-Z][a-z]+')
ARTIFACT_IDENT_PATTERN = re.compile(r'(?P<art_prefix>[A-Z]{1,4})(?P<art_num>\d+)')
VALID_ARTIFACT_ABBREV  = None # set later after config values for artifact prefixes are known

JENKINS_URL      = "{prefix}/api/json"
ALL_JOBS_URL     = "{prefix}/api/json?tree=jobs[displayName,name,url,jobs[displayName,name,url]]"
VIEW_JOBS_URL    = "{prefix}/view/{view}/api/json?depth=0&tree=jobs[name]"
VIEW_FOLDERS_URL = "{prefix}/view/{view}/api/json?tree=jobs[displayName,name,url,jobs[displayName,name,url]]"
#BUILD_ATTRS      = "number,id,fullDisplayName,timestamp,duration,result,url,changeSet[kind,items[*[*]]]"
BUILD_ATTRS      = "number,id,fullDisplayName,timestamp,duration,result,url,changeSet[kind,items[id,timestamp,date,msg]]"
JOB_BUILDS_URL   = "{prefix}/view/{view}/job/{job}/api/json?tree=builds[%s]" % BUILD_ATTRS
FOLDER_JOBS_URL  = "{prefix}/job/{folder_name}/api/json?tree=jobs[displayName,name,url]"
#FOLDER_JOB_BUILD_ATTRS = "number,id,description,timestamp,duration,result,changeSet[kind,items[*[*]]]"
FOLDER_JOB_BUILD_ATTRS = "number,id,description,timestamp,duration,result,url,changeSet[kind,items[id,timestamp,date,msg]]"
FOLDER_JOB_BUILDS_MINIMAL_ATTRS = "number,id,timestamp,result"
FOLDER_JOB_BUILDS_URL = "{prefix}/job/{folder_name}/jobs/{job_name}/api/json?tree=builds[%s]" % FOLDER_JOB_BUILD_ATTRS
FOLDER_JOB_BUILD_URL  = "{prefix}/job/{folder_name}/jobs/{job_name}/{number}/api/json"
#VALID_JENKINS_CONTAINERS = ['Jobs', 'Views', 'Folders']

############################################################################################


class DepthCharge:
    def __init__(self, server, port, user, password, logger):
        self.protocol         = 'http'
        self.server           = server
        self.port             = port
        self.auth             = True
        self.user             = user
        self.password         = password
        self.base_url = "http://{0}:{1}".format(self.server, self.port)
        self.creds = (self.user, self.password)
        self.log   = logger
        self.maxDepth = 5

        self.all_views        = []
        self.all_jobs         = []
        self.view_folders     = {}
        self.job_folders      = {}

    def connect(self):
        urlovals = {'prefix': self.base_url}

        fields = self.makeFieldsString(self.maxDepth)
        pprint(fields)
        #fields = '_class,name,displayName,jobs[_class,name,displayName,jobs[_class,name,displayName,jobs]]'
        jenkins_url = "%s?depth=%d&tree=%s" % (JENKINS_URL.format(**urlovals), self.maxDepth, fields)
        response = requests.get(jenkins_url, auth=self.creds)
        status = response.status_code
        jenkins_info = response.json()

        print("Jenkins DepthCharge response keys:")
        #interesting jenkins_info keys: 'jobs', 'views', 'primaryView')
        pprint(jenkins_info)

        self.all_views = [str(view['name']) for view in jenkins_info['views']]
        #for view in self.all_views:
         #   self.log.debug("View: {0}".format(view))
        self.all_jobs  = [str( job['name']) for job  in jenkins_info['jobs']]
        #for job in self.all_jobs:
        #    self.log.debug("Job: {0}".format(job))
        self.primary_view = jenkins_info['primaryView']['name']

        self.view_folders['All'] = self.getViewFolders('All')
        self.log.debug("PrimaryView: {0}".format(self.primary_view))

        return True

    def makeFieldsString(self, depth):
        basic_fields = '_class,name,displayName,views[name,jobs[name]],jobs'
        detailed_fetch = basic_fields[:]
        if depth <= 1:
            return basic_fields

        for i in range(1, depth):
            detailed_fetch = "%s[%s]" % (basic_fields , detailed_fetch)
        return detailed_fetch

    def getViewFolders(self, view):
        if view not in self.all_views:
            raise ConfigurationError("specified view '%s' not present in list of existing Jenkins views" % view['View'])

        urlovals = {'prefix' : self.base_url, 'view' : quote(view)}
        view_job_folders_url = VIEW_FOLDERS_URL.format(**urlovals)
        #self.log.debug("view: %s  req_url: %s" % (view, view_job_folders_url))
        response = requests.get(view_job_folders_url, auth=self.creds)
        jenk_stuff = response.json()
        jenk_jobs = [job for job in jenk_stuff.get('jobs', None)]
        view_folders = {}
        #self.log.debug('Folders:')
        for job in jenk_jobs:
            if not 'jobs' in job:
                continue
            jenkins_folder = JenkinsJobsFolder(job['displayName'], job['name'], job['url'], job['jobs'])
            view_folders[jenkins_folder.displayName] = jenkins_folder
            #self.log.debug(jenkins_folder)
        return view_folders


    def descend(self):
        pass

############################################################################################

class JenkinsJobsFolder(object):
    def __init__(self, displayName, name, url, jobs):
        self.displayName = displayName
        self.name = name
        self.url = url
        self.jobs = jobs

    def __str__(self):
        sub_jobs = len(self.jobs)
        return "displayName: %-24.24s   name: %-24.24s   sub-jobs: %3d   url: %s " % \
               (self.displayName, self.name, sub_jobs, self.url)

    def info(self):
        return str(self)


############################################################################################

logger  = ActivityLogger("jenk.log", policy='calls', limit=1000)
jenk = DepthCharge("tiema03-u183073.ca.com", 8080, 'jenkins', 'rallydev', logger)

started = time.time()
jenk.connect()


