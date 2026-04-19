class CasSelector:
    """
    Description:
        Analyzes the GC and AT content of a DNA sequence and recommends
        whether to use Cas9 or Cas12a for CRISPR editing in that organism.

        Cas9 (e.g. SpCas9) uses an NGG PAM site. NGG PAM sites occur more
        frequently in GC-rich genomes, making Cas9 the better choice when
        GC content >= 50%.

        Cas12a (e.g. AsCas12a / LbCas12a) uses a TTTV PAM site (where V is
        A, C, or G). TTTV PAM sites are more abundant in AT-rich genomes,
        making Cas12a the better choice when AT content > GC content
        (i.e. GC content < 50%).

        The framework resolves the input before calling run(): a GenBank file,
        FASTA string, resource name (e.g. "pBR322"), or a raw sequence string
        are all accepted and converted to a clean uppercase sequence automatically.
        IUPAC ambiguity bases (e.g. N) are ignored and not counted toward
        either GC or AT totals.

    Input:
        seq (str): DNA sequence. Accepts a resource name, a raw sequence
                   string, a FASTA-formatted string, or a GenBank-formatted
                   string. The framework resolves the format automatically.

    Output:
        dict: A dictionary with keys:
            - gc_fraction (float): Fraction of G/C bases out of counted bases (0.0 to 1.0).
            - at_fraction (float): Fraction of A/T bases out of counted bases (0.0 to 1.0).
            - recommendation (str): "Cas9" or "Cas12a".
            - rationale (str): One-sentence explanation of the recommendation.

    Tests:
        - Case:
            Input: seq="GCGCGCGCGC"
            Expected Output: {"gc_fraction": 1.0, "at_fraction": 0.0, "recommendation": "Cas9"}
            Description: All-GC sequence should recommend Cas9.
        - Case:
            Input: seq="ATATATATAT"
            Expected Output: {"gc_fraction": 0.0, "at_fraction": 1.0, "recommendation": "Cas12a"}
            Description: All-AT sequence should recommend Cas12a.
        - Case:
            Input: seq="ATGCATGC"
            Expected Output: {"gc_fraction": 0.5, "at_fraction": 0.5, "recommendation": "Cas9"}
            Description: Exactly 50% GC defaults to Cas9.
        - Case:
            Input: seq="ATGCNNNN"
            Expected Output: {"gc_fraction": 0.5, "at_fraction": 0.5, "recommendation": "Cas9"}
            Description: Ambiguous N bases are ignored; fractions computed from ATGC only.
        - Case:
            Input: seq=""
            Expected Exception: ValueError
            Description: Empty sequence raises ValueError.
    """

    def initiate(self) -> None:
        pass  # no setup needed

    def run(self, seq: str) -> dict:
        """Return GC/AT fractions and a Cas9-vs-Cas12a recommendation."""
        seq = seq.upper()

        if not seq:
            raise ValueError("Sequence must not be empty.")

        gc = sum(1 for b in seq if b in "GC")
        at = sum(1 for b in seq if b in "AT")
        counted = gc + at  # ignore IUPAC ambiguity bases

        if counted == 0:
            raise ValueError(
                "Sequence contains no countable A/T/G/C bases."
            )

        gc_fraction = gc / counted
        at_fraction = at / counted

        if gc_fraction >= 0.5:
            recommendation = "Cas9"
            rationale = (
                f"GC content is {gc_fraction:.1%}, so NGG PAM sites (used by Cas9) "
                "are relatively abundant — Cas9 is the preferred CRISPR nuclease."
            )
        else:
            recommendation = "Cas12a"
            rationale = (
                f"AT content is {at_fraction:.1%}, so TTTV PAM sites (used by Cas12a) "
                "are relatively abundant — Cas12a is the preferred CRISPR nuclease."
            )

        return {
            "gc_fraction": round(gc_fraction, 4),
            "at_fraction": round(at_fraction, 4),
            "recommendation": recommendation,
            "rationale": rationale,
        }


_instance = CasSelector()
_instance.initiate()
cas_selector = _instance.run   # cas_selector("ATGCATGC") → dict
