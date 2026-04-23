"""
MCP tool for retrieving nucleotide sequence candidates from a gene symbol or gene ID.
"""

from modules.sequence_tools.gene_sequence_lookup import GeneSequenceLookup


class GeneSequenceLookupTool:
    """
    Description:
        Retrieve nucleotide sequence candidates for a gene symbol or NCBI Gene ID,
        optionally filtered by organism.

    Inputs:
        gene_symbol (str, optional): Gene symbol, e.g. YAP1
        gene_id (str, optional): NCBI Gene ID, e.g. 855005
        organism (str, optional): Organism name, e.g. Saccharomyces cerevisiae
        max_nucleotide_records (int, optional): Max linked nucleotide entries to fetch
        include_fasta (bool, optional): Whether to fetch FASTA text

    Output:
        dict with resolved gene and linked nucleotide sequence records
    """

    def initiate(self) -> None:
        self.lookup = GeneSequenceLookup()

    def run(
        self,
        gene_symbol: str | None = None,
        gene_id: str | None = None,
        organism: str | None = None,
        max_nucleotide_records: int = 3,
        include_fasta: bool = True,
    ) -> dict:
        result = self.lookup.run(
            gene_symbol=gene_symbol,
            gene_id=gene_id,
            organism=organism,
            max_nucleotide_records=max_nucleotide_records,
            include_fasta=include_fasta,
        )
        return result.to_dict()


_instance = GeneSequenceLookupTool()
_instance.initiate()
gene_sequence_lookup_tool = _instance.run