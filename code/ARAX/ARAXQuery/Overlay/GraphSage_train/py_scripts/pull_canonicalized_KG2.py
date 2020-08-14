import sys, os
import pandas as pd
from neo4j import GraphDatabase
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration

output_path = '~/work/RTX/code/reasoningtool/MLDrugRepurposing/Test_graphsage/kg2canonicalized_data/'

## Connect to neo4j database
rtxc = RTXConfiguration()
driver = GraphDatabase.driver("bolt://kg2canonicalized.rtx.ai:7687", auth=(rtxc.neo4j_username, rtxc.neo4j_password))
session = driver.session()

## Pull a dataframe of all of the graph edges
query = 'match (n)-[r]-(m) where m<>n and type(r)<>"contraindicated_for" and type(r)<>"indicated_for" and type(r)<>"treats" and type(r)<>"prevents" and type(r)<>"causes" and type(r)<>"contraindicated_with" and type(r)<>"intent_to_treat" and type(r)<>"disease_responds_to" and type(r)<>"antagonist" and type(r)<>"disrupts" and type(r)<>"has_pharmaceutical_state_of_matter" and type(r)<>"increase" and type(r)<>"has_pharmaceutical_basic_dose_form" and type(r)<>"chemical_or_drug_has_mechanism_of_action" and type(r)<>"contributes_to" and type(r)<>"predisposes_towards" and type(r)<>"regulates_process_to_process" and type(r)<>"positively_regulates_entity_to_entity" and type(r)<>"negatively_regulates_entity_to_entity" with distinct n as node1, m as node2 return node1.id as source, node2.id as target'
res = session.run(query)
KG2_alledges = pd.DataFrame(res.data())
KG2_alledges.to_csv(output_path + 'graph_edges.txt', sep='\t', index=None)

## Pulls a dataframe of all of the graph nodes with category label
query = "match (n) with distinct n.id as id, n.name as name, n.preferred_type as category return id, name, category"
res = session.run(query)
KG2_allnodes_label = pd.DataFrame(res.data())
KG2_allnodes_label = KG2_allnodes_label.iloc[:, [0, 2]]
KG2_allnodes_label.to_csv(output_path + 'graph_nodes_label_remove_name.txt', sep='\t', index=None)

## Pulls a dataframe of all of the graph drug-associated nodes
query = f"match (n:chemical_substance) with distinct n.id as id, n.name as name return id, name union match (n:drug) with distinct n.id as id, n.name as name return id, name"
res = session.run(query)
drugs = pd.DataFrame(res.data())
drugs.to_csv(output_path + 'drugs.txt', sep='\t', index=None)

## Pulls a dataframe of all of the graph disease and phenotype nodes
query = "match (n:phenotypic_feature) with distinct n.id as id, n.name as name return id, name union match (n:disease) with distinct n.id as id, n.name as name return id, name"
res = session.run(query)
diseases = pd.DataFrame(res.data())
diseases.to_csv(output_path + 'diseases.txt', sep='\t', index=None)
