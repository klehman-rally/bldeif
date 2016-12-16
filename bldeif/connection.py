
import re

from collections import OrderedDict
from bldeif.utils.eif_exception import ConfigurationError

#############################################################################################################

class BLDConnection(object):

    def __init__(self, logger):
        self.log      = logger
        self.config   = None
        self.username = None
        self.password = None
        self.username_required = True
        self.password_required = True
        self.build_selectors   = []
        self.log.info("Initializing %s connection version %s" % (self.name(), self.version()))

    def name(self):
        """
            abstract, provider should return a non-empty string with name of the specific connector
        """
        raise NotImplementedError("A BLDConnection subclass must implement the name method")

    #Placeholder to put the version of the connector
    def version(self):
        """
            abstract, provider should return a non-empty string with version 
            identification of the specific connector
        """
        raise NotImplementedError("All descendants of the BLDConnection class need to implement version()")
        #Should return a string

    def getBackendVersion(self):
        raise NotImplementedError("All descendants of the BLDConnection class need to implement getBackendVersion()")
        #Should return a string representing the version of the back-end system the instance of this class is connected to

    def connect(self):
        """
            Returns True or False depending on whether a connection was "established".
            As many connectors are stateless, the "establishment of a connection" might
            just mean that the target and credentials are adequate to post a request and
            receive a non-error response.
        """
        raise NotImplementedError("All descendants of the BLDConnection class need to implement connect()")
        #Should return True or False

    def disconnect(self):
        """
            Returns True or False depending on whether an existing connection was disconnected
            successfully.
            As many connectors are stateless, the disconnection may be as easy as 
            resetting an instance variable to None
        """
        raise NotImplementedError("All descendants of the BLDConnection class need to implement disconnect()")
        #Should return True or False

    def fieldExists(self, field_name):
        """
            Return a boolean truth value (True/False) depending on whether the targeted
            field_name exists for the current connection on a Build
        """
        raise NotImplementedError("All descendants of the BLDConnection class need to implement fieldExists(field_name)")


    def validate(self):
        """
        """
        raise NotImplementedError("All descendants of the BLDConnection class need to implement a validation method")


    def internalizeConfig(self, config):
        """
            config has already been read, it comes to us here as
            a dict with information relevant to this connection
        """
        self.config = config
        self.username = config.get('Username', config.get('User', False))
        self.password = config.get('Password', False)
        self.proxy_protocol = config.get('ProxyProtocol', 'http')
        self.proxy_server   = config.get('ProxyServer',   False)
        self.proxy_port     = config.get('ProxyPort',     False)
        self.proxy_username = config.get('ProxyUsername', config.get('ProxyUser', False))
        self.proxy_password = config.get('ProxyPassword', False)
        self.build_selectors  = config.get('BuildSelectors', []) 
        self.lookback = int(config.get('Lookback', 60)) * 60 # if not provided default this to 1 hour in secs
        self.debug    = config.get('Debug', False)
        #print("Connection debug value is {0}".format(self.debug))
        if self.debug:
            self.log.setLevel('DEBUG')


    def getRecentBuilds(self, ref_time):
        """
            Finds items that have been created since a reference time (ref_time is in UTC) 
            and applying all specified BuildSelector conditions.

            Concrete subclasses must implement this method and return a list of qualified items.
        """
        problem = "All descendants of the BLDConnection class need to implement getRecentBuilds(ref_time)"
        raise NotImplementedError(problem)


    def createBuild(self, int_work_item):
        """
            This method should never be overridden. 
            Instead override one of the next three (it might be called 'final' in another language).
        """
        modified_int_work_item = self.preCreate(int_work_item)
        work_item              = self._createInternal(modified_int_work_item)
        modified_artifact      = self.postCreate(work_item)
        return modified_artifact


    def preCreate(self, int_work_item):
        """
            Usually will be overridden by those who extend our existing connection 
            classes (like RallySCMConnection or ...Connection?)
        """
        return int_work_item


    def _createInternal(self, int_work_item):
        """
            Concrete subclasses must implement this method and return the newly created artifact.

            Returns an artifact 
        """
        problem = "All descendants of the BLDConnection class need to implement __createInternal(int_work_item)"
        raise NotImplementedError(problem)


    def postCreate(self, artifact):
        """
            Usually will be overridden by those who extend our existing connection 
            classes (like RallySCMConnection or ???Connection)
        """
        return artifact


