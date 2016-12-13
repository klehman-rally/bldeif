
############## query TypeDefs for PI types and IDPrefixes


def get_pi_types_info(agicen):
    fields    = "ElementName,IDPrefix"
    query = '((Parent.Name = "Portfolio Item") AND (Ordinal >= 0))' # Ordinal >= 0 can be replaced with Creatable = true
    response = agicen.get('TypeDefinition', fetch=fields, query=query, order="Ordinal", pagesize=200)
    if response.resultCount:
        return [{"PortfolioItem/%s" % pi.ElementName: pi.IDPrefix} for pi in response]

def get_artifact_types_info(agicen, element_name):
    fields = "ElementName,IDPrefix"
    query = 'ElementName = "%s"' % element_name
    art_type = agicen.get('TypeDefinition', fetch=fields, query=query, order="Ordinal", instance=True)
    return {art_type.ElementName: art_type.IDPrefix}

def get_all_prefixes(agicen):
    pi_type_prefixes = get_pi_types_info(agicen)
    art_type_prefixes = pi_type_prefixes[:]
    art_types = ['HierarchicalRequirement', 'Defect', 'DefectSuite', 'TestCase', 'Task']
    for a_type in art_types:
        art_type_prefixes.append(get_artifact_types_info(agicen, a_type))
    return art_type_prefixes


