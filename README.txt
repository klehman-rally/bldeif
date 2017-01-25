

   Overview
      The Agile Central Build Connector for Jenkins posts information about Jenkins Job Builds to
      Agile Central, relating those Build items to AC Changesets and Artifacts if sufficient information
      is contained in the VCS commit messages to identify the relevant artifacts.
      The AC Build Connector is classified as a "one-way" / "one-time" mechanism.  Information in
      Jenkins is never altered, information is only written in Agile Central and no duplication of
      data is attempted/allowed.
      The AC Build Connector consists of software that you run on your platform according to your
      desired schedule.  The configuration of the connector is policy-based, meaning that you do not
      need to provide configuration information in Jenkins for each job for which you want the connector
      to operate.  While you can configure specific jobs with this connector, the opportunity is there
      to be able to configure by views and/or folders with the option to use shell regex syntax to
      include jobs or exclude jobs.  The policy based nature allows you to add Jenkins jobs and not have
      to alter the configuration in order to get the builds for those jobs to be posted to Agile Central.


   Requirements

      Jenkins 2.2 or higher  (For CloudBees, the version identifier is different, but most recent versions (>= May 2016) will work)

      Python 3.5   (if the platform you are using is Windows, we recommend using the 64-bit version)
         You can retrieve the package/installer from www.python.org

         - Windows only
              win32com module available from:
                 https://sourceforge.net/projects/pywin32/files/pywin32/Build%20220/pywin32-220.win-amd64-py3.5.exe/download
              (If you are using the 64-bit version Python3.5.x, other pick the appropriate file from
                 https://sourceforge.net/projects/pywin32/files/pywin32/Build%20220/)


   Installation

      pip3.5 install requests==2.8.1
      pip3.5 install pyral==1.2.3
      pip3.5 install PyYAML==3.12
      unpack bldeif-0.9.0.zip
         change your working directory (cd) to a directory where you want to install the connector
         unzip bldeif-0.9.0.zip   (or use a suitable program that can unzip a .zip file)
         cd bldeif-0.9.0
         ls -laR   # observe the unpacked contents, or use dir on Windows

            bldeif              # bldeif module root directory
            bldeif_connector    # connector initiation script, this is what you will run
            config              # holds any config files used with this connector
                sample.yml      # a sample config to use as a base reference
            README.txt          # this file


   Setup

      Locate the config subdirectory
      Copy the sample.yml file to a file named suitably for your environment
         eg,  cp sample.yml to product_x.yml   (or some other suitably named file that has a .yml suffix)

      Edit your product_x.yml file
        Change the sample values for credentials, Workspace, Project, Job, View, Folder to values that are
        relevant and valid for your environment.

        *see Appendix A on config file syntax


   Operation

      Manual
         Using a terminal window or console:
            cd to the installation root directory  eg.  /opt/local/sw/bldeif-0.9.0
            python3.5 bldeif_connector product_x.yml

         This software requires that the configuration file reside in the config subdirectory.  You specify the name
         of the file on the command line (don't specify the subdirectory in the command line argument).

      Scheduled
         use either cron or launchctl or Windows Task Scheduler
            make sure the environment in effect when running this software has an appropriate environment set
            so that you can run:
               python3.5 $BLDEIF/bldeif_connector your_config_file_name.yml
   
            where $BLDEIF is the reference to an environment variable containing the
            fully qualified path to the directory where the software is installed.  Here's an example:
            If you unzipped the package in /opt/local/sw, then your BLDEIF would be set like this:
               export BLDEIF=/opt/local/sw/bldeif-0.9.0


  Time File
      In normal operation, the connector writes a "time file" (in the log directory)
      whose name is based on the configuration file name.  
      Example: If the configuration file name is 'product_x.yml'
      then the associated "time file" name would be 'product_x_time.file'.  The content
      of the "time file" is a single line containing a human readable date/time stamp value
      in the format 'YYYY-MM-DD hh:mm:ss Z'.  The value represents the timestamp of the last
      Jenkins jobs considered (after some negative value adjustment to insure no Jenkins jobs
      are ever overlooked).  When the connector is run a subsequent time, it consults the
      "time file" to determine which jobs need to be considered for the current run by
      only processing the builds whose start time is greater than or equal than the "time file" value.
      It is possible to set the "time file" value artificially (but in the correct format) so
      that you can "go back in time" and pick up builds from some arbitrary point in the past.
      The connector does not duplicate Build records so you don't have to worry about
      duplicated information getting posted to Agile Central.


  Troubleshooting

      The connector always writes a log file named based on the configuration file name.
      The log file is written into the log subdirectory under the "base" installation directory.
      Within the configuration file, you can set the LogLevel which determines the amount
      of logging information written to the log file.  When you set the LogLevel to DEBUG,
      you'll get the full range of logging messages that can be very helpful in pinpointing
      where a problem occured and what information was being processed at the time of the
      anomaly.
      It can be very helpful to run the connector in 'Preview' mode when setting things up for
      the first time.  This allows you to get the connections to Agile Central and Jenkins to
      initialized and validate correctly without posting any build information.  This mode also
      can show you what Jenkins jobs would actually be considered without actually posting
      any build information to Agile Central.

  Known Limitations

      Within AgileCentral there is an entity called a BuildDefinition which for the purposes
      of the Build Connector for Jenkins contains the name of the Jenkins job.  The Jenkins job
      as recorded in a BuildDefinition item is the full URL of the Jenkins job, including any folder
      and view elements.  A BuildDefinition Name is limited to 256 characters.  In the
      event that a Jenkins job has a URL whose length exceeds 256 characters, the behavior of the
      connector is to delete off leading chars on the the job URL such that the result is no longer
      than 256 characters and this resulting string value is used as the BuildDefinition name.  Be aware that
      in some edge cases you might have a Jenkins installation in which this type of modification of the full Job
      URL for various Jenkins Job URLs could end up with the same abbreviated value.  We do not anticipate
      that this will be a common occurence.  If you are in the situation where your Jenkins installation
      contains folder and view names that are fairly long (> 40 chars per folder/view name) with a high
      degree of nesting (> 6 levels) then you may need to alter your connnector config file(s) such that
      jobs whose URL results in a string of > 256 chars are not specified in your config file.

         Example Jenkins Job URL:  http://bigjenkins.stegasaurus.ancient:8080/job/ReallyLongScientificFolderName/.../job/FernCoveredLowlands/job/MickyDinosaur
         Result   .../job/FernCoveredLowlands/job/MickyDinosaur


      The connector will process jobs under named folders, there is not currently the facility to specify an upper level
      folder and process all jobs directly in that folder and in any contained folders in any level of nesting.
      To get jobs in folders to be processed you must specify the folder name in the config file.

      You may have a nested folder structure as illustrated below:
       - upper folder
         -- job 1
         -- lower folder
            -- job 2

       To insure that both job 1 and job 2 are picked up by the connector the Folders section of the config file must look as follows:
          Folders:
            - Folder : upper folder
            - Folder : lower folder

       **** Provisional
       ****  If you have multiple folders in various locations in your Jenkins Job organization that have the same name,
       ****  you must specify each folder using a fully qualified path with ' // ' as a separator between each folder/view level.
         Example:
             Folders:
                 - Folder: Area 51 // Intermediate Stuff // Good Stuff
                 - Folder: Level1 //  Level 2 // Level 3 // Good Stuff


       VCS support: currently connector will process changesets related to builds as long as related job is using a Git repository.
       Some configurations with Subversion have been successful, but there are combinations of Jenkins version, Subversion version and
         Jenkins Subversion plugin version that do not work with our connector due to variances in the json data returned for the
         build information.
         We recommend using a designated VCS connector for Subversion along with Jenkins connector to capture commit/changeSet and build information.
         In those cases set ShowVCSData property in the Jenkins config file to False.


  Appendix A  - Configuration file editing
                --------------------------
     The Agile Central bldeif connector for Jenkins uses a text file in the YAML format.
     For complete information, consult the web page at www.yaml.org/start.html or any of the
     many other fine websites on the subject of YAML.

     For brevity, this document mentions several of the most relevant syntax items
     and covers the 3 sections of a valid YAML config that can be used with the connector.

       1) Use a text editor (not MS Word or Google Doc) to edit the file
       2) NEVER use a tab character in the file, YAML does not allow/recognize tab characters
       3) Save the file in UTF-8 format
       4) Use a monospace font
       5) Be consistent with the number of spaces you use to ident
       6) On a line, the first occurrence of a non-quoted # character indicates a comment,
          the # char and all chars to the right are ignored in processing
       7) Keep the sections in the same order as is present in the sample.yml file
       8) Be aware that the colon char ':' is significant, it separates a key from the value.
       9) Be aware that the dash char '-' is significant, it denotes the start of a list which may
          have 1 or more key value pairs that constitute the list item.
      10) You usually do not have to quote values if they have spaces in them;
          you will have to quote the value if it contains an embedded '#' character

     Here is a skeleton of the template_config.yml file.
     The '|' character denotes the left "edge" of the doc (column 0) and is here for illustration purposes
     only, do not include that character in an actual config file.

     |JenkinsBuildConnector:
     |    AgileCentral:
     |        ...  # several key value pairs are relevant for this section
     |    Jenkins:
     |        ...  # several key value pairs are relevant for this section
     |    Service:
     |        ...  # a few key value pairs relevant for the overall operation of the connector appear in this section


     The AgileCentral "section" specifies values to use to obtain a "connection" with Agile Central.
     The Jenkins      "section" specifies values to use to obtain a "connection" with Jenkins and
                      specify the policies governing what jobs in Jenkins get processed
                      to result in posting of build information to Agile Central
     The Sevice       "section" controls some aspects of the connector behavior on an overall basis.

 a sample file with some explanatory notations
 ---------------------------------------------
 JenkinsBuildConnector:
     AgileCentral:   # all of the possible key value pairs, not all must be used, see the right-hand side
                     # comments for designation as either 'R' required or 'O' optional
         Server:       : rally1.rallydev.com      # R
         Username      : henry5@hauslancaster.uk  # R   if an API_Key entry is used, then this isn't needed
         Password      : 2MuchAngst1415           # R   if an API_Key entry is used, then this isn't needed
         API_Key       : _zzzyyyy234twqwtqwet89y4t38g38y0  # O can use this instead of a Username and Password
         ProxyServer   : wu-tank.smooth.org       # O
         ProxyUser     : jessonbrone              # O
         ProxyPassword : S-e-c*r*E&T321!789       # 0
         Workspace     : My Onliest Workspace     # R  name of the Agile Central Workspace where
                                                  # SCMRepository, Changeset and Build records are written

     Jenkins:        # all of the possible key value pairs, not all must be used, see the right-hand side
                     # comments for designation as either 'R' required or 'O' optional
         Protocol    : http                       # R
         Server      : jenkado.mydomain.com       # R
         Port        : 8080                       # R
         Prefix      :                            # O  for custom Jenkins installation in a non-standard directory
         Username    : validuser                  # R  provide a value when Jenkins requires credentials for access
         Password    : somepasswd                 # R  provide a value when Jenkins requires credentials for access
         API_Token   : 320ca9ae9408d099183aa052ff3199c2  # O can use in place of Password when credentials required
         MaxDepth    : 3                          # O  how many folder levels will be considered, default is three
                                                  #    this will accommodate a scenario like AlphaFolder // BetaFolder // CherryFolder and the jobs in that folder
         FullFolderPath : False                   # O (default is False)  False value indicates Folder and View names only need the leaf name not the full path
                                                  #   When set to True Folder and Value names must use the full path syntax, example:
                                                  #       Some Top Level Folder // some second level folder // target folder name
                                                  #   The path component separator is ' // '.
         AgileCentral_DefaultProject : an Agile Central Project name  # R

         Folders:
             - Folder: a folder name
               include: toaster,microwave,stove   # O use adequate non-ambiguous patterns of job names to include
                                                  #   only those specified. this example would include the jobs
                                                  #   stove-hot, stove-warm, stove-burning
             - Folder: another folder name
               exclude: beta-,post-prod           # O use adequate non-ambiguous patterns of job names to exclude,
                                                  # you do not have to specify the full job name
               AgileCentral_Project: Divison X // National // Engineering

         Views:
             - View  : view name
               AgileCentral_Project: Divison Y // Provincial // Engineering
             - View  : another name
               include: prod-
               exclude: pre-prod

         Jobs:
             - Job   : job name             # only top level jobs can be listed here. Jobs nested in Views or Folders must be listed in respective sections
               AgileCentral_Project: Beta Test for Northeast
             - Job   : another job name     # this job with a unique name could live in some view or folder not at the top level

     Service:
         Preview      : True   # When set to True, the connector shows the items that would be processed
                               #  but doesn't actually post any build information to Agile Central
                               # When you have completed the setup and the connections with AgileCentral and Jenkins
                               # are made successfully, you can change this value to True
         LogLevel     : INFO   # This is the default value, can also be DEBUG, WARN, ERROR. DEBUG is very verbose
         MaxBuilds    : 100    # Use a non-negative integer value. This "limit" pertains to builds for a particular job.

 ------  end of the file ---------------------------------------




