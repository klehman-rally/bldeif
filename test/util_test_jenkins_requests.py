import util_jenkins_requests as jenkins
import yaml
import re

def read_config(config_file):
    config_file = "config/{}".format(config_file)
    with open(config_file, 'r') as cf:
        content = cf.read()
        conf = yaml.load(content)
    return conf

def construct_jenkins_url(jenk_conf):
    protocol = jenk_conf['Protocol']
    server   = jenk_conf['Server']
    port     = jenk_conf['Port']
    return "%s://%s:%d" % (protocol, server, port)

def get_first_level_job_names():
    config = 'buildorama.yml'
    conf = read_config(config)
    jenk_conf = conf['JenkinsBuildConnector']['Jenkins']
    jenkins_url = construct_jenkins_url(jenk_conf)
    response = jenkins.get_first_level_jobs(jenk_conf, jenkins_url)
    # assert response.status_code == 200
    results = response.json()
    jobs = [value for key, value in results.items() if key == 'jobs'][0]
    test_produced_names = [job['name'] for job in jobs]
    return test_produced_names

def test_delete():
    config   = 'buildorama.yml'
    conf = read_config(config)
    jenk_conf = conf['JenkinsBuildConnector']['Jenkins']
    jenkins_url = construct_jenkins_url(jenk_conf)
    job_name = 'a'
    response = jenkins.delete_job(jenk_conf, jenkins_url, job_name) # e.g. 'http://localhost:8080/job/a/doDelete'
    assert response.status_code == 200

def test_delete_from_folder():
    config = 'buildorama.yml'
    conf = read_config(config)
    jenk_conf = conf['JenkinsBuildConnector']['Jenkins']
    jenkins_url = construct_jenkins_url(jenk_conf)
    job_name = 'a'
    folder_name = 'test_folder'
    response = jenkins.delete_job(jenk_conf, jenkins_url, job_name, folder_name)
    assert response.status_code == 200

def test_delete_pattern():
    print("\ndeleting test produced items...")
    config = 'buildorama.yml'
    conf = read_config(config)
    jenk_conf = conf['JenkinsBuildConnector']['Jenkins']
    jenkins_url = construct_jenkins_url(jenk_conf)
    job_names = get_first_level_job_names()
    #pattern = '\w+{1}\d{10}\.\d{5}'
    pattern = '\d{10,11}\.\d{5,6}$'
    matching_jobs = [job for job in job_names if re.search(pattern, job)]
    for mj in matching_jobs:
        print(mj)
        response = jenkins.delete_job(jenk_conf, jenkins_url, mj)
        assert response.status_code == 200

