"""
Semantic Gene Search MCP tool.

Natural language biology query -> GO terms -> optional NCBI metadata
"""

from modules.semantic_tools.semantic_wrapper import SemanticGeneWrapper


class SemanticGeneSearch:
    """
    Description:
        Search for biology concepts using a natural-language query by mapping
        the query to Gene Ontology terms, with optional exploratory NCBI metadata.

    Input:
        query (str): Natural-language biology query, e.g.
                     "genes related to oxidative stress in yeast"

    Output:
        dict: Structured result containing:
              - parsed_query
              - go_terms
              - genes
              - ncbi_records
    """

    def initiate(self) -> None:
        self.wrapper = SemanticGeneWrapper()

    def run(
        self,
        query: str,
    ) -> dict:
        result = self.wrapper.run(query=query)
        return result.to_dict()


_instance = SemanticGeneSearch()
_instance.initiate()
semantic_gene_search = _instance.run