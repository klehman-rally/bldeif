import build_spec_helper   as bsh
from bldeif.agicen_bld_connection import AgileCentralConnection
from bldeif.utils.ac_prefixes import get_all_prefixes, get_artifact_types_info, get_pi_types_info


config_file = 'wombat.yml'
fake_logger = bsh.ActivityLogger('test.log')

conf = {'Server'   : 'rally1.rallydev.com',
        'APIKey'   : '_2QFAQA0wQoSKiORUOsVlMjeQfFr1JkawtItGFHtrtx8',
        'Workspace': 'Alligators BLD Unigrations',
        'Project'  : 'Static'
       }


ac = AgileCentralConnection(conf, fake_logger)
ac.other_name = "Jenkins"
ac.connect()
agicen = ac.agicen

def test_get_pi_types_info():
    results = get_pi_types_info(agicen)
    print (results)
    assert [result for result in results if 'PortfolioItem/Feature' in result.keys()][0] == {'PortfolioItem/Feature': 'F'}

def test_get_artifact_types_info():
    element_name = 'HierarchicalRequirement'
    art_type_info = get_artifact_types_info(agicen, element_name)
    #print (art_type_info)
    assert art_type_info[element_name] == 'US'
    element_name = 'DefectSuite'
    art_type_info = get_artifact_types_info(agicen, element_name)
    # print (art_type_info)
    assert art_type_info[element_name] == 'DS'

def test_all_prefixes():
    art_type_prefixes = get_all_prefixes(agicen)
    #print (art_type_prefixes)
    assert [atp for atp in art_type_prefixes if 'Defect'                   in atp.keys()][0] == {'Defect'                  :'DE'}
    assert [atp for atp in art_type_prefixes if 'HierarchicalRequirement'  in atp.keys()][0] == {'HierarchicalRequirement' :'US'}
    assert [atp for atp in art_type_prefixes if 'PortfolioItem/Initiative' in atp.keys()][0] == {'PortfolioItem/Initiative':'I'}
    prefixes = [prefix for item in art_type_prefixes for prefix in item.values()]
    #print (prefixes)
    assert prefixes == ['F', 'I', 'US', 'DE', 'DS', 'TC', 'TA']