"""
gene_sequence_lookup.py

Retrieve nucleotide sequence candidates for a gene using NCBI E-utilities.

Current flow:
- search gene by symbol and organism, or use provided gene_id
- prefer exact gene symbol matches
- fetch gene summary
- fetch linked nucleotide IDs from Gene -> nuccore
- retrieve FASTA for top linked nucleotide records
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import requests


NCBI_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class NucleotideRecord:
    nucleotide_id: str
    accession: Optional[str]
    title: Optional[str]
    fasta: Optional[str]


@dataclass
class GeneSequenceResult:
    query_gene_symbol: Optional[str]
    query_gene_id: Optional[str]
    organism: Optional[str]
    resolved_gene_id: Optional[str]
    resolved_symbol: Optional[str]
    gene_description: Optional[str]
    nucleotide_records: List[NucleotideRecord]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_gene_symbol": self.query_gene_symbol,
            "query_gene_id": self.query_gene_id,
            "organism": self.organism,
            "resolved_gene_id": self.resolved_gene_id,
            "resolved_symbol": self.resolved_symbol,
            "gene_description": self.gene_description,
            "nucleotide_records": [asdict(x) for x in self.nucleotide_records],
        }


def get_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: tuple[int, int] = (10, 45),
    max_retries: int = 3,
) -> Dict[str, Any]:
    last_error = None

    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=timeout,
                headers={"User-Agent": "sequence-tools/1.0"},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            last_error = exc
            print(
                f"[gene_sequence_lookup] attempt {attempt + 1}/{max_retries} failed "
                f"for {url}: {exc}"
            )
            time.sleep(1.5 * (attempt + 1))

    print(f"[gene_sequence_lookup] FINAL FAIL for {url}: {last_error}")
    return {}


def get_text(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: tuple[int, int] = (10, 45),
    max_retries: int = 3,
) -> str:
    last_error = None

    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=timeout,
                headers={"User-Agent": "sequence-tools/1.0"},
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as exc:
            last_error = exc
            print(
                f"[gene_sequence_lookup] attempt {attempt + 1}/{max_retries} failed "
                f"for {url}: {exc}"
            )
            time.sleep(1.5 * (attempt + 1))

    print(f"[gene_sequence_lookup] FINAL FAIL for {url}: {last_error}")
    return ""


class GeneSequenceLookup:
    def search_gene_ids(
        self,
        gene_symbol: str,
        organism: Optional[str] = None,
        retmax: int = 10,
    ) -> List[str]:
        """
        Search NCBI Gene with a stricter query that prefers exact official symbols.
        Falls back to a looser search if needed.
        """
        symbol = gene_symbol.strip()

        strict_term = f'{symbol}[Gene Name]'
        if organism:
            strict_term += f' AND "{organism}"[Organism]'

        data = get_json(
            f"{NCBI_EUTILS_BASE}/esearch.fcgi",
            {
                "db": "gene",
                "term": strict_term,
                "retmode": "json",
                "retmax": retmax,
            },
        )
        ids = data.get("esearchresult", {}).get("idlist", [])

        if ids:
            return ids

        fallback_term = symbol
        if organism:
            fallback_term += f' AND "{organism}"[Organism]'

        data = get_json(
            f"{NCBI_EUTILS_BASE}/esearch.fcgi",
            {
                "db": "gene",
                "term": fallback_term,
                "retmode": "json",
                "retmax": retmax,
            },
        )
        return data.get("esearchresult", {}).get("idlist", [])

    def gene_summaries(self, gene_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        if not gene_ids:
            return {}

        data = get_json(
            f"{NCBI_EUTILS_BASE}/esummary.fcgi",
            {
                "db": "gene",
                "id": ",".join(gene_ids),
                "retmode": "json",
            },
        )

        result_block = data.get("result", {})
        summaries: Dict[str, Dict[str, Any]] = {}
        for gene_id in gene_ids:
            summaries[gene_id] = result_block.get(gene_id, {})
        return summaries

    def choose_best_gene_id(
        self,
        gene_ids: List[str],
        gene_symbol: Optional[str],
    ) -> Optional[str]:
        """
        Choose the best gene ID by exact symbol match if possible.
        Otherwise return the first result.
        """
        if not gene_ids:
            return None

        if not gene_symbol:
            return gene_ids[0]

        summaries = self.gene_summaries(gene_ids)
        requested = gene_symbol.strip().upper()

        # First pass: exact official symbol match
        for gene_id in gene_ids:
            record = summaries.get(gene_id, {})
            symbol = record.get("name")
            if symbol and symbol.strip().upper() == requested:
                return gene_id

        # Second pass: substring match
        for gene_id in gene_ids:
            record = summaries.get(gene_id, {})
            symbol = record.get("name")
            if symbol and requested in symbol.strip().upper():
                return gene_id

        return gene_ids[0]

    def gene_summary(self, gene_id: str) -> Dict[str, Any]:
        data = get_json(
            f"{NCBI_EUTILS_BASE}/esummary.fcgi",
            {
                "db": "gene",
                "id": gene_id,
                "retmode": "json",
            },
        )
        return data.get("result", {}).get(gene_id, {})

    def linked_nuccore_ids(self, gene_id: str, max_ids: int = 5) -> List[str]:
        data = get_json(
            f"{NCBI_EUTILS_BASE}/elink.fcgi",
            {
                "dbfrom": "gene",
                "db": "nuccore",
                "id": gene_id,
                "retmode": "json",
            },
        )

        linksets = data.get("linksets", [])
        if not linksets:
            return []

        nuccore_ids: List[str] = []
        for linkset in linksets:
            for db_linkset in linkset.get("linksetdbs", []):
                for linked_id in db_linkset.get("links", []):
                    if linked_id not in nuccore_ids:
                        nuccore_ids.append(linked_id)

        return nuccore_ids[:max_ids]

    def nucleotide_summary(self, nucleotide_id: str) -> Dict[str, Any]:
        data = get_json(
            f"{NCBI_EUTILS_BASE}/esummary.fcgi",
            {
                "db": "nuccore",
                "id": nucleotide_id,
                "retmode": "json",
            },
        )
        return data.get("result", {}).get(nucleotide_id, {})

    def fetch_fasta(self, nucleotide_id: str) -> str:
        return get_text(
            f"{NCBI_EUTILS_BASE}/efetch.fcgi",
            {
                "db": "nuccore",
                "id": nucleotide_id,
                "rettype": "fasta",
                "retmode": "text",
            },
        )

    def run(
        self,
        gene_symbol: Optional[str] = None,
        gene_id: Optional[str] = None,
        organism: Optional[str] = None,
        max_nucleotide_records: int = 3,
        include_fasta: bool = True,
    ) -> GeneSequenceResult:
        resolved_gene_id = gene_id
        query_gene_symbol = gene_symbol
        query_gene_id = gene_id

        if not resolved_gene_id:
            if not gene_symbol:
                return GeneSequenceResult(
                    query_gene_symbol=None,
                    query_gene_id=None,
                    organism=organism,
                    resolved_gene_id=None,
                    resolved_symbol=None,
                    gene_description=None,
                    nucleotide_records=[],
                )

            candidate_gene_ids = self.search_gene_ids(
                gene_symbol=gene_symbol,
                organism=organism,
                retmax=10,
            )

            if not candidate_gene_ids:
                return GeneSequenceResult(
                    query_gene_symbol=query_gene_symbol,
                    query_gene_id=query_gene_id,
                    organism=organism,
                    resolved_gene_id=None,
                    resolved_symbol=None,
                    gene_description=None,
                    nucleotide_records=[],
                )

            resolved_gene_id = self.choose_best_gene_id(
                gene_ids=candidate_gene_ids,
                gene_symbol=gene_symbol,
            )

        if not resolved_gene_id:
            return GeneSequenceResult(
                query_gene_symbol=query_gene_symbol,
                query_gene_id=query_gene_id,
                organism=organism,
                resolved_gene_id=None,
                resolved_symbol=None,
                gene_description=None,
                nucleotide_records=[],
            )

        summary = self.gene_summary(resolved_gene_id)
        resolved_symbol = summary.get("name")
        gene_description = summary.get("description")

        if gene_symbol and resolved_symbol:
            if resolved_symbol.strip().upper() != gene_symbol.strip().upper():
                print(
                    f"[gene_sequence_lookup] warning: requested symbol '{gene_symbol}' "
                    f"but resolved to '{resolved_symbol}' (gene_id={resolved_gene_id})"
                )

        nuccore_ids = self.linked_nuccore_ids(
            resolved_gene_id,
            max_ids=max_nucleotide_records,
        )

        nucleotide_records: List[NucleotideRecord] = []
        for nuccore_id in nuccore_ids:
            nuccore_summary = self.nucleotide_summary(nuccore_id)

            accession = (
                nuccore_summary.get("caption")
                or nuccore_summary.get("accessionversion")
                or nuccore_summary.get("title")
            )
            title = nuccore_summary.get("title")

            fasta = self.fetch_fasta(nuccore_id) if include_fasta else None

            nucleotide_records.append(
                NucleotideRecord(
                    nucleotide_id=nuccore_id,
                    accession=accession,
                    title=title,
                    fasta=fasta,
                )
            )
            time.sleep(0.2)

        return GeneSequenceResult(
            query_gene_symbol=query_gene_symbol,
            query_gene_id=query_gene_id,
            organism=organism,
            resolved_gene_id=resolved_gene_id,
            resolved_symbol=resolved_symbol,
            gene_description=gene_description,
            nucleotide_records=nucleotide_records,
        )