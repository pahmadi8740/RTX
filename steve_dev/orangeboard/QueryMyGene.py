import mygene
import functools
import CachedMethods


class QueryMyGene:
    def __init__(self):
        self.mygene_obj = mygene.MyGeneInfo()

    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def convert_gene_symbol_to_uniprot_id(self, gene_symbol):
        res = self.mygene_obj.query('symbol:' + gene_symbol, species='human',
                           fields='uniprot')
        uniprot_id = set()
        if len(res) > 0:
            uniprot_id = set([hit["uniprot"]["Swiss-Prot"] for hit in res["hits"]])
        return uniprot_id

    @CachedMethods.register
    @functools.lru_cache(maxsize=1024, typed=False)
    def convert_uniprot_id_to_gene_symbol(self, uniprot_id):
        res = self.mygene_obj.query('uniprot:' + uniprot_id, species='human',
                           fields='symbol')
        gene_symbol = set()
        if len(res) > 0:
            gene_symbol = set([hit["symbol"] for hit in res["hits"]])
        return gene_symbol
    
    def test():
        mg = QueryMyGene()
        print(mg.convert_gene_symbol_to_uniprot_id("HMOX1"))
        print(mg.convert_uniprot_id_to_gene_symbol("P09601"))
        
if __name__ == '__main__':
    QueryMyGene.test()
