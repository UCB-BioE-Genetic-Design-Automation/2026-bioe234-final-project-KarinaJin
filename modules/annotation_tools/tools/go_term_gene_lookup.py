"""
MCP tool for GO-term-based gene lookup.
"""

from modules.annotation_tools.go_term_to_genes import GOTermGeneLookup


class GOTermGeneLookupTool:
    """
    Description:
        Retrieve genes related to a GO term label, optionally filtered by organism.

    Inputs:
        go_id (str): GO identifier, e.g. GO:0006979
        go_label (str): GO term label, e.g. "response to oxidative stress"
        organism (str, optional): Organism name, e.g. "Saccharomyces cerevisiae"
        max_genes (int, optional): Maximum number of genes to return

    Output:
        dict with go_id, go_label, organism, and gene list
    """

    def initiate(self) -> None:
        self.lookup = GOTermGeneLookup()

    def run(
        self,
        go_id: str,
        go_label: str,
        organism: str | None = None,
        max_genes: int = 10,
    ) -> dict:
        result = self.lookup.run(
            go_id=go_id,
            go_label=go_label,
            organism=organism,
            max_genes=max_genes,
        )
        return result.to_dict()


_instance = GOTermGeneLookupTool()
_instance.initiate()
go_term_gene_lookup = _instance.run