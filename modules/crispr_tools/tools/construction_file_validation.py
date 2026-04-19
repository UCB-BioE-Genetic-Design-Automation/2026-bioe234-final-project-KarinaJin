from __future__ import annotations

from typing import Dict, List, Optional

from modules.crispr_tools.tools.create_construction_file import CreateConstructionFile


DNA_ALPHABET = {"A", "C", "G", "T", "N"}
COMPLEMENT = str.maketrans("ACGTN", "TGCAN")


class ConstructionValidationError(ValueError):
    """Raised when a construction file fails biological validation."""


def normalize_sequence(seq: str) -> str:
    """
    Normalize a DNA sequence by uppercasing and removing non-letter characters.
    Then confirm it only contains A/C/G/T/N.
    """
    if not isinstance(seq, str) or not seq.strip():
        raise ConstructionValidationError("Sequence must be a non-empty string.")

    cleaned = "".join(ch for ch in seq.upper() if ch.isalpha())
    if not cleaned:
        raise ConstructionValidationError("Sequence became empty after normalization.")

    invalid = set(cleaned) - DNA_ALPHABET
    if invalid:
        raise ConstructionValidationError(
            f"Sequence contains invalid DNA characters: {sorted(invalid)}"
        )

    return cleaned


def reverse_complement(seq: str) -> str:
    seq = normalize_sequence(seq)
    return seq.translate(COMPLEMENT)[::-1]


