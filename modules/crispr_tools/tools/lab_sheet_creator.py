"""
Lab Sheet Creator

Description:
    Generate lecture-aligned LabSheets from a rendered construction file text.

    This tool is designed to work with the current CreateConstructionFile tool,
    which returns:
        {
            "construction_file_txt": "..."
        }

    The lab sheet creator parses each operation line from the construction file
    and converts it into LabPlanner-style assignment sheets such as:
    - PCR
    - GoldenGate / Gibson / DirectSynthesis / Assemble
    - Transform

    This follows the Function Object Pattern required by the course:
    - initiate(): one-time setup
    - run(): per-tool invocation

Input:
    construction_file_txt (str):
        Rendered construction file text from create_construction_file.
    thread_letter (str):
        Lecture-style thread label prefix, e.g. "A". Default is "A".
    include_text_render (bool):
        Whether to include human-readable LabSheet text output. Default True.

Output:
    dict:
        {
            "lab_sheets": [...],
            "lab_sheet_txt": "...",
            "notes": [...]
        }

Notes:
    - This tool formats planning output only.
    - It does not validate biological correctness.
    - construction_file_validate should be used separately.
"""

from __future__ import annotations

from typing import Any, Dict, List


class LabSheetCreator:
    """
    Convert rendered construction file text into lecture-style LabSheets.
    """

    def initiate(self) -> None:
        self.supported_operations = {
            "PCR",
            "GoldenGate",
            "Gibson",
            "DirectSynthesis",
            "Transform",
        }

        self.default_destination_by_op = {
            "PCR": "thermocycler1A",
            "GoldenGate": "thermocycler1A",
            "Gibson": "thermocycler1A",
            "DirectSynthesis": "ordering",
            "Transform": "bench",
        }

        self.default_program_by_op = {
            "PCR": "Q5/Q5-4K",
            "GoldenGate": "main/GG1",
            "Gibson": "main/GIB2",
            "DirectSynthesis": "",
            "Transform": "",
        }

        self.default_notes_by_op = {
            "PCR": [
                "When complete, save any important primer or DNA stocks in the appropriate box.",
                "Never let enzymes warm up. Only take the enzyme cooler out when actively using it.",
            ],
            "GoldenGate": [
                "Assembly reactions are similar to digestion and ligation setup.",
                "Never let enzymes warm up. Only take the enzyme cooler out when actively using it.",
            ],
            "Gibson": [
                "A Gibson setup is similar on paper to a Golden Gate setup.",
                "Never let enzymes warm up. Only take the enzyme cooler out when actively using it.",
            ],
            "DirectSynthesis": [
                "Direct synthesis does not require bench assembly planning at this step."
            ],
            "Transform": [
                "If the antibiotic requires recovery/rescue, perform that before plating."
            ],
        }

    def _require_nonempty_string(self, value: str, field_name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string.")

    def _parse_operation_lines(self, construction_file_txt: str) -> List[Dict[str, Any]]:
        """
        Parse only the operation lines from the construction file text.
        Stops when it reaches the blank line before the parts section.
        """
        lines = construction_file_txt.splitlines()
        operations: List[Dict[str, Any]] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                break

            tokens = stripped.split()
            if not tokens:
                continue

            op = tokens[0]
            if op not in self.supported_operations:
                continue

            if op == "PCR":
                # Format:
                # PCR <forward_primer> <reverse_primer> <template> <output>
                if len(tokens) < 5:
                    raise ValueError(f"Malformed PCR line: '{line}'")
                operations.append(
                    {
                        "step_type": "PCR",
                        "forward_primer": tokens[1],
                        "reverse_primer": tokens[2],
                        "template": tokens[3],
                        "output": tokens[4],
                    }
                )

            elif op == "GoldenGate":
                # Format:
                # GoldenGate <vector_pcr> <insert_pcr> <enzyme> <output>
                if len(tokens) < 5:
                    raise ValueError(f"Malformed GoldenGate line: '{line}'")
                operations.append(
                    {
                        "step_type": "GoldenGate",
                        "vector": tokens[1],
                        "insert": tokens[2],
                        "enzyme": tokens[3],
                        "output": tokens[4],
                    }
                )

            elif op == "Gibson":
                # Format:
                # Gibson <vector_pcr> <insert_pcr> <overlap_info> <output>
                if len(tokens) < 5:
                    raise ValueError(f"Malformed Gibson line: '{line}'")
                operations.append(
                    {
                        "step_type": "Gibson",
                        "vector": tokens[1],
                        "insert": tokens[2],
                        "overlap_info": tokens[3],
                        "output": tokens[4],
                    }
                )

            elif op == "DirectSynthesis":
                # Format:
                # DirectSynthesis <input> <output>
                if len(tokens) < 3:
                    raise ValueError(f"Malformed DirectSynthesis line: '{line}'")
                operations.append(
                    {
                        "step_type": "DirectSynthesis",
                        "input": tokens[1],
                        "output": tokens[2],
                    }
                )

            elif op == "Transform":
                # Format:
                # Transform <construct> <cells> <selection> <temp> <output>
                if len(tokens) < 6:
                    raise ValueError(f"Malformed Transform line: '{line}'")
                operations.append(
                    {
                        "step_type": "Transform",
                        "construct": tokens[1],
                        "cells": tokens[2],
                        "selection": tokens[3],
                        "temperature_c": tokens[4],
                        "output": tokens[5],
                    }
                )

        return operations

    def _make_sample_label(self, thread_letter: str, index: int) -> str:
        return f"{thread_letter}{index}"

    def _build_lab_sheet_for_operation(
        self,
        operation: Dict[str, Any],
        thread_letter: str,
        index: int,
    ) -> Dict[str, Any]:
        step_type = operation["step_type"]
        label = self._make_sample_label(thread_letter, index)

        if step_type == "PCR":
            return {
                "title": f"{thread_letter}: PCR",
                "operation": "PCR",
                "samples": [
                    {
                        "label": label,
                        "primer1": operation["forward_primer"],
                        "primer2": operation["reverse_primer"],
                        "template": operation["template"],
                        "product": operation["output"],
                    }
                ],
                "source": [
                    {"label": operation["template"], "location": "", "note": ""},
                    {"label": operation["forward_primer"], "location": "", "note": ""},
                    {"label": operation["reverse_primer"], "location": "", "note": ""},
                ],
                "destination": self.default_destination_by_op["PCR"],
                "program": self.default_program_by_op["PCR"],
                "notes": self.default_notes_by_op["PCR"],
            }

        if step_type == "GoldenGate":
            return {
                "title": f"{thread_letter}: Assemble",
                "operation": "GoldenGate",
                "dna_mix": [
                    f"5 uL {operation['vector']}",
                    f"5 uL {operation['insert']}",
                ],
                "reaction": [
                    "7 uL ddH2O",
                    "1 uL T4 DNA ligase buffer",
                    "1 uL DNA Mix",
                    "0.5 uL T4 DNA ligase",
                    f"0.5 uL {operation['enzyme']}",
                ],
                "source": [
                    {"dna": operation["vector"], "location": ""},
                    {"dna": operation["insert"], "location": ""},
                ],
                "samples": [
                    {
                        "label": label,
                        "fragments": f"{operation['vector']},{operation['insert']}",
                        "product": operation["output"],
                    }
                ],
                "destination": self.default_destination_by_op["GoldenGate"],
                "program": self.default_program_by_op["GoldenGate"],
                "notes": self.default_notes_by_op["GoldenGate"],
            }

        if step_type == "Gibson":
            return {
                "title": f"{thread_letter}: Assemble",
                "operation": "Gibson",
                "dna_mix": [
                    f"5 uL {operation['vector']}",
                    f"5 uL {operation['insert']}",
                ],
                "reaction": [
                    "4 uL ddH2O",
                    "1 uL DNA Mix",
                    "5 uL 2X Gibson Mix",
                ],
                "source": [
                    {"dna": operation["vector"], "location": ""},
                    {"dna": operation["insert"], "location": ""},
                ],
                "samples": [
                    {
                        "label": label,
                        "fragments": f"{operation['vector']},{operation['insert']}",
                        "product": operation["output"],
                    }
                ],
                "destination": self.default_destination_by_op["Gibson"],
                "program": self.default_program_by_op["Gibson"],
                "notes": self.default_notes_by_op["Gibson"] + [
                    f"Overlap info: {operation['overlap_info']}"
                ],
            }

        if step_type == "DirectSynthesis":
            return {
                "title": f"{thread_letter}: DirectSynthesis",
                "operation": "DirectSynthesis",
                "samples": [
                    {
                        "label": label,
                        "input": operation["input"],
                        "product": operation["output"],
                    }
                ],
                "instructions": [
                    "Submit the sequence for synthesis/order.",
                    "No bench assembly step is required before receiving the product.",
                ],
                "destination": self.default_destination_by_op["DirectSynthesis"],
                "program": self.default_program_by_op["DirectSynthesis"],
                "notes": self.default_notes_by_op["DirectSynthesis"],
            }

        if step_type == "Transform":
            rescue_required = "yes" if operation["selection"].lower() in {"spec", "spectinomycin"} else "no"
            notes = list(self.default_notes_by_op["Transform"])
            notes.append(f"rescue_required: {rescue_required}")

            return {
                "title": f"{thread_letter}: Transform",
                "operation": "Transform",
                "source": [
                    {"label": operation["construct"], "location": ""}
                ],
                "samples": [
                    {
                        "label": label,
                        "product": operation["construct"],
                        "strain": operation["cells"],
                        "antibiotic": operation["selection"],
                        "incubate": f"{operation['temperature_c']}°C",
                    }
                ],
                "destination": self.default_destination_by_op["Transform"],
                "program": self.default_program_by_op["Transform"],
                "notes": notes,
            }

        raise ValueError(f"Unsupported step_type '{step_type}'.")

    def _render_lab_sheet_text(self, lab_sheets: List[Dict[str, Any]]) -> str:
        """
        Render lecture-style text output.
        """
        blocks: List[str] = []

        for sheet in lab_sheets:
            lines: List[str] = [sheet["title"]]

            if "dna_mix" in sheet:
                lines.append("DNA Mix:")
                lines.extend(sheet["dna_mix"])

            if "reaction" in sheet:
                lines.append("reaction:")
                lines.extend(sheet["reaction"])

            if "samples" in sheet and sheet["samples"]:
                lines.append("samples:")
                headers = list(sheet["samples"][0].keys())
                lines.append(" ".join(headers))
                for row in sheet["samples"]:
                    lines.append(" ".join(str(row.get(h, "")) for h in headers))

            if "source" in sheet and sheet["source"]:
                lines.append("source:")
                headers = list(sheet["source"][0].keys())
                lines.append(" ".join(headers))
                for row in sheet["source"]:
                    lines.append(" ".join(str(row.get(h, "")) for h in headers))

            if "instructions" in sheet and sheet["instructions"]:
                lines.append("Instructions:")
                lines.extend(sheet["instructions"])

            if sheet.get("destination"):
                lines.append(f"destination: {sheet['destination']}")

            if sheet.get("program"):
                lines.append(f"program: {sheet['program']}")

            for note in sheet.get("notes", []):
                lines.append("note:")
                lines.append(note)

            blocks.append("\n".join(lines))

        return "\n\n".join(blocks)

    def run(
        self,
        construction_file_txt: str,
        thread_letter: str = "A",
        include_text_render: bool = True,
    ) -> dict:
        self._require_nonempty_string(construction_file_txt, "construction_file_txt")
        self._require_nonempty_string(thread_letter, "thread_letter")

        operations = self._parse_operation_lines(construction_file_txt)

        if not operations:
            raise ValueError("No supported operations were found in construction_file_txt.")

        lab_sheets: List[Dict[str, Any]] = []
        for i, operation in enumerate(operations, start=1):
            lab_sheets.append(
                self._build_lab_sheet_for_operation(
                    operation=operation,
                    thread_letter=thread_letter,
                    index=i,
                )
            )

        result = {
            "lab_sheets": lab_sheets,
            "notes": [
                "Lab sheets were generated from rendered construction file text.",
                "This tool formats planning output and does not validate biological correctness."
            ]
        }

        if include_text_render:
            result["lab_sheet_txt"] = self._render_lab_sheet_text(lab_sheets)

        return result


_instance = LabSheetCreator()
_instance.initiate()
lab_sheet_creator = _instance.run