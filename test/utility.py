import sys, os
import re
from pyral import Rally, rallyWorkset, RallyRESTAPIError


rally = Rally("rally1.rallydev.com", "yeti@rallydev.com", "Vistabahn", workspace="Alligators BLD Unigrations", project="Static")


def find_scm_repo(name):
    fields = "ObjectID"
    query = '(Name = "{}")'.format(name)
    scm_repos = []
    response = rally.get('SCMRepository', fetch=fields, query=query, order="Name", project=None, pagesize=20, limit=20)
    if response.resultCount > 0:
        for item in response:
            scm_repos.append(item)
        return scm_repos[0]
    return None

def create_scm_repo(name, scm_type):
    repo = find_scm_repo(name)
    if repo:
        print ("SCMRepository %s already exists" %name)
        return repo

    scm_repo_payload = {
        'Name'    : name,
        'SCMType' : scm_type
    }
    try:
        scm_repo = rally.create('SCMRepository', scm_repo_payload)
        print("Created SCMRepository %s" % scm_repo.ObjectID)
    except RallyRESTAPIError as msg:
        sys.stderr.write('ERROR: %s \n' % msg)
        sys.exit(4)

    return scm_repo

def delete_scm_repo(name):
    result = find_scm_repo(name)
    if not result:
        print ("SCMRepository %s does not exists" %name)
        return False
    else:
        delete_changesets_of_scm_repo(name)
        try:
            scm_repo = rally.delete('SCMRepository', result.ObjectID, project=None)
            print("Deleted SCMRepository %s" % result.ObjectID)
        except RallyRESTAPIError as msg:
            sys.stderr.write('ERROR: %s \n' % msg)
            raise
    return True

def get_all_scm_repos():
    fields    = "Name,ObjectID" # REMEMBER: no spaces in the fetch list!!!!
    response = rally.get('SCMRepository', fetch=fields, order="CreationDate", project=None, pagesize=200)
    return response

def bulk_delete_scm_repos():
    scm_repos = get_all_scm_repos()
    if scm_repos.resultCount == 0:
        return False

    for repo in scm_repos:
        print("\n%s: %s" % (repo.Name, repo.ObjectID))
        try:
            print("deleting SCMRepository %s" %repo.Name)
            rally.delete("SCMRepository", repo.ObjectID, "Alligators BLD Unigrations", project=None)
        except Exception as msg:
            print("Problem deleting SCMRepository %s" %repo.Name)
            raise RallyRESTAPIError(msg)

    return True

def get_changesets_of_scm_repo(repo_name):
    fields = "ObjectID"
    query = "(SCMRepository.Name = {})".format(repo_name)
    changesets = []
    response = rally.get('Changeset', fetch=fields, query=query, order="Name", project=None, pagesize=20, limit=20)
    if response.resultCount:
        for item in response:
            changesets.append(item)
        return changesets
    return None


def delete_changesets_of_scm_repo(repo_name):
    changesets = get_changesets_of_scm_repo(repo_name)
    if not changesets:
        return False

    for changeset in changesets:
        print("\n%s: %s" % (changeset.Name, changeset.ObjectID))
        try:
            print("deleting Changeset %s" %changeset.ObjectID)
            rally.delete("Changeset", changeset.ObjectID)
        except Exception as msg:
            print("Problem deleting Changeset %s" %changeset.ObjectID)
            raise RallyRESTAPIError(msg)

    return True

# def get_build_definition(build_def_oid):
#     fields = "Name,ObjectID"
#     query = ("ObjectID = %s" % build_def_oid)
#     response = rally.get('BuildDefinition', fetch=fields, query=query, pagesize=200)
#     return response.next()

def get_build_definition(build_def_name, project='Static'):
    fields = "Name,ObjectID,Project,Builds"
    query = ('Name = "%s"' % build_def_name)
    response = rally.get('BuildDefinition', fetch=fields, query=query, project=project, pagesize=200)
    if response.resultCount == 0:
        return []
    return [item for item in response]

def get_ac_builds(build_def, project='Static'):
    fields = "ObjectID,BuildDefinition,Number,Status"
    query = ("BuildDefinition.ObjectID = %s" %(build_def.ObjectID))
    response = rally.get('Build', fetch=fields, query=query, project=project, pagesize=200)
    return [item for item in response]

def delete_ac_build_definition(build_def):
    try:
        #print("deleting Build Definition %s" % build_def.ObjectID)
        rally.delete("BuildDefinition", build_def.ObjectID)
    except Exception as msg:
        print(msg)
        raise RallyRESTAPIError(msg)


