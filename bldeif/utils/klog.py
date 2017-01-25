__doc__ = """
   This module implements the machinery used to effect a generalized logging 
   capability.  Predominant use is seen as using the FileOutput to record
   information about the processing performed in a program as it proceeds.
   Much like other logging frameworks, log messages can be provided a "level"
   designation and the "level" of the logger can be set so that only messages
   above a certain "level" are recorded.  The FileOutput logging destination
   can also be instantiated with a rotation policy so that a limited set of
   destination files will ever exist, thereby preventing unbounded use of
   disk resource.
   The ActivityLogger class also offers the capability to record unformatted
   verbiage/messages in the log sink.
"""

__addendum__ = """
   Cue whiny voice... "Why didn't you just use the std logging module...?"

   A few reasons, not all all them compelling, but they are mine...

   1) I detest the Java logging approach on which the std Python logging module is based.
      It seems so overly cumbersome to set up and configure properly.
      I have to get a logger and give it a "name", then another call to obtain
      a file handler to direct log messages to a particular file,
      and another to create a formatter object and then tell the handler
      to use that formatter and then another to tell the logger to use the
      handler, etc.   Just too much cruft for my taste.

   2) I wanted a more flexible and simpler to use log rotation capability.

   3) I wanted to see class.method(line_number) in the log entry
        where the class and method were at the level I found useful.

   4) I didn't care about syslog or socket or message bus logging.

   5) At the time, I wanted to experiment with additional log levels.

   6) I wanted the ability to write non-formatted blurbs to the log sink.

   Could I have accomplished the same thing by wrapping std logging?
   Sure, but I'll maintain that would have been painful and more difficult
   to maintain/tune/extend than just having it all in *** 1 *** reasonably
   sized source module.
"""

__author__ = "Kip Lehman <kipster-t@comcast.net>"

__credits__ = "Largely based on a previous ActivityLogger module and klog.py by Kier Davis"

##################################################################################

import sys, os
import types
import inspect
import time
import re
import string
import stat

DEFAULT_FORMAT_STR = "[%(time)s] %(level)5.5s: %(caller)s - %(msg)s"

##################################################################################

def getCaller(frame):
    """
        Given a stack frame object, return the name of the function 
        or the name of the class and method that is operating in the frame.
    """

    caller = ""
    function_name = frame.f_code.co_name

    # Get the name of the calling class
    if "self" in frame.f_locals:
        caller_frame_object = frame.f_locals["self"]
        obj_name = None
        if hasattr(caller_frame_object, "__instance_name__"):
            obj_name = caller_frame_object.__instance__name__()
        elif hasattr(caller_frame_object, "__class__"):
            obj_name = caller_frame_object.__class__.__name__
        else:
            obj_name = caller_frame_object.__name__
        
        if obj_name:
            caller = "%s%s." % (caller, obj_name)

    #caller + function_name

    # Give a name to the function that calls all
    caller = caller.replace("?", "main")

    return caller + function_name

###############################################################################

class StreamOutput(object):
    """
        An instance of this class sends output to a file-like object.
  
        Attributes:
         formatstr  - a String (duh!)
           The format string for the messages. 
           the default is  "[%(time)s] %(level)5.5s: %(caller)s - %(msg)s"
         stream  -  a file-like object (must have a write method)
            object where the object gets written to
    """
  
    def __init__(self, stream=None, formatstr=DEFAULT_FORMAT_STR):
    
        if not stream:
            stream = sys.stdout
            #~ stream = sys.stderr
    
        self.formatstr = formatstr
        self.stream = stream
  
    def log(self, msg, level, exception_triggered=False):
        """
            Logs a message at a given level
        """
        #stack_item = inspect.stack()[3] # assume caller of interest is 3 down in the call stack
        # TODO: document why it's 4 down in the stack for non exception_triggered calls...
        # TODO: investigate feasability of looking at level to determine if this is triggered by
        #       an Exception and if so, go back another level in the stack to 
        #       identify the right class/method that triggered the exception
        stack_level = 3  
        if exception_triggered:
            stack_level = 4  