def find_all_occurrences(sequence: str, subsequence: str) -> List[int]:
    sequence = normalize_sequence(sequence)
    subsequence = normalize_sequence(subsequence)

    positions: List[int] = []
    start = 0

    while True:
        idx = sequence.find(subsequence, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + 1

    return positions


def find_all_forward_matches(
    primer: str,
    template: str,
    min_anneal_len: int = 12,
) -> List[dict]:
    primer = normalize_sequence(primer)
    template = normalize_sequence(template)

    if len(primer) < min_anneal_len:
        raise ConstructionValidationError(
            f"Primer length ({len(primer)}) is shorter than min_anneal_len ({min_anneal_len})."
        )

    matches: List[dict] = []
    seen = set()

    for k in range(len(primer), min_anneal_len - 1, -1):
        anneal_seq = primer[-k:]
        for start in find_all_occurrences(template, anneal_seq):
            key = (start, k)
            if key in seen:
                continue
            seen.add(key)
            matches.append(
                {
                    "binding_start": start,
                    "binding_end": start + len(anneal_seq),
                    "anneal_sequence": anneal_seq,
                    "anneal_length": len(anneal_seq),
                }
            )

    if not matches:
        raise ConstructionValidationError(
            f"No forward-primer suffix of length >= {min_anneal_len} anneals to the template."
        )

    matches.sort(key=lambda m: (m["binding_start"], -m["anneal_length"]))
    return matches


def find_all_reverse_matches(
    reverse_primer: str,
    template: str,
    min_anneal_len: int = 12,
) -> List[dict]:
    reverse_primer = normalize_sequence(reverse_primer)
    template = normalize_sequence(template)

    if len(reverse_primer) < min_anneal_len:
        raise ConstructionValidationError(
            f"Reverse primer length ({len(reverse_primer)}) is shorter than min_anneal_len ({min_anneal_len})."
        )

    matches: List[dict] = []
    seen = set()

    for k in range(len(reverse_primer), min_anneal_len - 1, -1):
        anneal_suffix = reverse_primer[-k:]
        binding_seq = reverse_complement(anneal_suffix)

        for start in find_all_occurrences(template, binding_seq):
            key = (start, k)
            if key in seen:
                continue
            seen.add(key)
            matches.append(
                {
                    "binding_start": start,
                    "binding_end": start + len(binding_seq),
                    "anneal_sequence": anneal_suffix,
                    "template_binding_sequence": binding_seq,
                    "anneal_length": len(anneal_suffix),
                }
            )

    if not matches:
        raise ConstructionValidationError(
            f"No reverse-primer suffix of length >= {min_anneal_len} anneals to the template."
        )

    matches.sort(key=lambda m: (m["binding_start"], -m["anneal_length"]))
    return matches


def choose_best_pcr_product(
    forward_primer: str,
    reverse_primer: str,
    template: str,
    min_anneal_len: int = 12,
    is_circular: bool = False,
) -> Dict[str, object]:
    """
    Evaluate all forward/reverse binding combinations and choose the best valid PCR product.

    Linear template:
    - require forward_start < reverse_start
    - require no overlap

    Circular template:
    - search on template + template
    - allow wraparound products
    - only allow products spanning <= one template length
    """
    forward_primer = normalize_sequence(forward_primer)
    reverse_primer = normalize_sequence(reverse_primer)
    template = normalize_sequence(template)

    template_len = len(template)
    search_template = template + template if is_circular else template

    forward_matches = find_all_forward_matches(
        forward_primer, search_template, min_anneal_len=min_anneal_len
    )
    reverse_matches = find_all_reverse_matches(
        reverse_primer, search_template, min_anneal_len=min_anneal_len
    )

    candidates: List[dict] = []

    for fwd in forward_matches:
        for rev in reverse_matches:
            fwd_start = fwd["binding_start"]
            fwd_end = fwd["binding_end"]
            rev_start = rev["binding_start"]
            rev_end = rev["binding_end"]

            if not is_circular:
                if fwd_start >= rev_start:
                    continue
                if fwd_end > rev_start:
                    continue

                internal_template_region = search_template[fwd_end:rev_start]
                predicted_product = (
                    forward_primer
                    + internal_template_region
                    + reverse_complement(reverse_primer)
                )

                candidates.append(
                    {
                        "predicted_sequence": predicted_product,
                        "forward_binding_start": fwd_start,
                        "forward_binding_end": fwd_end,
                        "forward_anneal_sequence": fwd["anneal_sequence"],
                        "forward_anneal_length": fwd["anneal_length"],
                        "reverse_binding_start": rev_start,
                        "reverse_binding_end": rev_end,
                        "reverse_anneal_sequence": rev["anneal_sequence"],
                        "reverse_anneal_length": rev["anneal_length"],
                        "product_length": len(predicted_product),
                        "is_circular_template": False,
                    }
                )
            else:
                # For circular templates, require the reverse site to be downstream
                # of the forward site on the doubled template.
                if rev_start <= fwd_start:
                    continue
                if fwd_end > rev_start:
                    continue

                span = rev_start - fwd_end
                if span < 0:
                    continue
                if span > template_len:
                    continue

                internal_template_region = search_template[fwd_end:rev_start]
                predicted_product = (
                    forward_primer
                    + internal_template_region
                    + reverse_complement(reverse_primer)
                )

                candidates.append(
                    {
                        "predicted_sequence": predicted_product,
                        "forward_binding_start": fwd_start % template_len,
                        "forward_binding_end": fwd_end % template_len,
                        "forward_anneal_sequence": fwd["anneal_sequence"],
                        "forward_anneal_length": fwd["anneal_length"],
                        "reverse_binding_start": rev_start % template_len,
                        "reverse_binding_end": rev_end % template_len,
                        "reverse_anneal_sequence": rev["anneal_sequence"],
                        "reverse_anneal_length": rev["anneal_length"],
                        "product_length": len(predicted_product),
                        "is_circular_template": True,
                        "wraparound_span": span,
                    }
                )

    if not candidates:
        if is_circular:
            raise ConstructionValidationError(
                "No valid forward/reverse primer pair produced a PCR amplicon on the circular plasmid template."
            )
        raise ConstructionValidationError(
            "No valid forward/reverse primer pair produced a correctly oriented PCR amplicon."
        )

    candidates.sort(
        key=lambda c: (
            c["product_length"],
            -(c["forward_anneal_length"] + c["reverse_anneal_length"]),
            c["forward_binding_start"],
            c["reverse_binding_start"],
        )
    )

    best = candidates[0]
    best["candidate_count"] = len(candidates)
    return best


def predict_pcr_product(
    forward_primer: str,
    reverse_primer: str,
    template: str,
    min_anneal_len: int = 12,
    is_circular: bool = False,
) -> Dict[str, object]:
    return choose_best_pcr_product(
        forward_primer=forward_primer,
        reverse_primer=reverse_primer,
        template=template,
        min_anneal_len=min_anneal_len,
        is_circular=is_circular,
    )


def build_part_lookup(parts: List[dict]) -> Dict[str, dict]:
    lookup: Dict[str, dict] = {}

    for part in parts:
        name = part.get("name", "").strip()
        if not name:
            raise ConstructionValidationError("Each part must have a non-empty name.")
        lookup[name] = part

    return lookup


def get_part_sequence(part_lookup: Dict[str, dict], part_name: str) -> str:
    if part_name not in part_lookup:
        raise ConstructionValidationError(f"Part '{part_name}' not found in parts list.")

    sequence = part_lookup[part_name].get("sequence", "")
    return normalize_sequence(sequence)


def validate_pcr_step(
    step: dict,
    part_lookup: Dict[str, dict],
    expected_sequences: Optional[Dict[str, str]] = None,
    min_anneal_len: int = 12,
) -> Dict[str, object]:
    expected_sequences = expected_sequences or {}

    if step.get("step_type") != "PCR":
        raise ConstructionValidationError("validate_pcr_step only accepts PCR steps.")

    params = step.get("parameters", {})
    output_name = step.get("output", "").strip()

    forward_name = params.get("forward_primer", "").strip()
    reverse_name = params.get("reverse_primer", "").strip()
    template_name = params.get("template", "").strip()

    if not forward_name or not reverse_name or not template_name or not output_name:
        raise ConstructionValidationError("PCR step is missing required names.")

    if template_name not in part_lookup:
        raise ConstructionValidationError(f"Template part '{template_name}' not found.")

    template_part = part_lookup[template_name]
    template_type = template_part.get("part_type", "").strip()

    forward_seq = get_part_sequence(part_lookup, forward_name)
    reverse_seq = get_part_sequence(part_lookup, reverse_name)
    template_seq = get_part_sequence(part_lookup, template_name)

    is_circular = template_type == "plasmid"

    prediction = predict_pcr_product(
        forward_primer=forward_seq,
        reverse_primer=reverse_seq,
        template=template_seq,
        min_anneal_len=min_anneal_len,
        is_circular=is_circular,
    )

    predicted_seq = prediction["predicted_sequence"]
    expected_seq = None
    matches_expected = None

    if output_name in expected_sequences:
        expected_seq = normalize_sequence(expected_sequences[output_name])
        matches_expected = predicted_seq == expected_seq
        if not matches_expected:
            raise ConstructionValidationError(
                f"PCR output '{output_name}' does not match the expected sequence."
            )

    if is_circular:
        message = "PCR step validated successfully on circular plasmid template."
    else:
        message = "PCR step validated successfully."

    return {
        "step_number": step.get("step_number"),
        "step_type": "PCR",
        "output_name": output_name,
        "is_valid": True,
        "message": message,
        "expected_sequence_provided": expected_seq is not None,
        "matches_expected_sequence": matches_expected,
        "details": prediction,
    }


def validate_construction_record(
    structured_construction_file: dict,
    expected_sequences: Optional[Dict[str, str]] = None,
    min_anneal_len: int = 12,
    strict: bool = False,
) -> Dict[str, object]:
    expected_sequences = expected_sequences or {}

    parts = structured_construction_file.get("parts", [])
    operations = structured_construction_file.get("operations", [])

    if not isinstance(parts, list) or not isinstance(operations, list):
        raise ConstructionValidationError(
            "structured_construction_file must contain 'parts' and 'operations' lists."
        )

    part_lookup = build_part_lookup(parts)

    report = {
        "construct_name": structured_construction_file.get("construct_name"),
        "assembly_strategy": structured_construction_file.get("assembly_strategy"),
        "is_valid": True,
        "step_results": [],
        "errors": [],
        "warnings": [],
    }

    for step in operations:
        step_type = step.get("step_type")

        if step_type == "PCR":
            try:
                step_result = validate_pcr_step(
                    step=step,
                    part_lookup=part_lookup,
                    expected_sequences=expected_sequences,
                    min_anneal_len=min_anneal_len,
                )
                report["step_results"].append(step_result)

            except ConstructionValidationError as e:
                report["step_results"].append(
                    {
                        "step_number": step.get("step_number"),
                        "step_type": "PCR",
                        "output_name": step.get("output"),
                        "is_valid": False,
                        "message": str(e),
                    }
                )
                report["errors"].append(
                    f"PCR step {step.get('step_number')} failed: {e}"
                )
                report["is_valid"] = False

                if strict:
                    raise

        else:
            report["step_results"].append(
                {
                    "step_number": step.get("step_number"),
                    "step_type": step_type,
                    "output_name": step.get("output"),
                    "is_valid": None,
                    "message": f"{step_type} biological validation is not implemented in version 1.",
                }
            )
            report["warnings"].append(
                f"Step {step.get('step_number')} ({step_type}) was not biologically validated."
            )

    return report


def format_validation_report(report: dict) -> str:
    lines = []

    construct_name = report.get("construct_name", "Unknown construct")
    assembly_strategy = report.get("assembly_strategy", "Unknown strategy")
    is_valid = report.get("is_valid", False)

    status = "PASS" if is_valid else "FAIL"

    lines.append("=== Construction File Validation Report ===")
    lines.append(f"Construct: {construct_name}")
    lines.append(f"Assembly strategy: {assembly_strategy}")
    lines.append(f"Overall result: {status}")
    lines.append("")

    lines.append("Step-by-step results:")
    for step in report.get("step_results", []):
        step_number = step.get("step_number", "?")
        step_type = step.get("step_type", "Unknown")
        output_name = step.get("output_name", "Unknown output")
        step_valid = step.get("is_valid")

        if step_valid is True:
            icon = "[PASS]"
        elif step_valid is False:
            icon = "[FAIL]"
        else:
            icon = "[SKIP]"

        lines.append(f"{icon} Step {step_number}: {step_type} -> {output_name}")
        lines.append(f"       {step.get('message', '')}")

        details = step.get("details")
        if isinstance(details, dict) and step_type == "PCR" and step_valid is True:
            if details.get("is_circular_template"):
                lines.append("       Template type: circular plasmid")
            lines.append(
                f"       Forward binding: {details.get('forward_binding_start')} to {details.get('forward_binding_end')}"
            )
            lines.append(
                f"       Reverse binding: {details.get('reverse_binding_start')} to {details.get('reverse_binding_end')}"
            )
            lines.append(
                f"       Product length: {details.get('product_length')} bp"
            )
            lines.append(
                f"       Candidate primer pairings checked: {details.get('candidate_count', 1)}"
            )

        lines.append("")

    errors = report.get("errors", [])
    if errors:
        lines.append("Errors:")
        for error in errors:
            lines.append(f"  - {error}")
        lines.append("")

    warnings = report.get("warnings", [])
    if warnings:
        lines.append("Warnings:")
        for warning in warnings:
            lines.append(f"  - {warning}")
        lines.append("")

    return "\n".join(lines)


class ValidateConstructionFile:
    """
    Validate a construction workflow from the original user inputs rather than
    requiring a pre-built structured construction record.
    """

    def initiate(self) -> None:
        self.builder = CreateConstructionFile()
        self.builder.initiate()

    def run(
        self,
        construct_name: str,
        host_organism: str,
        assembly_strategy: str,
        backbone_name: str,
        backbone_sequence: str,
        insert_name: str,
        insert_sequence: str,
        insert_forward_primer_name: str = "",
        insert_forward_primer_sequence: str = "",
        insert_reverse_primer_name: str = "",
        insert_reverse_primer_sequence: str = "",
        vector_forward_primer_name: str = "",
        vector_forward_primer_sequence: str = "",
        vector_reverse_primer_name: str = "",
        vector_reverse_primer_sequence: str = "",
        enzyme: str = "",
        cell_strain: str = "",
        selection: str = "",
        temperature_c: int = 37,
        notes: str = "",
        expected_sequences: Optional[Dict[str, str]] = None,
        min_anneal_len: int = 12,
        strict: bool = False,
    ) -> dict:
        if expected_sequences is not None and not isinstance(expected_sequences, dict):
            raise ConstructionValidationError(
                "expected_sequences must be a dictionary if provided."
            )

        if not isinstance(min_anneal_len, int) or min_anneal_len <= 0:
            raise ConstructionValidationError(
                "min_anneal_len must be a positive integer."
            )

        if not isinstance(strict, bool):
            raise ConstructionValidationError("strict must be a boolean.")

        # Rebuild the same internal structure used by create_construction_file
        host_organism = self.builder._normalize_host_organism(host_organism)

        self.builder._require_nonempty_string(construct_name, "construct_name")
        self.builder._require_nonempty_string(host_organism, "host_organism")
        self.builder._require_nonempty_string(assembly_strategy, "assembly_strategy")
        self.builder._require_nonempty_string(backbone_name, "backbone_name")
        self.builder._require_nonempty_string(backbone_sequence, "backbone_sequence")
        self.builder._require_nonempty_string(insert_name, "insert_name")
        self.builder._require_nonempty_string(insert_sequence, "insert_sequence")

        if host_organism not in self.builder.supported_organisms:
            raise ConstructionValidationError("host_organism must be E_coli for version 1.")

        if assembly_strategy not in self.builder.allowed_strategies:
            raise ConstructionValidationError(
                f"assembly_strategy must be one of {sorted(self.builder.allowed_strategies)}."
            )

        self.builder._validate_user_inputs(
            assembly_strategy=assembly_strategy,
            insert_forward_primer_name=insert_forward_primer_name,
            insert_forward_primer_sequence=insert_forward_primer_sequence,
            insert_reverse_primer_name=insert_reverse_primer_name,
            insert_reverse_primer_sequence=insert_reverse_primer_sequence,
            vector_forward_primer_name=vector_forward_primer_name,
            vector_forward_primer_sequence=vector_forward_primer_sequence,
            vector_reverse_primer_name=vector_reverse_primer_name,
            vector_reverse_primer_sequence=vector_reverse_primer_sequence,
            enzyme=enzyme,
        )

        parts = self.builder._build_parts(
            backbone_name=backbone_name,
            backbone_sequence=backbone_sequence,
            insert_name=insert_name,
            insert_sequence=insert_sequence,
            insert_forward_primer_name=insert_forward_primer_name,
            insert_forward_primer_sequence=insert_forward_primer_sequence,
            insert_reverse_primer_name=insert_reverse_primer_name,
            insert_reverse_primer_sequence=insert_reverse_primer_sequence,
            vector_forward_primer_name=vector_forward_primer_name,
            vector_forward_primer_sequence=vector_forward_primer_sequence,
            vector_reverse_primer_name=vector_reverse_primer_name,
            vector_reverse_primer_sequence=vector_reverse_primer_sequence,
        )
        validated_parts = self.builder._validate_parts(parts)

        operations = self.builder._build_operations(
            construct_name=construct_name,
            assembly_strategy=assembly_strategy,
            backbone_name=backbone_name,
            insert_name=insert_name,
            insert_forward_primer_name=insert_forward_primer_name,
            insert_reverse_primer_name=insert_reverse_primer_name,
            vector_forward_primer_name=vector_forward_primer_name,
            vector_reverse_primer_name=vector_reverse_primer_name,
            enzyme=enzyme,
            cell_strain=cell_strain,
            selection=selection,
            temperature_c=temperature_c,
        )
        validated_operations = self.builder._validate_operations(operations, validated_parts)

        structured_construction_file = {
            "construct_name": construct_name,
            "host_organism": host_organism,
            "assembly_strategy": assembly_strategy,
            "parts": validated_parts,
            "operations": validated_operations,
            "notes": notes,
        }

        report = validate_construction_record(
            structured_construction_file=structured_construction_file,
            expected_sequences=expected_sequences or {},
            min_anneal_len=min_anneal_len,
            strict=strict,
        )

        return {
            "readable_summary": format_validation_report(report)
        }


_instance = ValidateConstructionFile()
_instance.initiate()
validate_construction_file = _instance.run