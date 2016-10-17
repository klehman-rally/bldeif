
import sys, os
import urllib
import socket
import re
import time
import calendar

from subprocess   import Popen, STDOUT, PIPE
from pprint import pprint

import requests
import json

#from connection import BLDConnection
from bldeif.connection import BLDConnection
from bldeif.utils.eif_exception import ConfigurationError, OperationalError

quote = urllib.parse.quote

############################################################################################

__version__ = "0.4.1"

ACTION_WORD_PATTERN    = re.compile(r'[A-Z][a-z]+')
ARTIFACT_IDENT_PATTERN = re.compile(r'(?P<art_prefix>[A-Z]{1,4})(?P<art_num>\d+)')
VALID_ARTIFACT_ABBREV  = None # set later after config values for artifact prefixes are known

JENKINS_URL      = "{prefix}/api/json"
ALL_JOBS_URL     = "{prefix}/api/json?tree=jobs[displayName,name,url,jobs[displayName,name,url]]"
VIEW_JOBS_URL    = "{prefix}/view/{view}/api/json?depth=0&tree=jobs[name]"
VIEW_FOLDERS_URL = "{prefix}/view/{view}/api/json?tree=jobs[displayName,name,url,jobs[displayName,name,url]]"
BUILD_ATTRS      = "number,id,fullDisplayName,timestamp,duration,result,changeSet[kind,items[*[*]]]"
JOB_BUILDS_URL   = "{prefix}/view/{view}/job/{job}/api/json?tree=builds[%s]" % BUILD_ATTRS
FOLDER_JOBS_URL  = "{prefix}/job/{folder_name}/api/json?tree=jobs[displayName,name,url]"
#FOLDER_JOB_BUILD_ATTRS = "number,id,description,timestamp,duration,result,changeSet[kind,items[*[*]]]"
FOLDER_JOB_BUILD_ATTRS = "number,id,description,timestamp,duration,result,changeSet[kind,items[timestamp,commitId,author[*],comment,paths[editType,file]]]"
FOLDER_JOB_BUILDS_MINIMAL_ATTRS = "number,id,timestamp,result"
FOLDER_JOB_BUILDS_URL = "{prefix}/job/{folder_name}/jobs/{job_name}/api/json?tree=builds[%s]" % FOLDER_JOB_BUILD_ATTRS
FOLDER_JOB_BUILD_URL  = "{prefix}/job/{folder_name}/jobs/{job_name}/{number}/api/json"

############################################################################################

