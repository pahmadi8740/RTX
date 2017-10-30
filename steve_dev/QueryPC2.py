import requests
import json
import sys

class QueryPC2:

    API_BASE_URL='http://www.pathwaycommons.org/pc2'
    
    def send_query_get(self, handler, url_suffix):
        res = requests.get(QueryPC2.API_BASE_URL + "/" + handler + "?" + url_suffix)
        assert 200==res.status_code
        return res
                           
    def uniprot_id_to_reactome_pathways(self, uniprot_id):
        res = self.send_query_get("search.json",
                                  "q=" + uniprot_id + "&type=pathway")
        res_dict = res.json()
        search_hits = res_dict["searchHit"]
        pathway_list = [item.split("http://identifiers.org/reactome/")[1] for i in range(0, len(search_hits)) for item in search_hits[i]["pathway"]]
        return set(pathway_list)

    def test():
        qp = QueryPC2()
        print(qp.uniprot_id_to_reactome_pathways("P68871"))

if "--test" in set(sys.argv):
    QueryPC2.test()

        
        
    
