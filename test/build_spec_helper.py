import sys, os
import pytest
import time
from datetime import datetime, timedelta
from bldeif.utils.konfabulus import Konfabulator
from bldeif.utils.klog       import ActivityLogger
from bldeif.jenkins_connection import JenkinsConnection
from bldeif.agicen_bld_connection import AgileCentralConnection

from pprint import pprint

def epochSeconds(offset):
    if offset[-1] == 'd':
        days_to_subtract = int(offset[:-1])
        es = datetime.today() - timedelta(days=days_to_subtract)
        return int(es.timestamp())


class MockJenkinsBuild:
    def __init__(self, job_name, build_number, status, started, duration, commits=None):
        self.name     = job_name
        self.number   = build_number
        self.status   = status
        self.result   = status
        self.timestamp = started
        self.id_str   = datetime.fromtimestamp(started).strftime('%Y-%m-%d_%H-%M-%S')
        self.id_as_ts = time.gmtime(self.timestamp)
        # the next line is what happens if the job is a regular or view build.
        #self.id_as_ts = time.strptime(self.id_str, '%Y-%m-%d_%H-%M-%S')
        self.started  = time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime(self.timestamp/1000))
        self.duration = duration
        total = (self.timestamp + self.duration) / 1000
        self.finished    = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(total))
        self.commits = commits


    def as_tuple_data(self):
        start_time = datetime.utcfromtimestamp(self.timestamp / 1000.0).strftime('%Y-%m-%dT%H:%M:%SZ')
        build_data = [('Number', self.number),
                      ('Status', str(self.result)),
                      ('Start', start_time),
                      ('Duration', self.duration / 1000.0),
                      ('Uri', self.url)]
        return build_data