class JenkinsConnection(BLDConnection):

    def __init__(self, config, logger):
        super(JenkinsConnection, self).__init__(logger)
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
        super(JenkinsConnection, self).internalizeConfig(config)
        self.protocol         = config.get('Protocol',  'http')
        self.server           = config.get('Server',    socket.gethostname())
        self.port             = config.get('Port',      8080)
        self.prefix           = config.get("Prefix",    '')
        self.auth             = config.get("Auth",      False)
        self.user             = config.get("User",      '')
        self.password         = config.get("Password",  '')
        self.api_token        = config.get("API_Token", '')
        self.debug            = config.get("Debug",     False)
        self.max_items        = config.get("MaxItems",  1000)
        self.ac_workspace     = config.get("AgileCentral_Workspace", None)
        self.ac_project       = config.get("AgileCentral_Project",   None)
        self.views            = config.get("Views",   [])
        self.jobs             = config.get("Jobs",    [])
        self.folders          = config.get("Folders", [])
        self.base_url         = "{0}://{1}:{2}".format(self.protocol, self.server, self.port)
        self.all_views        = []
        self.all_jobs         = []
        self.view_folders     = {}


    def connect(self):
        """
        """
        self.log.info("Connecting to Jenkins")
        self.backend_version = self._getJenkinsVersion()
        self.log.info("Connected to Jenkins server: %s running at version %s" % (self.server, self.backend_version))
        self.log.info("Url: %s" % self.base_url)
        
        urlovals = {'prefix' : self.base_url}
        jenkins_url = JENKINS_URL.format(**urlovals)
        self.log.info("Jenkins initial query url: %s" % jenkins_url)
        response = requests.get(jenkins_url)
        jenkins_info = response.json()

        self.all_views = [str(view['name']) for view in jenkins_info['views']]
        for view in self.all_views:
            self.log.debug("View: {0}".format(view))
        self.all_jobs  = [str( job['name']) for job  in jenkins_info['jobs']]
        for job in self.all_jobs:
            self.log.debug("Job: {0}".format(job))
        self.primary_view = jenkins_info['primaryView']['name']

        self.view_folders['All'] = self.getViewFolders('All')
        self.log.debug("PrimaryView: {0}".format(self.primary_view))

        return True

    def _getJenkinsVersion(self):
        version = None
        jenkins_url = "%s/manage" % self.base_url
        self.log.debug(jenkins_url)
        response = requests.get(jenkins_url)
        self.log.debug(response.headers)
        extract = [value for key, value in response.headers.items() if key.lower() == 'x-jenkins']
        if extract:
            version = extract.pop(0)
        return version

    def disconnect(self):
        """
            Just reset our jenkins instance variable to None
        """
        self.jenkins = None


    def getQualifyingJobs(self, view):

        if view['View'] not in self.all_views:
            raise ConfigurationError("specified view '%s' not present in list of existing Jenkins views" % view['View'])
        
        urlovals = {'prefix' : self.base_url, 'view' : urllib.parse.quote(view['View'])}
        view_jobs_url = VIEW_JOBS_URL.format(**urlovals)
        response = requests.get(view_jobs_url)
        jenk_jobs = response.json()
        jobs = [str(job['name']) for job in jenk_jobs.get('jobs', None)]

        include_patt = view.get('include', '*')
        included_jobs = [job for job in jobs if re.search(include_patt, job) != None]
        excluded_jobs = []
        if 'exclude' in view:
            exclusions = re.split(',\s*', view['exclude'])
            for job in jobs:
                for exclusion in exclusions:
                    if re.search(exclusion, job):
                        excluded_jobs.append(job)
                        break

        #print("\n".join(included_jobs))
        #print("\n")
        #print("\n".join(excluded_jobs))

        qualifying_jobs = list(set(included_jobs) - set(excluded_jobs))
        #print("\n".join(qualifying_jobs))
        #print("\n")
        return qualifying_jobs


    def getViewFolders(self, view):
        if view not in self.all_views:
            raise ConfigurationError("specified view '%s' not present in list of existing Jenkins views" % view['View'])

        urlovals = {'prefix' : self.base_url, 'view' : quote(view)}
        view_job_folders_url = VIEW_FOLDERS_URL.format(**urlovals)
        response = requests.get(view_job_folders_url)
        jenk_stuff = response.json()
        jenk_jobs = [job for job in jenk_stuff.get('jobs', None)]
        view_folders = {}
        self.log.debug('Folders:')
        for job in jenk_jobs:
            if not 'jobs' in job:
                continue
            jenkins_folder = JenkinsJobsFolder(job['displayName'], job['name'], job['url'], job['jobs'])
            view_folders[jenkins_folder.displayName] = jenkins_folder
            self.log.debug(jenkins_folder)
        return view_folders


    def getRecentBuilds(self, ref_time):
        """
            Obtain all Builds created in Jenkins at or after the ref_time parameter
            which is a struct_time object of:
               (tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst)

            Construct a dict keyed by Jenkins-View-Name::AgileCentral_ProjectName
            with a list of JenkinsBuild items for each key
        """
        ref_time_readable = time.strftime("%Y-%m-%d %H:%M:%S Z", ref_time)
        ref_time_iso      = time.strftime("%Y-%m-%dT%H:%M:%SZ",  ref_time)
        #ref_time_merc_iso = ref_time_iso.replace('T', ' ').replace('Z', '')
        pending_operation = "Detecting recently added Jenkins Builds (added on or after %s)"
        self.log.info(pending_operation % ref_time_readable)

        builds = {}
        recent_builds_count = 0

        for folder_conf in self.folders:
           #print "folder_conf: %s" % repr(folder_conf)
            folder_display_name = folder_conf['Folder']
           #print("config item for folder display name: %s --> %s" % (folder_display_name, repr(folder_conf)))
            ac_project = folder_conf.get('AgileCentral_Project', self.ac_project)
           #print "  AgileCentral_Project: %s" % ac_project

            fits = [(dn, f) for dn, f in self.view_folders['All'].items() if str(dn) == folder_display_name]
            if not fits:
                continue
            fdn, job_folder = fits.pop(0)
           #print("\n%-16.16s   %s" % (fdn, job_folder.name))
           #print("\n%s   folder" % (fdn))
            key = '%s::%s' % (fdn, ac_project) 
            builds[key] = {}
            for job in job_folder.jobs:
                job_name = job['displayName']
                job_url  = job['url']
                # TODO: prototype a means of qualifying each job through this folder's inclusion/exclusion config
                if 'exclude' in folder_conf:
                    excluded = False
                    exclusions = re.split(',\s*', folder_conf['exclude'])
                    for exclusion in exclusions:
                        if re.search(exclusion, job_name):
                            excluded = True
                    if excluded:
                       #print("         excluding job: %s" % job_url)
                        continue

               #print "    %s" % job_url
                builds[key][job_name] = self.getFolderJobBuildHistory(job_folder.name, job, ref_time)
                recent_builds_count += len(builds[key][job_name])

        for view in self.views:
            view_name = view['View']
            ac_project = view.get('AgileCentral_Project', 'DefaultProject')
            #print(view_name)
            #print("view info: %s" % repr(view))
            key = '%s::%s' % (view_name, ac_project)
            builds[key] = {}
            view_jobs = self.getQualifyingJobs(view)
            for job_name in view_jobs:
                builds[key][job_name] = self.getBuildHistory(view_name, job_name, ref_time)
                recent_builds_count += len(builds[key][job_name])

        for job in self.jobs:
            job_name = job['Job']
            ac_project = job.get('AgileCentral_Project', 'DefaultProject')
            key = 'All::%s' % ac_project
            if key not in builds:
                builds[key] = {}
            builds[key][job_name] = self.getBuildHistory('All', job_name, ref_time)
            recent_builds_count += len(builds[key][job_name])


        log_msg = "recently added Jenkins Builds detected: %s"
        self.log.info(log_msg % recent_builds_count)

        if self.debug:
            jbf = open('jenkins.blds.hist', 'w+')
            jbf.write((log_msg % recent_builds_count) + "\n")
            jbf.close()

        return builds

    def getBuildHistory(self, view, job, ref_time):
        JOB_BUILDS_URL = "{prefix}/view/{view}/job/{job}/api/json?tree=builds[%s]" % BUILD_ATTRS

        urlovals = {'prefix' : self.base_url, 'view' : quote(view), 'job' : quote(job)}
        job_builds_url = JOB_BUILDS_URL.format(**urlovals)
        response = requests.get(job_builds_url)
        result = response.json()
        raw_builds = result['builds']
        builds = []
        for brec in raw_builds:
            build = JenkinsBuild(job, brec)
            # only take those builds >= ref_time
            if build.id_as_ts < ref_time:
                break
            builds.append(build)
        return builds[::-1]

    def getFolderJobBuildHistory(self, folder_name, job, ref_time):
        builds = []
        job_name = job['displayName']
        folder_job_builds_url = job['url'] + ('api/json?tree=builds[%s]' % FOLDER_JOB_BUILD_ATTRS)
       #print("    %s" % folder_job_builds_url)
        response   = requests.get(folder_job_builds_url)
        result     = response.json()
        for brec in result['builds']:
            #print(brec)
            build = JenkinsBuild(job_name, brec)
            # only take those builds >= ref_time
            build_utc_time_tuple = tuple(time.gmtime(int(str(build.timestamp)[:-3])))
            if build_utc_time_tuple < ref_time:
                break
            builds.append(build)
        return builds[::-1]

    def constructJobUri(self, job_name):
        return "{0}/job/{1}".format(self.base_url, job_name)

    def constructJobBuildUrl(self, job_name, build_number):
        return "{0}/job/{1}/{2}".format(self.base_url, job_name, build_number)

