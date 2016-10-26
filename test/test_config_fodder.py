

SIMPLE_CONFIG_STRUCTURE = """
---

JenkinsBuildConnector:

    AgileCentral:
        <!AC_CREDS_INFO!>

    Jenkins:
        Protocol  : http
        Server    : int-win7bldmstr.f4tech.com
        Port      : 8080
        Prefix    :
        Auth      : false
        AgileCentral_DefaultBuildProject: Sandbox

        Jobs:
            - Job : VCSEIF-git-master

            - Job: WICoCo-master build
              AgileCentral_Project: Dynamic

            - Job: jenkins-rally-build-publisher
              AgileCentral_Project: Static

    Service:
        Preview       : False
        LogLevel      : DEBUG
        MaxBuilds     : 100   # current implementation is this is a per job maximum not total builds
        VCSData       : False

...


"""

CONFIG_STRUCTURE_WITH_FOLDERS = """
---

JenkinsBuildConnector:

    AgileCentral:
        <!AC_CREDS_INFO!>

    Jenkins:
        Protocol  : http
        Server    : almci.f4tech.com
        Port      : 80
        Prefix    :
        Auth      : false
       #API_Token : 342gaeg3q4ybv8th4obr8g3afe
       # to get an API_Token, in your browser, navigate to http://server:port/user/<username>/configure
        AgileCentral_DefaultBuildProject: Sandbox

        Folders:
            - Folder : ALM
              #AgileCentral_Project: Engineering
              exclude: backward-compatibility,on-demand

            - Folder : ALM Deploy

            - Folder : Pinata

    Service:
        Preview       : True
        LogLevel      : DEBUG
        MaxBuilds     : 50   # current implementation is this is a per job maximum not total builds
        StrictProject : True
        VCSData       : True
        # What is the StrictProject entry used for?
        #
        # If your team/project morphs into another AC project, you might not have to
        # update your config file(s) if you've set the Service -> StrictProject to False
        #  (If you have a BuildDefinition for the job in question associated with another
        #   Project that the account accessing Agile Central can find, and the original
        #   Project is moribund or has been renamed, the connector will post the Builds
        #   to be associated with the BuildDefinition with the Name of the Jenkins job.)

..."""