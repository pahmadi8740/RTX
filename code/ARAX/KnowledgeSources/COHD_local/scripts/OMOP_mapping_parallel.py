import pandas as pd
import pickle
import requests
import os
import multiprocessing

# import internal modules
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
fpath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])

with open(fpath + "/preferred_synonyms_kg2_3_4_with_concepts.pkl", "rb") as file:
    temp = pickle.load(file)

with open(fpath + "/preferred_synonyms_kg2_3_4_with_concepts_new.pkl", "rb") as file:
    synonyms_kg2 = pickle.load(file)

concept_table = pd.read_csv(fpath + "/Athena_tables/ALL_CONCEPT_filtered.txt", sep='\t', index_col=None)
concepts_table_select = concept_table.loc[:, ['concept_id', 'vocabulary_id', 'concept_code']]
concepts_table_select['curie_name'] = concepts_table_select[['vocabulary_id', 'concept_code']].apply(lambda x: str(x[0]).upper() + ":" + str(x[1]).upper(), axis=1)
concepts_table_select.drop(columns=['vocabulary_id', 'concept_code'])
concepts_table_select = concepts_table_select.drop(columns=['vocabulary_id', 'concept_code'])

def change_format(synonym):

    synonym = synonym.upper()

    try:
        vocabulary_id, concept_code = synonym.split(':')
    except ValueError:
        vocabulary_id, concept_code = synonym.split(':')[1:]

    if vocabulary_id == "ICD-10":
        synonym = synonym.replace('ICD-10', 'ICD10')
    elif vocabulary_id == "ICD-9":
        synonym = synonym.replace('ICD-9', 'ICD9CM')
    # elif vocabulary_id == "MESH":
    #     synonym = synonym.replace('MESH', 'MeSH')
    # elif vocabulary_id == "RXNORM":
    #     synonym = synonym.replace('RXNORM', 'RxNorm')
    elif vocabulary_id == "SNOMEDCT":
        synonym = synonym.replace('SNOMEDCT', 'SNOMED')
    elif vocabulary_id == "SNOMEDCT_VET":
        synonym = synonym.replace('SNOMEDCT_VET', 'SNOMED')
    # elif vocabulary_id == "MEDDRA":
    #     synonym = synonym.replace('MEDDRA', 'MedDRA')
    else:
        pass

    return synonym

def get_OMOP(key):

    print(key, flush=True)
    temp = [concepts_table_select.loc[concepts_table_select['curie_name'] == change_format(synonym), 'concept_id'] for synonym in synonyms_kg2[key]['synonyms']]
    concept_ids = [int(item) for item in temp if len(item)!=0]

    return concept_ids