##############################################################################################

class JenkinsBuild(object):
    def __init__(self, name, raw):
        """
        """
        self.name        = name
        self.number      = int(raw['number'])
        self.result      = str(raw['result'])
        self.result      = 'INCOMPLETE' if self.result == 'ABORTED' else self.result

        self.id_str      = str(raw['id'])
        self.Id          = self.id_str
        self.timestamp   = raw['timestamp']

        if re.search('^\d+$', self.id_str):
            self.id_as_ts =     self.timestamp
            self.id_str   = str(self.timestamp)
            self.Id       = self.id_str
        else:
            self.id_as_ts = time.strptime(self.id_str, '%Y-%m-%d_%H-%M-%S')

        self.started     = time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime(self.timestamp/1000)) 
        self.duration    = raw['duration']
        whole, millis    = divmod(self.duration, 1000)
        hours, leftover  = divmod(whole,  3600)
        minutes, secs    = divmod(leftover, 60)
        if hours:
            duration = "%d:%02d:%02d.%03d" % (hours, minutes, secs, millis)
        else:
            if minutes >= 10:
                duration = "%02d:%02d.%03d" % (minutes, secs, millis)
            else:
                duration = " %d:%02d.%03d" % (minutes, secs, millis)

        self.elapsed = "%12s" % duration

        total = (self.timestamp + self.duration) / 1000
        self.finished    = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(total))
        self.changeSets  = self.ripChangeSets(raw['changeSet']['kind'], raw['changeSet']['items'])

    def ripChangeSets(self, vcs, changesets):
        tank = [JenkinsChangeset(vcs, cs_info) for cs_info in changesets]
        return tank

    def __repr__(self):
        name      = "name: %s"       % self.name
        ident     = "id_str: %s"     % self.id_str
        number    = "number: %s"     % self.number
        result    = "result: %s"     % self.result
        finished  = "finished: %s"   % self.finished
        duration  = "duration: %s"   % self.duration
        nothing = ""
        pill = "  ".join([name, ident, number, result, finished, duration, nothing])
        return pill

    def __str__(self):
        elapsed = self.elapsed[:]
        if elapsed.startswith('00:'):
            elapsed = '   ' + elapsed[3:]
        if elapsed.startswith('   00:'):
            elapsed = '      ' + elapsed[6:]
        bstr = "%s Build # %5d   %-10.10s  Started: %s  Finished: %s   Duration: %s" % \
                (self.name, self.number, self.result, self.started, self.finished, elapsed)
        return bstr

class JenkinsJobsFolder(object):
    def __init__(self, displayName, name, url, jobs):
        self.displayName = displayName
        self.name = name
        self.url  = url
        self.jobs = jobs

    def __str__(self):
        sub_jobs = len(self.jobs)
        return "displayName: %-24.24s   name: %-24.24s   sub-jobs: %3d   url: %s " % \
                (self.displayName, self.name, sub_jobs, self.url)
        
    def info(self):
        return str(self)


class JenkinsChangeset(object):
    def __init__(self, vcs, wad):
        self.vcs       = vcs
        self.commitId  = wad['commitId']
        self.author    = wad['author']['fullName']
        self.timestamp = wad['timestamp'] / 1000
        self.comment   = wad['comment']
        self.changes = [JenkinsChangesetFile(changeItem) for changeItem in wad['paths']]

class JenkinsChangesetFile(object):
    def __init__(self, item):
        self.action    = item['editType']
        self.file_path = item['file']

