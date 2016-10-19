

SIMPLE_CONFIG_STRUCTURE = """
---

JenkinsBuildConnector:

    AgileCentral:
        <!AC_CREDS_INFO!>

    Jenkins:
        Protocol  : http
        Server    : int-win7bldmstr.f4tech.com
        Port      : 80
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

...


"""