def get_omop_id(key):

    print(key, flush=True)
    synonyms = [change_format(synonym) for synonym in synonyms_kg2[key]['synonyms'] if synonym.split(":")[0] != "OMIM" and synonym.split(":")[0] != "Orphanet" and synonym.split(":")[0] != "CHEMBL.COMPOUND"]
    # synonym = key
    # if synonym.split(":")[0] != "OMIM" and synonym.split(":")[0] != "Orphanet" and synonym.split(":")[0] != "CHEMBL.COMPOUND":
    #     synonyms = [change_format(synonym)]
    # else:
    #     return (key, [])

    if len(synonyms) != 0:
        query_ids = ",".join(synonyms)
        dist = 1
        res = requests.get(f"https://www.ebi.ac.uk/spot/oxo/api/search?format=json&ids={query_ids}&distance={dist}")
        if res.status_code == 200:
            res_curies = [change_format(curie['curie'].upper()) for item in res.json()['_embedded']['searchResults'] if len(item['mappingResponseList']) != 0 for curie in item['mappingResponseList']]
            if any([True if curie_name in res_curies else False for curie_name in concepts_table_select['curie_name']]):
                bool_list = [True if curie_name in res_curies else False for curie_name in concepts_table_select['curie_name']]
                return (key, list(set(concepts_table_select['concept_id'][bool_list])))
            else:
                dist = 2
                res = requests.get(f"https://www.ebi.ac.uk/spot/oxo/api/search?format=json&ids={query_ids}&distance={dist}")
                if res.status_code == 200:
                    res_curies = [change_format(curie['curie'].upper()) for item in res.json()['_embedded']['searchResults'] if len(item['mappingResponseList']) != 0 for curie in item['mappingResponseList']]
                    if any([True if curie_name in res_curies else False for curie_name in concepts_table_select['curie_name']]):
                        bool_list = [True if curie_name in res_curies else False for curie_name in concepts_table_select['curie_name']]
                        return (key, list(set(concepts_table_select['concept_id'][bool_list])))
                    else:
                        dist = 3
                        res = requests.get(f"https://www.ebi.ac.uk/spot/oxo/api/search?format=json&ids={query_ids}&distance={dist}")
                        if res.status_code == 200:
                            res_curies = [change_format(curie['curie'].upper()) for item in res.json()['_embedded']['searchResults'] if len(item['mappingResponseList']) != 0 for curie in item['mappingResponseList']]
                            if any([True if curie_name in res_curies else False for curie_name in concepts_table_select['curie_name']]):
                                bool_list = [True if curie_name in res_curies else False for curie_name in concepts_table_select['curie_name']]
                                return (key, list(set(concepts_table_select['concept_id'][bool_list])))
                            else:
                                return (key, [])
                        else:
                            print(f"{key}\tError {res.status_code}: https://www.ebi.ac.uk/spot/oxo/api/search?format=json&ids={query_ids}&distance={dist}", flush=True)
                            return (key, [])
                else:
                    print(f"{key}\tError {res.status_code}: https://www.ebi.ac.uk/spot/oxo/api/search?format=json&ids={query_ids}&distance={dist}", flush=True)
                    return (key, [])
        else:
            print(f"{key}\tError {res.status_code}: https://www.ebi.ac.uk/spot/oxo/api/search?format=json&ids={query_ids}&distance={dist}", flush=True)
            return (key, [])
    else:
        return (key, [])


# query_key = list(synonyms_kg2.keys())
# print(f'Total curies: {len(synonyms_kg2)}', flush=True)

# batch = list(range(0, len(query_key), 200000))
# batch.append(len(query_key))
# print(f'Total batches: {len(batch)-1}', flush=True)

# for i in range(len(batch)):
#     if (i + 1) < len(batch):
#         print(f'Here is batch{i + 1}', flush=True)
#         start = batch[i]
#         end = batch[i + 1]
#         sub_query_key = query_key[start:end]
#         with multiprocessing.Pool(processes=200) as executor:
#             query_res = [elem for elem in executor.map(get_OMOP, sub_query_key)]

#         for key_item in zip(sub_query_key, query_res):
#             key, concept_ids = key_item
#             if len(concept_ids) != 0:
#                 synonyms_kg2[key]['concept_ids'] = concept_ids
#             else:
#                 synonyms_kg2[key]['concept_ids'] = []

#         with open(fpath + "/preferred_synonyms_kg2_3_4_with_concepts.pkl", "wb") as file:
#             pickle.dump(synonyms_kg2, file)


# total_curies = len([key for key in synonyms_kg2 if len(synonyms_kg2[key]['concept_ids']) == 0])
# print(f"Total curies: {total_curies}", flush=True)
total_curies = len([key for key in temp if len(temp[key]['concept_ids']) == 0])
print(f"Total curies: {total_curies}", flush=True)

# query_key = [key for key in synonyms_kg2 if len(synonyms_kg2[key]['concept_ids']) == 0]
query_key = [key for key in temp if len(temp[key]['concept_ids']) == 0]
del temp

batch = list(range(0, len(query_key), 200000))
batch.append(len(query_key))
print(f'Total batches: {len(batch)-1}', flush=True)

# for i in range(len(batch)):
for i in range(2, len(batch)):
    if (i + 1) < len(batch):
        print(f'Here is batch{i + 1}', flush=True)
        start = batch[i]
        end = batch[i + 1]
        sub_query_key = query_key[start:end]
        with multiprocessing.Pool(processes=50) as executor:
            query_res = [elem for elem in executor.map(get_omop_id, sub_query_key)]

        for key_item in query_res:
            key, concept_ids = key_item
            if len(concept_ids) != 0:
                synonyms_kg2[key]['concept_ids'] = concept_ids

        with open(fpath + "/preferred_synonyms_kg2_3_4_with_concepts_new.pkl", "wb") as file:
            pickle.dump(synonyms_kg2, file)
