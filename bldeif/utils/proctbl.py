
# Copyright 2011-2012 Rally Software Development Corp. All Rights Reserved.

import os
import re
import socket
import time
import datetime

########################################################################################

class ProcTable(object):

    @staticmethod
    def allProcesses():
        op_sys = 'posix'  # default

        try:
            import win32com.client
            op_sys = 'windows'
        except Exception as msg:
            pass

        try:
            import pwd
        except Exception as msg:
            pass

        if op_sys == 'posix':
            all_procs = ProcTable.posixProcesses()
        else:
            all_procs = ProcTable.windowsProcesses()

        #for proc in all_procs:
        #  print "%5d %s" % (proc['pid'], proc['cmdline'])

        return all_procs

    @staticmethod
    def posixProcesses():
        all_procs = []
        import subprocess
        command = 'ps -ef'
        command_vector = command.split(' ') # to make our command a list of strings
        ps_output = subprocess.Popen(command_vector, stdout=subprocess.PIPE).communicate()[0]
        pslines = ps_output.decode().split("\n")
        hdr_line = pslines[0]
        cmd_column_ix = hdr_line.index('CMD')
        #proc_lines =  pslines[1:len(pslines)-1] # the last line is a blank line...
        proc_lines =  pslines[1:-1] # the last line is a blank line...
        for ps_entry in proc_lines:
            #puts "|%s|" % ps_entry
            fields = re.split('\s+', ps_entry.lstrip())
            uid, pid, ppid, junk, started = fields[0:5]
            remainder = " ".join(fields[7:])
            #proc_info = {'pid'     : int(pid),
            #             'ppid'    : int(ppid),
            #             #'cmdline' : ps_entry[cmd_column_ix:len(ps_entry)],
            #             'cmdline' : ps_entry[cmd_column_ix:],
            #             'started' : started,
            #             'uid'     : int(uid)
            #            }
            #fields[5] = ps_entry[cmd_column_ix:]
            fields[5] = remainder
            proc_info = ProcessInfo(fields)
            all_procs.append(proc_info)
        return all_procs

    @staticmethod
    def windowsProcesses():
        import win32com.client
        all_procs = []
        host = socket.gethostname()
        wmi = win32com.client.GetObject("winmgmts://%s/root/cimv2" % host)
        processes = wmi.InstancesOf("Win32_Process")
        for wproc in processes:
            if not wproc.CreationDate:
                startDate = None
            else:
                temp = wproc.CreationDate.split('.').pop(0)
                startDate = time.strftime("%Y-%m-%d %H:%M:%S ")
                #startDate = Date.parse(wproc.CreationDate.split('.').pop(0))
            fields = [0, wproc.ProcessId, wproc.ParentProcessId, 
                      "", startDate, wproc.CommandLine]
            proc_info = ProcessInfo(fields)
            all_procs.append(proc_info)
        return all_procs


    @staticmethod
    def targetProcess(target_pid):
        """
            Return a dict with process related info for the given target_pid
        """
        aps = ProcTable.allProcesses()
        target_proc = [proc for proc in aps if proc.pid == int(target_pid)]
        if target_proc:
            return target_proc[0]
        else:
            return None

    @staticmethod
    def processesOwnedBy(target_uid=None):
        """
            Return a list of dicts with process related info for all processes
            owned by the given target_uid
        """
        if target_uid is None:
            target_uid = os.getuid()
        aps = ProcTable.allProcesses()
        procs = [proc for proc in aps if proc.uid == int(target_uid)]
        if not procs:
            return None
        else:
            return procs

    @staticmethod
    def processesMatchingPattern(pattern):
        """
            Return a list of dicts with process related info for all processes
            whose command line contains the given pattern string.
        """
        cmd_pattern = re.compile(pattern)
        aps = ProcTable.allProcesses()
        procs = [proc for proc in aps if cmd_pattern.search(proc.cmdline)]
        if not procs:
            return None
        else:
            return procs

######################################################################################

class ProcessInfo(object):
    def __init__(self, fields):
        user_field = fields[0]
        try:
            self.uid = int(user_field)
        except:
            try:
                import pwd
                info = pwd.getpwnam(user_field)
                self.uid = info.pw_uid
            except:
                self.uid = 0

        self.pid  = int(fields[1])
        self.ppid = int(fields[2])
        self.junk    =  fields[3]
        self.started =  fields[4]
        self.cmdline =  fields[5]

    def __repr__(self):
        return "%5s %5s %5s %12s %s" % (self.pid, self.uid, self.ppid, self.started, self.cmdline)

######################################################################################

#all_procs = ProcTable.allProcesses()
#for proc in all_procs:
#    #print "%5d %s" % (proc['pid'], proc['cmdline'])
#    print "%5d %s" % (proc.pid, proc.cmdline)

#my_procs = ProcTable.processesMatchingPattern('klehman')
#for proc in my_procs:
#    print "%d  %5d %s" % (proc.uid, proc.pid, proc.cmdline)
