# Copyright 2011-2012 Rally Software Development Corp.  All Rights Reserved.

import os
import time
import re

from  bldeif.utils.proctbl import ProcTable

#########################################################################################

LOCK_FILE_ENTRY_PATTERN = re.compile(r'^(\d+)\s+(.+)$')

#########################################################################################

class LockFile(object):

    @staticmethod
    def exists(filename):
        """
            Given a filename, return a boolean indication of whether that file exists
            and is readable.
        """
        if os.path.exists(filename) and os.path.isfile(filename):
            if os.access(filename, os.F_OK | os.R_OK):
                return True
            else:
                raise Exception('Lock file: %s is unreadable' % filename)
        else:
            return False

    @staticmethod
    def lockerIsRunning(filename, locker):
        """
            Return False if no lock file exists 
            OR the PID that wrote the lock file is no longer running
        """
        if not os.path.exists(filename):
            return False
        holder = LockFile.currentLockHolder(filename)
        if not holder:
            return False
        mo = LOCK_FILE_ENTRY_PATTERN.search(holder)
        if not mo:  # we can't tell without a pid...
            return False 
        locker_pid = mo.group(1)
        started    = mo.group(2)
        running = ProcTable.targetProcess(locker_pid)
        if not running:
            return False
        return True


    @staticmethod
    def currentLockHolder(filename):
        """
            Given a filename, attempt to open and read the content.
            Return any content (which should be a single text line,
            containing the PID and process start time)
        """
        if not os.path.exists(filename):
            return ""
        try:
            with open(filename, 'r') as lf:
                holder = lf.read().strip()
        except Exception as msg:
            raise Exception('Unable to read contents of lock file %s: %s' % \
                                          (filename, msg))
        if not holder:
            raise Exception('lock file: %s has no content' % filename)
        try:
            pid, lock_time = holder.split(' ', 1)
            pid = int(pid)
        except Exception as msg:
            raise Exception("lock file '%s' purported pid '%s' is not an integer value" % (filename, pid))

        return holder


    @staticmethod
    def createLock(filename):
        """
            Remove any existing lock file (filename)
            Create the filename with the PID of this process and a current timestamp
        """
        LockFile.destroyLock(filename)
        try:
            pid = os.getpid()
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S Z", time.gmtime(time.time()))
            lf_entry = "%d %s\n" % (pid, timestamp)
            with open(filename, 'w') as lf:
                lf.write(lf_entry)
        except Exception as msg:
            raise Exception('Unable to create lock file %s: %s' % (filename, msg))

    @staticmethod
    def destroyLock(filename):
        """
            Remove the existing lock file (filename)
        """
        if not os.path.exists(filename):
            return True
        try:
            os.remove(filename)
        except Exception as msg:
            raise Exception('Unable to remove lock file %s: %s' % (filename, msg))
        return True

