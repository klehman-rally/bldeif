
import sys
import inspect
import traceback

######################################################################################

errout = sys.stderr.write

_blurt = False
_logger = None

######################################################################################

def logAllExceptions(truthiness, logger=None):
    """
        Call this function when you want the convenience of raising the 
        Exception subclasses defined in this module without having to supply
        an instance of a logger for each raise statement. 
        Simply supply the logger to be used in this call and you're set
        for the duration!
    """
    global _blurt, _logger
    if truthiness and logger:
        _blurt = True
        _logger = logger
    else:
        _blurt = False
        _logger = None

######################################################################################

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

######################################################################################

class EIFException(Exception): 
    def __init__(self, msg, logger=None):
        global _blurt, _logger
        if logger or (_blurt and _logger):
            log = logger or _logger
            log_method = getattr(log, self.log_level, 'error')
            # prepend message with specific exception class name
            msg = "<%s> %s" % (self.__class__.__name__, msg) 
            log_method(msg, exception_triggered=True)
        else:
            errout('%s raised: %s\n' % (self.__class__.__name__, msg))
            sys.stderr.flush()
        #
        # should we blurt out any traceback info?
        #
        # stack_level could be 2 or 3 or 4 or 5 ...
        #stack_level = 5  # this seems the right value in py.test mode
        #stack_level = 3  # this seems the right value in regular execution mode
        #caller, filename, line_no, code_unit = stackulus(inspect.stack()[stack_level])
        #caller += "(%d)" % line_no
        raise self

def stackulus(stack_item):
    """
        placeholder for code than can futz with various levels of the stack and 
        retrieve interesting things about an item at particular stack level
    """
    frame, filename, line_no, code_unit = stack_item[:4]
    caller = getCaller(frame)
    return caller, filename, line_no, code_unit


class RecoverableException(EIFException): 
    """
        This brand of EIFException is intended be used when a single atomic operation
        has failed but further processing can be attempted.
    """
    log_level = 'warn'

class UnrecoverableException(EIFException): 
    """
        This brand of EIFException is intended be used when an operation has failed and
        no further processing can or should be attempted.  
        The condition that caused this operation failure is either caused by a 
        bad configuration or something else that won't be different with the passage
        of time.
    """
    log_level = 'error'

class FatalError(EIFException):
    """
        This brand of EIFException is intended be used when an operation has failed and
        no further processing can or should be attempted.  
        The condition that caused this operation will typically be caused by an
        initialization/setup error where some part of the overall machinery is missing
        or unable to be exercised.
    """
    log_level = 'fatal'

class ConfigurationError(EIFException):
    """
        This brand of EIFException is intended to be used when a configuration error
        has been detected. Because of the configuration error no further processing
        can or should proceed. The configuration will have to be fixed or this 
        exception would be raised again in a future invocation.
    """
    log_level = 'fatal'

class NonFatalConfigurationError(EIFException):
    """
        This brand of EIFException is intended to be used when a configuration error
        has been detected. This exception differs from the ConfigurationError
        in that the configuration error detected will not prevent reasonable operation
        from proceeding but should be noted for future correction.
    """
    log_level = 'error'

class OperationalError(EIFException):
    """
        This brand of EIFException is intendedto be used when an operation has failed and
        no further processing can or should be attempted.  
        The condition that caused this though may not be in place if the operation were
        attempted again at a later time.
    """
    log_level = 'error'

__all__ = [RecoverableException, UnrecoverableException, 
           ConfigurationError, NonFatalConfigurationError, OperationalError, 
           logAllExceptions
          ]

