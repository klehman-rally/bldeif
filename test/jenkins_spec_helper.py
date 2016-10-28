import sys
import requests
import json

job_config = """<?xml version='1.0' encoding='UTF-8'?>

<project>

  <actions/>

  <description></description>

  <keepDependencies>false</keepDependencies>

  <properties>

    <hudson.model.ParametersDefinitionProperty>

      <parameterDefinitions>

        <hudson.model.StringParameterDefinition>

          <name>BAR</name>

          <description></description>

          <defaultValue>vagrancy</defaultValue>

        </hudson.model.StringParameterDefinition>

      </parameterDefinitions>

    </hudson.model.ParametersDefinitionProperty>

  </properties>

  <scm class="hudson.scm.NullSCM"/>

  <canRoam>true</canRoam>

  <disabled>false</disabled>

  <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>

  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>

  <triggers/>

  <concurrentBuild>false</concurrentBuild>

  <builders>

    <hudson.tasks.Shell>

      <command>echo the value of bar is $BAR</command>

    </hudson.tasks.Shell>

  </builders>

  <publishers/>

  <buildWrappers/>

</project>"""

# JENKINS_URL = "http://int-win7bldmstr.f4tech.com:8080"
# VIEW        = "/view/Fluffy%20Donuts"

# def create_job(job_name):
#     headers = {'Content-Type':'application/xml'}
#     url = "{}{}/createItem?name={}".format(JENKINS_URL,VIEW,job_name)
#     r = requests.post(url,data=job_config, headers=headers)
#     return r


def construct_jenkins_url(jenk_conf):
    protocol = jenk_conf['Protocol']
    server   = jenk_conf['Server']
    port     = jenk_conf['Port']
    return "%s://%s:%d" % (protocol, server, port)


def create_job(jenkins, job_name, view=None, folder=None):
    headers = {'Content-Type':'application/xml'}
    url = "{}{}/createItem?name={}".format(jenkins,view,job_name)
    r = requests.post(url,data=job_config, headers=headers)
    return r


# def delete_job(job_name):
#     url = "{}/job/{}/doDelete".format(JENKINS_URL,job_name)
#     r = requests.post(url)
#     return r

def delete_job(jenkins, job_name):
    url = "{}/job/{}/doDelete".format(jenkins,job_name)
    r = requests.post(url)
    return r

# def build(job_name):
#     headers = {'Content-Type': 'application/json'}
#     param_k = 'BAR'
#     param_v = 'noodlesz'
#     url = "{}/job/{}/buildWithParameters?{}={}".format(JENKINS_URL, job_name, param_k, param_v )
#     r = requests.post(url, headers=headers)
#     return r

def build(jenkins, job_name):
    headers = {'Content-Type': 'application/json'}
    param_k = 'BAR'
    param_v = 'noodlesz'
    url = "{}/job/{}/buildWithParameters?{}={}".format(jenkins, job_name, param_k, param_v)
    r = requests.post(url, headers=headers)
    return r

# def bad_build_attempts(job_name):
#     parameter = {'parameter':[{'name':'BAR','value':'fukabane'}]}
#     url = "{}/job/{}/buildWithParameters".format(JENKINS_URL, job_name)
#     r = requests.post(url, data=parameter, headers=headers)
#     return r