##
##            print "exception triggered in klog.StreamOutput.log"
##
        stack_item = inspect.stack()[stack_level] # assume caller of interest is stack_levels down in the call stack

##
##        print "StreamOutput stack_item[0]: %s" % repr(stack_item[0])  # it's a frame object...
##
        frame, filename, line_no, code_unit = stack_item[:4]
        caller = getCaller(frame)
        if exception_triggered:
            caller += "(%d)" % line_no
##
##            below_frame, below_filename, below_line_no, below_code_unit = inspect.stack()[stack_level-1][:4]
##            below_caller = getCaller(below_frame)
##            print "stack_level %d filename: %s line_no: %d code_unit: %s  caller: %s" % (stack_level-1, below_filename, below_line_no, below_code_unit, below_caller)
##
##            print "stack_level %d filename: %s line_no: %d code_unit: %s  caller: %s" % (stack_level, filename, line_no, code_unit, caller)
##            above_frame, above_filename, above_line_no, above_code_unit = inspect.stack()[stack_level+1][:4]
##            above_caller = getCaller(above_frame)
##
##            print "stack_level %d filename: %s line_no: %d code_unit: %s  caller: %s" % (stack_level+1, above_filename, above_line_no, above_code_unit, above_caller)
##

        # burn off any .__init__ from the caller value, don't want to expose that
        if caller.endswith('.__init__'):
            caller = caller.replace('.__init__', '')

        #if re.search('\w+\._', caller):
        #    caller = self._abbreviatePrivateCaller(caller, line_no)
