"""
go_term_to_genes.py

Retrieve genes associated with a GO term, with optional organism filtering.

Current strategy:
- Uses NCBI Gene search as a practical fallback:
    GO term label + organism -> gene summaries
- Designed so you can later swap in a stronger annotation source
  without changing the MCP tool interface.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import requests


NCBI_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class GeneHit:
    gene_id: str
    symbol: Optional[str]
    description: Optional[str]
    organism: Optional[str]


@dataclass
class LookupResult:
    go_id: str
    go_label: str
    organism: Optional[str]
    genes: List[GeneHit]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "go_id": self.go_id,
            "go_label": self.go_label,
            "organism": self.organism,
            "genes": [asdict(g) for g in self.genes],
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
                headers={"User-Agent": "annotation-tools/1.0"},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            last_error = exc
            print(
                f"[go_term_to_genes] attempt {attempt + 1}/{max_retries} failed "
                f"for {url}: {exc}"
            )
            time.sleep(1.5 * (attempt + 1))

    print(f"[go_term_to_genes] FINAL FAIL for {url}: {last_error}")
    return {}


class GOTermGeneLookup:
    def search_gene_ids(
        self,
        go_label: str,
        organism: Optional[str] = None,
        retmax: int = 10,
    ) -> List[str]:
        query = go_label
        if organism:
            query += f' AND "{organism}"[Organism]'

        data = get_json(
            f"{NCBI_EUTILS_BASE}/esearch.fcgi",
            {
                "db": "gene",
                "term": query,
                "retmode": "json",
                "retmax": retmax,
            },
        )

        return data.get("esearchresult", {}).get("idlist", [])

    def summarize_gene_ids(self, gene_ids: List[str]) -> List[GeneHit]:
        if not gene_ids:
            return []

        data = get_json(
            f"{NCBI_EUTILS_BASE}/esummary.fcgi",
            {
                "db": "gene",
                "id": ",".join(gene_ids),
                "retmode": "json",
            },
        )

        result_block = data.get("result", {})
        genes: List[GeneHit] = []

        for gene_id in gene_ids:
            record = result_block.get(gene_id, {})
            organism_name = None
            org_obj = record.get("organism")
            if isinstance(org_obj, dict):
                organism_name = org_obj.get("scientificname")

            genes.append(
                GeneHit(
                    gene_id=gene_id,
                    symbol=record.get("name"),
                    description=record.get("description"),
                    organism=organism_name,
                )
            )

        return genes

    def run(
        self,
        go_id: str,
        go_label: str,
        organism: Optional[str] = None,
        max_genes: int = 10,
    ) -> LookupResult:
        gene_ids = self.search_gene_ids(go_label=go_label, organism=organism, retmax=max_genes)
        genes = self.summarize_gene_ids(gene_ids)

        return LookupResult(
            go_id=go_id,
            go_label=go_label,
            organism=organism,
            genes=genes,
        )