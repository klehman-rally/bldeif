
import re

from collections import OrderedDict
import bldeif.utils.eif_exceptions
ConfigurationError = bldeif.utils.eif_exceptions.ConfigurationError

#############################################################################################################

class BuildSelector(object):

    def __init__(self, condition):
        """
            A BuildSelector instance is of the form: 
                attribute relational_operator value_or_expression
            Prime our 3 instance attributes of interest in case the regex match fails
        """
        self.attribute = ""
        self.relation  = ""
        self.value     = ""
        # define our extractor regex to handle a string with "attribute relation value_or_expression_that_may have spaces"
        # examples: 'Number > 1000' or 'Changesets != []' or "Name = 'CI-coverage-metrics'"
        # We only support these relational operators (=, !=, <, <=, >, >=) 
        attr_identifier_pattern = '[a-zA-Z@$%&*].*[a-zA-Z0-9_@$%&*]+'
        relational_operators     = ['=', '!=', '<', '<=', '>', '>=']
        relations = "%s" % [relational_operators.join('|')]
        selector_pattern_string = "^(?P<attribute>)\s+(?P<relation>)\s+(?P<value>.+)$" % ( attr_identifier_pattern, relations)

        selector_patt = re.compile(selector_pattern_string)
        mo = selector_patt.match(condition)
        if mo:
            self.attribute = mo.group('attribute').strip()
            self.relation  = mo.group('relation')
            self.value     = mo.group('value').strip()
        if not (self.attribute and self.relation and self.value):
            raise ConfigurationError("Invalid %s Selector specification: %s" % (self._type, condition))

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
        satisfactory = True

        if self.username_required:
            if not self.username:
                self.log.error("<Username> is required in the config file")
                satisfactory = False
            else:
                self.log.debug('%s - user entry "%s" detected in config file' % (self.__class__.__name__, self.username))

        if self.password_required:
            if not self.password:
                self.log.error("<Password> is required in the config file")
                satisfactory = False
            else:
                self.log.debug('%s - password entry detected in config file' % self.__class__.__name__)

        satisfactory = self.hasValidBuildSelectors()

        return satisfactory


    def hasValidBuildSelectors(self):
        """
            This method should be overridden in the BLDConnection subclass for 
            connections whose target does not support standard relational 
            operators of (=, !=, <, >, <=, and >=) .
        """
        if len(self.build_selectors) == 0: 
            return True
        status = True
        for bs in self.build_selectors:
            if not self.fieldExists(bs.field):
                self.log.error("BuildSelector field_name %s not found" % bs.field)
                status = False

        return status


    def internalizeConfig(self, config):
        """
            config has already been read, it comes to us here as
            a dict with information relevant to this connection
        """
        self.config = config
        self.username = config.get('Username', config.get('User', False))
        self.password = config.get('Password', False)
        self.build_selectors  = config.get('BuildSelectors', []) 
        self.lookback = int(config.get('Lookback', 60)) * 60 # if not provided default this to 1 hour in secs
        self.debug    = config.get('Debug', False)
        #print("Connection debug value is {0}".format(self.debug))
        if self.debug:
            self.log.setLevel('DEBUG')

        # minimum valid selector spec is 6 chars, 'xy = z'
        bad_build_selectors = [sel for sel in self.build_selectors if len(sel) < 6]
        if bad_build_selectors:
            raise ConfigurationError("One or more BuildSelector specifications is structurally invalid")
        
        if self.build_selectors:
            #transform our textual selector conditions to BuildSelector instances
            self.build_selectors = [BuildSelector(cs) for cs in self.build_selectors]


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


