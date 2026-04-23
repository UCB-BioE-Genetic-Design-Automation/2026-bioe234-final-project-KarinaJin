"""
MCP tool for resolving a gene to exact genomic locus coordinates and sequence.
"""

from modules.locus_tools.gene_locus_lookup import GeneLocusLookup


class GeneLocusLookupTool:
    """
    Description:
        Resolve a gene symbol or NCBI Gene ID to genomic locus coordinates and
        optionally fetch the locus FASTA sequence.

    Inputs:
        gene_symbol (str, optional): Gene symbol, e.g. YAP1
        gene_id (str, optional): NCBI Gene ID, e.g. 855005
        organism (str, optional): Organism name, e.g. Saccharomyces cerevisiae
        max_loci (int, optional): Maximum number of genomic loci to return
        include_fasta (bool, optional): Whether to fetch locus FASTA

    Output:
        dict with resolved gene metadata and genomic locus records
    """

    def initiate(self) -> None:
        self.lookup = GeneLocusLookup()

    def run(
        self,
        gene_symbol: str | None = None,
        gene_id: str | None = None,
        organism: str | None = None,
        max_loci: int = 3,
        include_fasta: bool = True,
    ) -> dict:
        result = self.lookup.run(
            gene_symbol=gene_symbol,
            gene_id=gene_id,
            organism=organism,
            max_loci=max_loci,
            include_fasta=include_fasta,
        )
        return result.to_dict()


_instance = GeneLocusLookupTool()
_instance.initiate()
gene_locus_lookup_tool = _instance.run