import sys, os
import re
from pyral import Rally, rallyWorkset, RallyRESTAPIError


rally = Rally("rally1.rallydev.com", "yeti@rallydev.com", "Vistabahn", workspace="Alligators BLD Unigrations", project="Static")


############## query TypeDefs for PI types and IDPrefixes


def get_pi_types_info():
    fields    = "ElementName,IDPrefix"
    query = '((Parent.Name = "Portfolio Item") AND (Ordinal >= 0))' # Ordinal >= 0 can be replaced with Creatable = true
    response = rally.get('TypeDefinition', fetch=fields, query=query, order="Ordinal", pagesize=200)
    if response.resultCount:
        return [{"PortfolioItem/%s" % pi.ElementName: pi.IDPrefix} for pi in response]

def get_artifact_types_info(element_name):
    fields = "ElementName,IDPrefix"
    query = 'ElementName = "%s"' % element_name
    art_type = rally.get('TypeDefinition', fetch=fields, query=query, order="Ordinal", instance=True)
    return {art_type.ElementName: art_type.IDPrefix}

def get_all_prefixes():
    pi_type_prefixes = get_pi_types_info()
    art_type_prefixes = pi_type_prefixes[:]
    art_types = ['HierarchicalRequirement', 'Defect', 'DefectSuite', 'TestCase', 'Task']
    for a_type in art_types:
        art_type_prefixes.append(get_artifact_types_info(a_type))
    return art_type_prefixes


def test_get_pi_types_info():
    results = get_pi_types_info()
    print (results)
    assert [result for result in results if 'PortfolioItem/Feature' in result.keys()][0] == {'PortfolioItem/Feature': 'F'}

def test_get_artifact_types_info():
    element_name = 'HierarchicalRequirement'
    art_type_info = get_artifact_types_info(element_name)
    #print (art_type_info)
    assert art_type_info[element_name] == 'US'
    element_name = 'DefectSuite'
    art_type_info = get_artifact_types_info(element_name)
    # print (art_type_info)
    assert art_type_info[element_name] == 'DS'

def test_all_prefixes():
    art_type_prefixes = get_all_prefixes()
    #print (art_type_prefixes)
    assert [atp for atp in art_type_prefixes if 'Defect'                   in atp.keys()][0] == {'Defect'                  :'DE'}
    assert [atp for atp in art_type_prefixes if 'HierarchicalRequirement'  in atp.keys()][0] == {'HierarchicalRequirement' :'US'}
    assert [atp for atp in art_type_prefixes if 'PortfolioItem/Initiative' in atp.keys()][0] == {'PortfolioItem/Initiative':'I'}
    prefixes = [prefix for item in art_type_prefixes for prefix in item.values()]
    #print (prefixes)
    assert prefixes == ['F', 'I', 'US', 'DE', 'DS', 'TC', 'TA']