def delete_ac_builds(job_name):
    fields = "Name,ObjectID"
    query = ('Name = "%s"' % job_name)
    response = rally.get('BuildDefinition', fetch=fields, query=query, project=None, pagesize=200)
    for build_def in response:
        builds = get_ac_builds(build_def)
        delete_ac_builds(builds)
        delete_ac_build_definition(build_def)
    return []


def create_change(changeset_ref, path_n_filename):
    change_payload = {
        'Changeset': changeset_ref,
        'PathAndFilename': path_n_filename
    }
    try:
        change = rally.create('Change', change_payload)
        print("Created Change %s" % change.ObjectID)
    except RallyRESTAPIError as msg:
        print(msg)
        raise RallyRESTAPIError(msg)

    return change

def update_changeset(payload):
    try:
        changeset = rally.update('Changeset', payload)
        print("Updated Changeset %s" % changeset.ObjectID)
    except RallyRESTAPIError as msg:
        print(msg)
        raise RallyRESTAPIError(msg)
    return changeset

#def create_changeset(repo_name, timestamp)

########################## tests ###########################################
def test_find_scm_repo():
    name = "/var/lib/jenkins/repos/wombats"
    oid  = 78513572348
    result = find_scm_repo(name)
    assert result.ObjectID == oid

def test_create_duplicate_scm_repo():
    name = '/var/lib/jenkins/repos/wombats'
    scm_type = 'git'
    assert not create_scm_repo(name, scm_type)

def test_create_scm_repo():
    #name = 'foobar-is-dead'
    name = 'wombat'
    scm_type = 'git'
    assert create_scm_repo(name, scm_type)

def test_backslash_in_name():
    name = r'C:\some\local\path'  # created "_refObjectName": "C:\\some\\local\\path"
    scm_type = 'git'
    assert create_scm_repo(name, scm_type)

def test_delete_repo():
    #name = 'foobar'
    #name = 'good/womabat/.git'
    name = 'wombat'
    assert delete_scm_repo(name)

def test_bulk_delete_scm_repos():
    assert bulk_delete_scm_repos()

def test_get_changesets_of_scm_repo():
    scm_repo = "MockBuildsRepo"
    changesets = get_changesets_of_scm_repo(scm_repo)
    assert changesets[0].ObjectID == 71456170320

def test_delete_changesets_of_scm_repo():
    scm_repo = "MockBuildsRepo"
    delete_changesets_of_scm_repo(scm_repo)

def test_delete_scm_repo():
    name = 'beta/wombat/.git'
    delete_scm_repo(name)
    assert not find_scm_repo(name)

def test_create_change():
    changeset_ref = '/changeset/79718865700'
    path_n_file = '/home/n/venison/foobar'
    result = create_change(changeset_ref, path_n_file)
    assert result

def test_update_changeset():
    payload = {
        'ObjectID': 79718865700,
        'Uri'     : 'http://bogus/path'
    }
    result = update_changeset(payload)
    assert result

def test_get_ac_builds():
    build_def = get_build_definition("truculent elk medallions", project="Jenkins")[0]
    builds = get_ac_builds(build_def, project='Jenkins')
    assert len(builds) == 10


################## parsing formatted id from commit message

def extract_fids(message):
    prefixes = ['S', 'US', 'DE', 'TA', 'TC', 'DS', 'TS']
    fid_pattern = r'((%s)\d+)' % '|'.join(prefixes)
    result = re.findall(fid_pattern, message, re.IGNORECASE)
    return [item[0].upper() for item in result]


def test_extract_fids():
    commit_message = "US123, US456 done!"
    assert extract_fids(commit_message) == ['US123', 'US456']
    commit_message = "US123DE4"
    assert extract_fids(commit_message) == ['US123', 'DE4']
    commit_message = "s123, de456 foo666 done!"
    assert extract_fids(commit_message) == ['S123', 'DE456']
    commit_message = "Jojo did [DE543-S123421-TAX123];TC098/DE3412(BA23,S543)"
    assert extract_fids(commit_message) == ['DE543', 'S123421', 'TC098', 'DE3412', 'S543']
    commit_message = "!US123, US456 done!\n adfadsfafTC999[PFI7878]DDE2344"
    assert extract_fids(commit_message) == ['US123', 'US456', 'TC999', 'DE2344']
    commit_message = "<b>US123:</b> done, <b>DE1:</b> fixed"
    assert extract_fids(commit_message) == ['US123', 'DE1']

