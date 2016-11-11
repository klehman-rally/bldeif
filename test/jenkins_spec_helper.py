import sys
import requests
import json

job_config = """<?xml version='1.0' encoding='UTF-8'?>
<project>
  <description></description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <scm class="hudson.scm.NullSCM"/>
  <canRoam>true</canRoam>
  <disabled>false</disabled>
  <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
  <triggers/>
  <concurrentBuild>false</concurrentBuild>
  <builders>
    <hudson.tasks.Shell>
      <command>echo &quot;the end is near&quot;</command>
    </hudson.tasks.Shell>
  </builders>
  <publishers/>
  <buildWrappers/>
</project>"""

'''
These are URL examples to create jobs in a folder and in a view:

curl -XPOST 'http://jenkins:e008e30c73820b7eeb097ae1f1fa1dd8@tiema03-u183073.ca.com:8080/job/Parkour/createItem?name=black-swan-2' --data-binary @bluestem.xml -H "Content-Type:text/xml"

curl -XPOST 'http://jenkins:e008e30c73820b7eeb097ae1f1fa1dd8@tiema03-u183073.ca.com:8080/view/Prairie/createItem?name=black-swan-3' --data-binary @bluestem.xml -H "Content-Type:text/xml"

no folder, no job

curl -XPOST 'http://jenkins:e008e30c73820b7eeb097ae1f1fa1dd8@tiema03-u183073.ca.com:8080/view/All/createItem?name=black-swan-4' --data-binary @bluestem.xml -H "Content-Type:text/xml"

'''


def construct_jenkins_url(jenk_conf):
    protocol = jenk_conf['Protocol']
    server   = jenk_conf['Server']
    port     = jenk_conf['Port']
    return "%s://%s:%d" % (protocol, server, port)


def create_job(config, jenkins, job_name, view='All', folder=None):
    headers = {'Content-Type':'application/xml'}
    if not folder:
        url = "{}/view/{}/createItem?name={}".format(jenkins, view, job_name)
    else:
        url = "{}/job/{}/createItem?name={}".format(jenkins, folder, job_name)
    r = requests.post(url, auth=(config['Username'], config['API_Token']), data=job_config, headers=headers)
    return r

def create_folder(config, jenkins, folder_name, outer_folder=None):
    headers = {'Content-Type': 'application/json'}
    folder_class = "com.cloudbees.hudson.plugins.folder.Folder"
    if not outer_folder:
        url = "{}/createItem?name={}&mode={}&from=".format(jenkins, folder_name, folder_class)
    else:
        url = "{}/job/{}/createItem?name={}&mode={}&from=".format(jenkins, outer_folder, folder_name, folder_class)
    r = requests.post(url, auth=(config['Username'], config['API_Token']), headers=headers)
    return r


def delete_job(config, jenkins, job_name, folder=None):
    if not folder:
        url = "{}/job/{}/doDelete".format(jenkins, job_name)
    else:
        url = "{}/job/{}/job/{}/doDelete".format(jenkins, folder, job_name)
    #url = "{}/job/{}/doDelete".format(jenkins,job_name)
    r = requests.post(url, auth=(config['Username'], config['API_Token']))
    return r


def build(config, jenkins, job_name, view="All", folder=None ):
    headers = {'Content-Type': 'application/json'}
    #param_k = 'BAR'
    #param_v = 'noodlesz'
    #url = "{}/job/{}/buildWithParameters?{}={}".format(jenkins, job_name, param_k, param_v)
    #url = "{}/job/{}/build".format(jenkins, job_name)
    #r = requests.post(url, auth=(config['Username'], config['API_Token']), headers=headers)
    if not folder:
        url = "{}/job/{}/build".format(jenkins, job_name)
    else:
        url = "{}/job/{}/job/{}/build".format(jenkins, folder, job_name)
    r = requests.post(url, auth=(config['Username'], config['API_Token']), headers=headers)
    return r

# def bad_build_attempts(job_name):
#     parameter = {'parameter':[{'name':'BAR','value':'fukabane'}]}
#     url = "{}/job/{}/buildWithParameters".format(JENKINS_URL, job_name)
#     r = requests.post(url, data=parameter, headers=headers)
#     return r

