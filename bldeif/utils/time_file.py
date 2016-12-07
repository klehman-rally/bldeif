# Copyright 2011-2012 Rally Software Development Corp.  All Rights Reserved.

#############################################################################################

import os
import re
import time
import calendar
import types

#############################################################################################

# Store the last time the connector was run - just in case the connector stops and restarts
# The timestamp  is stored as a string in "YYYY-MM-DD HH:MM:SS Z" format

ISO8601_FORMAT = "%Y-%m-%dT%H:%M:%S.%L%z"
STD_TS_FORMAT  = "%Y-%m-%d %H:%M:%S Z"

#############################################################################################

class TimeFile(object):
    """
        An instance of this class is used to record a timestamp in a file.
        The timestamp is an ASCII representation that is derived from the ISO-8601 format.
    """

    def __init__(self, filename, logger):
        self.filename = filename
        self.log      = logger

    def exists(self):
        if not os.path.exists(self.filename):
            return False
        return True

    def read(self):
        """
            Return an epoch seconds value representing the time recorded in the target file
            or a default value of 5 minutes ago.
        """
        # default to 5 minutes ago if file non-existent or empty 
        default = time.time() - (5*60)
        last_run_timestamp = default

        try:
            with open(self.filename, "r") as f:
                content = f.read()
                if content.count("\n") > 0:
                    entry = content.split("\n").pop(0).strip()
                else:
                    entry = content.strip()
                if len(entry) > 0:
                    iso = False
                    std = False
                    if re.search('^\d+.*T\d+:\d+.\d+', entry):  # in ISO8601 format?
                        iso = True
                        #print "detected ISO8601 format..."
                        last_run_timestamp = calendar.timegm(time.strptime(entry, ISO8601_FORMAT))
                    if re.search('^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \w+$', entry):
                        std = True
                        #print "detected standard ts format..."
                        ts = time.strptime(entry, STD_TS_FORMAT)
                        last_run_timestamp = calendar.timegm(ts)
                    if not (iso or std):
                        prob = "Invalid format for timefile entry: %s, reverting to default of %s"
                        self.log.error(prob % (entry, default))
        except:
            prob   = "Could not read time entry from %s" % self.filename
            action = "rewriting time file with default value" 
            self.log.error("%s, %s" % (prob, action))
            self.write(timehack=last_run_timestamp)

        return int(last_run_timestamp)


    def write(self, timehack=None):
        """
            Writes the timefile with a datetime value in the STD_TS_FORMAT.
            If not supplied, the value written is the current time.
            If supplied, the timehack value should be a datetime object (or epoch seconds?)
        """
        if not timehack:
            timehack = time.time()
        if type(timehack) == str and timehack.count('-') > 0:
            timehack = timehack.replace('T', ' ')[:19] + " Z"
        else:
            timehack = time.strftime(STD_TS_FORMAT, time.gmtime(timehack))
        with open(self.filename, "w") as f:
            f.write("%s\n" % timehack)

