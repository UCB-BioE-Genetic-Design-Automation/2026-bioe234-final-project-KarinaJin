"""
semantic_wrapper.py

Semantic wrapper for gene discovery using:
- OLS4 for GO term search
- NCBI Gene API for metadata enrichment

Pipeline:
Natural language -> OLS4 GO term search -> NCBI metadata
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import requests


OLS4_SEARCH_URL = "https://www.ebi.ac.uk/ols4/api/search"
NCBI_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class ParsedQuery:
    raw_query: str
    organism: Optional[str]
    keywords: List[str]
    ontology_terms: List[str]


@dataclass
class GOTerm:
    go_id: str
    label: str
    definition: Optional[str] = None


@dataclass
class GeneAnnotation:
    gene_id: str
    symbol: str
    taxon: Optional[str]
    evidence: Optional[str]
    source: Optional[str]
    go_id: str
    go_label: Optional[str]


@dataclass
class NCBIGene:
    gene_id: str
    symbol: Optional[str]
    description: Optional[str]
    organism: Optional[str]


@dataclass
class Result:
    parsed_query: ParsedQuery
    go_terms: List[GOTerm]
    genes: List[GeneAnnotation]
    ncbi_records: List[NCBIGene]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parsed_query": asdict(self.parsed_query),
            "go_terms": [asdict(x) for x in self.go_terms],
            "genes": [asdict(x) for x in self.genes],
            "ncbi_records": [asdict(x) for x in self.ncbi_records],
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
                headers={"User-Agent": "semantic-wrapper/1.0"},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            last_error = exc
            print(
                f"[semantic_wrapper] attempt {attempt + 1}/{max_retries} "
                f"failed for {url}: {exc}"
            )
            time.sleep(1.5 * (attempt + 1))

    print(f"[semantic_wrapper] FINAL FAIL for {url}: {last_error}")
    return {}


ORGANISMS = {
    "yeast": "Saccharomyces cerevisiae",
    "human": "Homo sapiens",
    "mouse": "Mus musculus",
    "ecoli": "Escherichia coli",
    "e. coli": "Escherichia coli",
}


def parse_query(q: str) -> ParsedQuery:
    q_lower = q.lower()

    organism = None
    for key, value in ORGANISMS.items():
        if key in q_lower:
            organism = value
            break

    tokens = re.findall(r"[a-zA-Z]+", q_lower)
    stop = {
        "find", "genes", "gene", "related", "to", "in", "of", "and",
        "for", "associated", "involved", "with", "show", "me", "the"
    }
    keywords = [t for t in tokens if t not in stop]

    ontology_terms: List[str] = []

    if "oxidative" in q_lower and "stress" in q_lower:
        ontology_terms.append("response to oxidative stress")
    elif "dna" in q_lower and "repair" in q_lower:
        ontology_terms.append("DNA repair")
    elif "immune" in q_lower and "response" in q_lower:
        ontology_terms.append("immune response")
    elif "cell" in q_lower and "cycle" in q_lower:
        ontology_terms.append("cell cycle")
    elif keywords:
        ontology_terms.append(" ".join(keywords[:4]))

    return ParsedQuery(
        raw_query=q,
        organism=organism,
        keywords=keywords,
        ontology_terms=ontology_terms,
    )


def search_go(term: str) -> List[GOTerm]:
    data = get_json(
        OLS4_SEARCH_URL,
        params={
            "q": term,
            "ontology": "go",
            "rows": 5,
        },
    )

    docs = data.get("response", {}).get("docs", [])
    results: List[GOTerm] = []
    seen = set()

    for doc in docs:
        go_id = doc.get("obo_id")
        label = doc.get("label")
        description = doc.get("description")

        if isinstance(description, list):
            definition = description[0] if description else None
        else:
            definition = description

        if go_id and label and go_id not in seen:
            seen.add(go_id)
            results.append(
                GOTerm(
                    go_id=go_id,
                    label=label,
                    definition=definition,
                )
            )

    return results


def ncbi_lookup(symbol: str, organism: Optional[str]) -> List[NCBIGene]:
    term = symbol
    if organism:
        term += f' AND "{organism}"[Organism]'

    search_data = get_json(
        f"{NCBI_EUTILS_BASE}/esearch.fcgi",
        {"db": "gene", "term": term, "retmode": "json", "retmax": 3},
    )

    ids = search_data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    summary_data = get_json(
        f"{NCBI_EUTILS_BASE}/esummary.fcgi",
        {"db": "gene", "id": ",".join(ids), "retmode": "json"},
    )

    results: List[NCBIGene] = []
    result_block = summary_data.get("result", {})

    for gene_id in ids:
        record = result_block.get(gene_id, {})
        organism_name = None
        org_obj = record.get("organism")
        if isinstance(org_obj, dict):
            organism_name = org_obj.get("scientificname")

        results.append(
            NCBIGene(
                gene_id=gene_id,
                symbol=record.get("name"),
                description=record.get("description"),
                organism=organism_name,
            )
        )

    return results


class SemanticGeneWrapper:
    def run(self, query: str) -> Result:
        parsed = parse_query(query)

        go_terms: List[GOTerm] = []
        for term in parsed.ontology_terms:
            go_terms.extend(search_go(term))
            time.sleep(0.2)

        # No direct gene retrieval yet in this fallback version.
        # It gets ontology terms reliably first, which is the part that is failing now.
        genes: List[GeneAnnotation] = []

        ncbi_records: List[NCBIGene] = []
        # Optional weak enrichment: search NCBI using the ontology phrase itself
        for phrase in parsed.ontology_terms[:1]:
            ncbi_records.extend(ncbi_lookup(phrase, parsed.organism))
            time.sleep(0.2)

        return Result(
            parsed_query=parsed,
            go_terms=go_terms,
            genes=genes,
            ncbi_records=ncbi_records,
        )