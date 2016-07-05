# bldeif

This is the repository for bldeif, a package and driver script(s) that implement a Jenkins to Agile Central Build connector.

## Context

CA Agile Central is the premier agile software development tool providing information and perspectives to those involved 
in software development including product managers, developers, testers, scrum masters and technical support personnel.
Among the entities present in the Agile Central system are BuildDefinition and Build records.  Agile Central is not a 
build "system" but can be populated with Build information that can be related to Changesets and the common work item 
artifacts (Story, Defect, TestCase, Task).  This repository contains code that populates Agile Central Build records
from Jenkins builds for various jobs.  More information on how to view and interpret Build data in Agile Central is 
available from the help pages in Agile Central.

There are various connectors that have been developed for Agile Central ranging from those developed by CA Technologies
to those developed by 3rd parties like independent software vendors and customers.  Most of the connectors deal with 
work items (Story, Task, Defect, TestCase) or version control systems (VCS) like Git, Mercurial, Subversion and TFS.
The connectors developed by CA Technologies use a hub and spoke system which has been dubbed "EIF" for 
Extensible Integration Framework.  The hub comprises code that obtains 2 "spokes" and orchestrates their operation.
A "spoke" is a service element that speaks to one system, like Agile Central or some other work item system or VCS.

bldeif is an initial EIF reference implemention for a an Agile Central Build connector to process builds from a Jenkins system.
There's the hub componentry that checks for, validates and utilizes configuration files that specify the Agile Central 
system and credentials and the Jenkins system and jobs of interest.  There are two "spokes", one for Agile Central and 
one for Jenkins.   The opportunity to swap out a Jenkins spoke for another build system spoke like Travis, Team City,
Bamboo or TFS exists, but they have yet to be written.

## Installation
Clone this repository in a suitable location.
You must have a working Python 2.7.x available in your environment.
```
    git clone https://github.com/klehman-rally/bldeif.git
    cd bldeif
    python setup.py install
```

## Configuration
Configuration of the bldeif connector is done via a YAML file which should be in the config subdirectory.
There is a sample configuration file name `sample.yml` in the config subdir that you can use as a template.
Simply copy it to a file with a name reflecting your intended usage or environment, and edit the file
substituting with values relevant to your situation.

## Operation
Run the connector using the jenaco.py script (or jenaco sym link) and one or more configuration file names.
```
    jenaco project_x 
```

## Troubleshooting
A log is written into the log directory named for the configuration file that is being processed.
You can control the extent of logging by specifying the level in the config file.  Under the 'Service' 
section, modify the LogLevel setting (valid values are ERROR, WARN, INFO, DEBUG).
The log can help you pinpoint problem areas and in some scenarios (typically when logging at DEBUG level)
you can see values being used in the processing.

## Development
You'll need a Python 2.7.x installed, a valid subscription and credentials to CA Agile Central and 
a working Jenkins installation that supports the Jenkins REST API.

## Contributing

## Extensions
This is a reference implementation for Jenkins.  To support a different build systems, you'll need to 
develop a connection spoke for your build system that can support a call to getRecentBuilds (ref_timestamp).
That method needs to return a list of Build items, where a Build item has the following attributes:
```
        job_name
        build number
        result
        timestamp
```

## License
This code is provided as open source under the terms of the [BSD license](http://opensource.org/licenses/BSD-3-Clause).


