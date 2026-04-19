"""
CRISPR gRNA designer

Description:
    Designs a guide RNA sequence for either Cas9 or Cas12a by:
    1. validating DNA,
    2. finding the PAM,
    3. extracting the protospacer,
    4. appending the scaffold,
    5. converting DNA to RNA.

    Version 1 supports:
    - Cas9 with PAM = NGG
    - Cas12a with PAM = TTTV

Input:
    target (str): DNA target sequence.
    nuclease (str): Either "Cas9" or "Cas12a".

Output:
    dict:
        {
            "nuclease": "...",
            "pam_index": ...,
            "pam_sequence": "...",
            "protospacer": "...",
            "guide_dna": "...",
            "guide_rna": "..."
        }
"""

class CRISPRGuideDesigner:
    def initiate(self) -> None:
        self.valid_dna = {"A", "T", "C", "G"}
        self.cas9_scaffold = (
            "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCAACTTGAAAAAGTGGCACCGAGTCGGTGC"
        )
        self.cas12a_scaffold = (
            "AATTTCTACTAAGTGTAGAT"
        )

    def run(self, target: str, nuclease: str = "Cas9") -> dict:
        if target is None:
            raise ValueError("Target sequence is required.")

        target = target.upper().strip()
        nuclease = nuclease.strip()

        if not self.validate_DNA(target):
            raise ValueError("Invalid target sequence")

        if nuclease == "Cas9":
            pam_index = self.find_PAM_cas9(target)
            pam_sequence = target[pam_index - 1 : pam_index + 2]
            protospacer = self.find_protospacer_cas9(target)
            guide_dna = self.design_cas9_DNA(target)
            guide_rna = self.design_cas9_gRNA(target)

        elif nuclease == "Cas12a":
            pam_index = self.find_PAM_cas12a(target)
            pam_sequence = target[pam_index : pam_index + 4]
            protospacer = self.find_protospacer_cas12a(target)
            guide_dna = self.design_cas12a_DNA(target)
            guide_rna = self.design_cas12a_gRNA(target)

        else:
            raise ValueError("nuclease must be either 'Cas9' or 'Cas12a'.")

        return {
            "nuclease": nuclease,
            "pam_index": pam_index,
            "pam_sequence": pam_sequence,
            "protospacer": protospacer,
            "guide_dna": guide_dna,
            "guide_rna": guide_rna,
        }

    def validate_DNA(self, seq: str) -> bool:
        if seq is None:
            return False
        return all(nucleotide in self.valid_dna for nucleotide in seq)

    # --------------------
    # Cas9 logic
    # --------------------
    def find_PAM_cas9(self, target: str) -> int:
        """
        Finds the first GG PAM after position 23.
        Returns the index of the first G in GG.
        """
        pam_index = target.find("GG", 23)
        if pam_index == -1:
            raise ValueError("No 'GG' PAM sequence found for Cas9.")
        return pam_index

    def find_protospacer_cas9(self, target: str) -> str:
        """
        Cas9 protospacer = 20 bp immediately before the NGG PAM.
        """
        pam_index = self.find_PAM_cas9(target)

        if pam_index < 21:
            raise ValueError("The Cas9 PAM is too close to the start of the sequence.")

        protospacer = target[pam_index - 21 : pam_index - 1]
        return protospacer

    def design_cas9_DNA(self, target: str) -> str:
        protospacer = self.find_protospacer_cas9(target)
        return protospacer + self.cas9_scaffold

    def design_cas9_gRNA(self, target: str) -> str:
        guide_dna = self.design_cas9_DNA(target)
        return guide_dna.replace("T", "U")

    # --------------------
    # Cas12a logic
    # --------------------
    def _is_TTTV(self, seq4: str) -> bool:
        """
        TTTV PAM where V = A, C, or G
        """
        if len(seq4) != 4:
            return False
        return seq4[:3] == "TTT" and seq4[3] in {"A", "C", "G"}

    def find_PAM_cas12a(self, target: str) -> int:
        """
        Finds the first TTTV PAM with enough downstream sequence
        for a 20 nt protospacer.
        Returns the index of the first T in TTTV.
        """
        for i in range(len(target) - 4):
            pam = target[i : i + 4]
            if self._is_TTTV(pam):
                if i + 4 + 20 <= len(target):
                    return i
        raise ValueError("No 'TTTV' PAM sequence found for Cas12a.")

    def find_protospacer_cas12a(self, target: str) -> str:
        """
        Cas12a protospacer = 20 bp immediately after the TTTV PAM.
        """
        pam_index = self.find_PAM_cas12a(target)
        start = pam_index + 4
        end = start + 20

        if end > len(target):
            raise ValueError("The Cas12a PAM is too close to the end of the sequence.")

        protospacer = target[start:end]
        return protospacer

    def design_cas12a_DNA(self, target: str) -> str:
        protospacer = self.find_protospacer_cas12a(target)
        return protospacer + self.cas12a_scaffold

    def design_cas12a_gRNA(self, target: str) -> str:
        guide_dna = self.design_cas12a_DNA(target)
        return guide_dna.replace("T", "U")


_instance = CRISPRGuideDesigner()
_instance.initiate()
crispr_guide_designer = _instance.run