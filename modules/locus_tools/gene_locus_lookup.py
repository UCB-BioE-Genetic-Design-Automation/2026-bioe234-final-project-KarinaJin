"""
gene_locus_lookup.py

Resolve a gene to genomic coordinates and fetch the corresponding locus sequence
using NCBI Gene and NCBI nuccore.

Design notes:
- NCBI Gene docsum GenomicInfo contains ChrAccVer, ChrStart, and ChrStop.
- ChrStart / ChrStop are 0-based in Gene docsums.
- This module converts those to a 1-based inclusive interval for reporting.
- The genomic slice is fetched from nuccore with seq_start / seq_stop using
  the smaller/larger coordinate values.
- If the gene is on the minus strand, we still fetch the genomic region in the
  forward genomic orientation and annotate the strand separately.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import requests


NCBI_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class LocusRecord:
    chr_accession: str
    chr_loc: Optional[str]
    start_0_based: int
    stop_0_based: int
    start_1_based: int
    stop_1_based: int
    strand: str
    exon_count: Optional[int]
    fasta: Optional[str]


@dataclass
class GeneLocusResult:
    query_gene_symbol: Optional[str]
    query_gene_id: Optional[str]
    organism: Optional[str]
    resolved_gene_id: Optional[str]
    resolved_symbol: Optional[str]
    gene_description: Optional[str]
    loci: List[LocusRecord]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_gene_symbol": self.query_gene_symbol,
            "query_gene_id": self.query_gene_id,
            "organism": self.organism,
            "resolved_gene_id": self.resolved_gene_id,
            "resolved_symbol": self.resolved_symbol,
            "gene_description": self.gene_description,
            "loci": [asdict(x) for x in self.loci],
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
                headers={"User-Agent": "locus-tools/1.0"},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            last_error = exc
            print(
                f"[gene_locus_lookup] attempt {attempt + 1}/{max_retries} failed "
                f"for {url}: {exc}"
            )
            time.sleep(1.5 * (attempt + 1))

    print(f"[gene_locus_lookup] FINAL FAIL for {url}: {last_error}")
    return {}


def get_text(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: tuple[int, int] = (10, 60),
    max_retries: int = 3,
) -> str:
    last_error = None

    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=timeout,
                headers={"User-Agent": "locus-tools/1.0"},
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as exc:
            last_error = exc
            print(
                f"[gene_locus_lookup] attempt {attempt + 1}/{max_retries} failed "
                f"for {url}: {exc}"
            )
            time.sleep(1.5 * (attempt + 1))

    print(f"[gene_locus_lookup] FINAL FAIL for {url}: {last_error}")
    return ""


class GeneLocusLookup:
    def search_gene_ids(
        self,
        gene_symbol: str,
        organism: Optional[str] = None,
        retmax: int = 10,
    ) -> List[str]:
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
        return {gene_id: result_block.get(gene_id, {}) for gene_id in gene_ids}

    def choose_best_gene_id(
        self,
        gene_ids: List[str],
        gene_symbol: Optional[str],
    ) -> Optional[str]:
        if not gene_ids:
            return None
        if not gene_symbol:
            return gene_ids[0]

        summaries = self.gene_summaries(gene_ids)
        requested = gene_symbol.strip().upper()

        for gene_id in gene_ids:
            name = summaries.get(gene_id, {}).get("name")
            if name and name.strip().upper() == requested:
                return gene_id

        for gene_id in gene_ids:
            name = summaries.get(gene_id, {}).get("name")
            if name and requested in name.strip().upper():
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

    def fetch_genomic_slice(
        self,
        accession: str,
        start_1_based: int,
        stop_1_based: int,
    ) -> str:
        lo = min(start_1_based, stop_1_based)
        hi = max(start_1_based, stop_1_based)

        return get_text(
            f"{NCBI_EUTILS_BASE}/efetch.fcgi",
            {
                "db": "nuccore",
                "id": accession,
                "rettype": "fasta",
                "retmode": "text",
                "seq_start": lo,
                "seq_stop": hi,
            },
        )

    def extract_loci_from_summary(
        self,
        summary: Dict[str, Any],
        include_fasta: bool,
        max_loci: int,
    ) -> List[LocusRecord]:
        genomic_info = summary.get("genomicinfo") or summary.get("locationhist") or []
        loci: List[LocusRecord] = []

        if not isinstance(genomic_info, list):
            return loci

        for item in genomic_info[:max_loci]:
            chr_acc = item.get("chraccver")
            chr_loc = item.get("chrloc")

            chr_start = item.get("chrstart")
            chr_stop = item.get("chrstop")
            exon_count = item.get("exoncount")

            if chr_acc is None or chr_start is None or chr_stop is None:
                continue

            try:
                chr_start = int(chr_start)
                chr_stop = int(chr_stop)
            except (TypeError, ValueError):
                continue

            strand = "plus" if chr_start <= chr_stop else "minus"

            start_1 = min(chr_start, chr_stop) + 1
            stop_1 = max(chr_start, chr_stop) + 1

            fasta = None
            if include_fasta:
                fasta = self.fetch_genomic_slice(
                    accession=chr_acc,
                    start_1_based=start_1,
                    stop_1_based=stop_1,
                )
                time.sleep(0.2)

            loci.append(
                LocusRecord(
                    chr_accession=chr_acc,
                    chr_loc=chr_loc,
                    start_0_based=min(chr_start, chr_stop),
                    stop_0_based=max(chr_start, chr_stop),
                    start_1_based=start_1,
                    stop_1_based=stop_1,
                    strand=strand,
                    exon_count=exon_count,
                    fasta=fasta,
                )
            )

        return loci

    def run(
        self,
        gene_symbol: Optional[str] = None,
        gene_id: Optional[str] = None,
        organism: Optional[str] = None,
        max_loci: int = 3,
        include_fasta: bool = True,
    ) -> GeneLocusResult:
        resolved_gene_id = gene_id
        query_gene_symbol = gene_symbol
        query_gene_id = gene_id

        if not resolved_gene_id:
            if not gene_symbol:
                return GeneLocusResult(
                    query_gene_symbol=None,
                    query_gene_id=None,
                    organism=organism,
                    resolved_gene_id=None,
                    resolved_symbol=None,
                    gene_description=None,
                    loci=[],
                )

            candidate_gene_ids = self.search_gene_ids(
                gene_symbol=gene_symbol,
                organism=organism,
                retmax=10,
            )
            if not candidate_gene_ids:
                return GeneLocusResult(
                    query_gene_symbol=query_gene_symbol,
                    query_gene_id=query_gene_id,
                    organism=organism,
                    resolved_gene_id=None,
                    resolved_symbol=None,
                    gene_description=None,
                    loci=[],
                )

            resolved_gene_id = self.choose_best_gene_id(
                gene_ids=candidate_gene_ids,
                gene_symbol=gene_symbol,
            )

        if not resolved_gene_id:
            return GeneLocusResult(
                query_gene_symbol=query_gene_symbol,
                query_gene_id=query_gene_id,
                organism=organism,
                resolved_gene_id=None,
                resolved_symbol=None,
                gene_description=None,
                loci=[],
            )

        summary = self.gene_summary(resolved_gene_id)
        resolved_symbol = summary.get("name")
        gene_description = summary.get("description")

        loci = self.extract_loci_from_summary(
            summary=summary,
            include_fasta=include_fasta,
            max_loci=max_loci,
        )

        return GeneLocusResult(
            query_gene_symbol=query_gene_symbol,
            query_gene_id=query_gene_id,
            organism=organism,
            resolved_gene_id=resolved_gene_id,
            resolved_symbol=resolved_symbol,
            gene_description=gene_description,
            loci=loci,
        )