##
##        print "log caller: |%s|" % caller
##
    
        formatted = self.formatMsg(level, msg, caller)
        self.stream.write('%s\n' % formatted)
        self.stream.flush()

    def formatMsg(self, level, msg, caller):
        """
            Formats a message using the `formatstr` attribute.
            Returns the formatted message.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S Z", time.gmtime(time.time()))
    
        entry = { "time"   : timestamp,
                  "level"  : level,
                  "caller" : caller,
                  "msg"    : msg,
                }
##    
##        print "log formatMsg entry: |%s|" % repr(entry)
##    

        return self.formatstr % entry

    def _abbreviatePrivateCaller(self, caller, line_no):
        """
            transform the caller's method name from _doSomethingToWhatever
            to _dSTW. IOW, abbreviate the method name down to the 
            first letter of each word in the method name.
        """
        class_name, method_name = caller.split('._')
        abbreviated = method_name[0] + "".join([letter for letter in method_name[1:] if letter in string.uppercase])
        return "%s._%s(%d)" % (class_name, abbreviated, line_no)


    def write(self, text):
        self.stream.write('%s\n' % text)
        self.stream.flush()

#################################################################################

class FileOutput(StreamOutput):
    """
        An instance of this class (a subclass of StreamOutput) handles the file 
        specific manipulations for a logging destination.
    """
    def __init__(self, fname, mode, formatstr=DEFAULT_FORMAT_STR):
        self.formatstr = formatstr
        self.using_stdout = False

        try:
            self.stream = open(fname, mode, encoding='utf-8')
        except Exception as msg:
            problem = 'Error opening logfile: %s --> %s, using stdout instead\n' % (fname, msg)
            sys.stderr.write(problem)
            self.stream = sys.stdout
            self.using_stdout = True
        super(FileOutput, self).__init__(stream=self.stream, formatstr=formatstr)

    def rotationEligible(self):
        return self.using_stdout == False

    def close(self):
        if not self.using_stdout:
            self.stream.close()
  
    def __del__(self):
        self.close()


#########################################################################################

class ActivityLogger(object):
    valid_levels = ['DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'CRITICAL', 'FATAL']
    level_value  = {'DEBUG'    : 1,
                    'INFO'     : 2,
                    'WARN'     : 3,
                    'WARNING'  : 3,
                    'ERROR'    : 4,
                    'CRITICAL' : 5,
                    'FATAL'    : 6,
                   }
    exception_level = 5

    def __init__(self, file_name, append=True, rotate=True, policy='size', limit=1024*1024, frequency='day'):
        self.file_name = file_name
        self.mode = 'a' if append else 'w'
        self.sink = FileOutput(file_name, self.mode)
        self.rotate = rotate
        self.current_level = self.level_value['INFO']
        self.message_count = 0
        if self.rotate:
            self.rotator = LogFileRotator(file_name, policy, limit, frequency, self)

    def setLevel(self, level_name):
        if level_name.upper() in ActivityLogger.valid_levels:
          self.current_level = ActivityLogger.level_value[level_name.upper()]
##
##        print("current ActivityLogger level set to |%s|" % self.current_level)
##
  
    def log(self, msg, level, exception_triggered=False):
        # check to see if msg is None, String, List, Dict, Int, Float, 
        # Class, Class instance, Exception, Exception instance
        #if type(msg) == types.UnicodeType:
        #    msg = str(msg)
        #if type(msg) not in [types.StringType, types.NoneType, types.IntType, types.FloatType]:
        #    msg = self._augment(msg)
##
##        print("ActivityLogger.log  message level: |%s|  current log level |%s|" % \
##              (self.level_value[level], self.current_level))
##
        if self.level_value[level] >= self.current_level:
            self.sink.log(msg, level, exception_triggered=exception_triggered)
  
            if self.rotate and self.sink.rotationEligible(): # no rotation possible with stdout...
                self.rotator.rotateLogPerPolicy()

    def _augment(self, original):
        """
        """
        if type(original) in [types.DictType, types.ListType, types.TupleType]:
            return repr(original)
##
##        print("in ActivityLogger._augment: original parm value: |%s|" % repr(original))
##        print("type of original msg: %s " % type(original))
##        type_as_string = repr(type(original))
##        if '(<type ' in type_as_string:
##            print "i saw the type identifier in the type"
####        else:
##            print("no type identifier in the type")
##
        # for now, punt by turning the original into a types.StringType
        augmented = "%s" % original
        return augmented

    def debug(self, msg):
        self.log(msg, 'DEBUG')

    def info(self, msg):
        self.log(msg, 'INFO')

    def warn(self, msg, exception_triggered=False):
        self.log(msg, 'WARN', exception_triggered=exception_triggered)

    warning = warn

    def error(self, msg, exception_triggered=False):
        self.log(msg, 'ERROR', exception_triggered=exception_triggered)

    def critical(self, msg, exception_triggered=True):
        self.log(msg, 'CRITICAL', exception_triggered=exception_triggered)

    def fatal(self, msg, exception_triggered=True):
        self.log(msg, 'FATAL', exception_triggered=exception_triggered)

    def write(self, msg, level=None):
      if not level or level not in ActivityLogger.valid_levels:
          self.sink.write(msg)
      else:
          if self.level_value[level] >= self.current_level:
              self.sink.write(msg)

#########################################################################################

class LogFileRotator(object):
    def __init__(self, file_name, policy, limit, frequency, logger):
        """
            if the policy is 'size', then the limit parm specifies roughly the
              size limitation on the file_name after which the rotation is performed.
            if the policy is 'calls', then the limit parm specifies roughly the
              number of calls (or lines) in the file_name after which rotation is performed.
            If the policy is 'time', the frequency value specifies how often
              a log rotation is performed.
                The value can be 'day', 'hour', 'minute' or an integer value designated seconds.
                The seconds value must be >= 60
        """
        self.logfile = file_name
        self.policy = policy
        self.limit  = limit
        self.frequency = frequency
        self.logger = logger
        self.message_count = 0
        self.rotation_check = 10
        self.time_fudge = 30
        if self.policy == 'time':
            self.last_rotation   = int(time.time())  # effectively, now
            try:
                if self.frequency not in ['day', 'hour', 'minute']:
                    seconds = int(self.frequency)
                    if seconds < 60:
                        seconds = 60
                    self.frequency = seconds
            except:
                self.frequency = 'day'

    def rotateLogPerPolicy(self):
        self.message_count += 1

        if self.policy == 'calls':
            if (self.message_count % self.limit) == 0:
                self.rotateLog()
        elif self.policy == 'time':
            doRotate = self._maybeRotate()
            if doRotate:
                self.rotateLog()
        elif self.policy == 'size':
            if os.path.getsize(self.logfile) >= self.limit:
               self.rotateLog()
        else:
            return 

    def enableScreenOutput(self):
        self.screenOutput = 1

    def disableScreenOutput(self):
        self.screenOutput = 0

    def _maybeRotate(self):
        """
            We're only going to call this internal use method when the rotation scheme
            is set to 'time'.
            In this case we only make a call to time.time() on the following conditions:
                if the self.rotation_check value is set to 1 
                if the self.rotation_check value is non-zero 
                   AND self.message_count mod self.rotation_check is equal to 0
        """
        should_check = False
        if self.rotation_check == 1:
            should_check = True

        elif self.rotation_check > 1:  # we don't check on every log call, only after n calls
            doit = self.message_count % self.rotation_check == 0
            if doit:
                should_check = True

        if should_check:
            now    = int(time.time())
            since_last = now - self.last_rotation     # and how long since last rotation
            if since_last >= self.frequency:
                self.last_rotation = now
                return True
            
        return False


    def _oldestLogfile(self, logfile_dir, logfile_names):
        """
            Return the name of the oldest filename in the logfile_names list
            with a .<digit> suffix
        """
        if not logfile_names:
            return None

        old_logfiles = []

        for filename in logfile_names:
            if filename[-1] not in string.digits:
                continue

            age = os.stat('%s/%s' % (logfile_dir, filename))[stat.ST_MTIME]
            age_filename = (age, filename)
            old_logfiles.append(age_filename)

        old_logfiles = sorted(old_logfiles)
        old_logfiles.reverse()
        filenames = [filename for age, filename in old_logfiles]
        #for age, logfile in old_logfiles:
        #    print "     %s  %s" % (age, logfile)
        return filenames.pop()


    def rotateLog(self):
        """
            close target.log
            mv target.log => targetLog.n   (see note below on figuring out value of 'n'
            reopen a new targetLog

            the main item is figuring out n
            when there are no current log files names with 'n', set n to 1
            when there are current log file names with 'n' and the highest is less than 9
                set n = highest n +1
            when there are current log file names with 'n' and the highest n == 9
            then we have to determine file ages to see which is the proper n value to use
            as we cycle though 1->9
        """

        n = 1
        rotationFile = '%s.%s' % (self.logfile, n) # default

        logfile_dir = os.path.dirname(self.logfile) or '.'
        allFiles = os.listdir(logfile_dir)
##        self.lf.write('  all logfiles in the %s directory:\n' % logfile_dir)
##        for lf in allFiles:
##            self.lf.write('\t%s\n' % lf)
##
        logfiles = [fn for fn in allFiles if fn.find(os.path.basename(self.logfile)) >= 0]
##        self.lf.write(' logfiles in the %s family:\n' % os.path.basename(self.logfile))
##        for lf in logfiles:
##            self.lf.write('\t%s\n' % lf)
##
        digitsUsed = [int(fn[-1]) for fn in logfiles if fn[-2] == '.' and fn[-1] in string.digits]
        digitsUsed.sort()
        digitsUsed = ['%d' % digit for digit in digitsUsed]
        if digitsUsed:
            #sys.stdout.write('\tdigits used: %s\n' % ', '.join(digitsUsed))
            last = int(digitsUsed[-1])
            if last < 9:    
                n = last + 1
                rotationFile = '%s.%d' % (self.logfile, n)
            else:
                oldest = self._oldestLogfile(logfile_dir, logfiles)
                #print "oldest logfile: |%s|" % oldest
                n = int(oldest[-1]) # last char of the filename is a digit
                rotationFile = oldest

        sys.stdout.write('  %s will be renamed to %s\n' % (self.logfile, rotationFile))

        self.logger.sink.close()
        os.rename(self.logfile, rotationFile)
        self.logger.sink = FileOutput(self.logfile, self.logger.mode)

        self.last_rotation = int(time.time())


