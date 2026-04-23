class CreateConstructionFile:
    """
    Description:
        Generate a construction file for a simple E_coli cloning workflow.
        This tool accepts user-facing build inputs and internally creates the
        structured parts list, workflow operations, and rendered construction file.

    Input:
        construct_name (str): Name of the final construct.
        assembly_strategy (str): Main assembly strategy. Supported:
            GoldenGate, Gibson, DirectSynthesis.
        backbone_name (str): Name of the backbone plasmid.
        backbone_sequence (str): Backbone plasmid sequence.
        insert_name (str): Name of the insert or donor.
        insert_sequence (str): Insert or donor sequence.

        insert_forward_primer_name (str): Name of insert forward primer.
        insert_forward_primer_sequence (str): Sequence of insert forward primer.
        insert_reverse_primer_name (str): Name of insert reverse primer.
        insert_reverse_primer_sequence (str): Sequence of insert reverse primer.

        vector_forward_primer_name (str): Name of vector forward primer.
        vector_forward_primer_sequence (str): Sequence of vector forward primer.
        vector_reverse_primer_name (str): Name of vector reverse primer.
        vector_reverse_primer_sequence (str): Sequence of vector reverse primer.

        enzyme (str): Assembly enzyme, used for GoldenGate.
        cell_strain (str): Transformation strain.
        selection (str): Selection marker, such as Kan or Amp.
        temperature_c (int): Transformation temperature in Celsius.
        notes (str): Optional notes.

    Output:
        dict: A structured construction file and a rendered text-based construction file.
    """

    def initiate(self) -> None:
        self.supported_organisms = {"E_coli"}
        self.allowed_strategies = {"GoldenGate", "Gibson", "DirectSynthesis"}
        self.allowed_part_types = {"oligo", "primer", "dsdna", "plasmid", "fragment"}
        self.allowed_step_types = {"PCR", "GoldenGate", "Gibson", "DirectSynthesis", "Transform"}

    def run(
        self,
        construct_name: str,
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
        notes: str = ""
    ) -> dict:

        self._require_nonempty_string(construct_name, "construct_name")
        self._require_nonempty_string(assembly_strategy, "assembly_strategy")
        self._require_nonempty_string(backbone_name, "backbone_name")
        self._require_nonempty_string(backbone_sequence, "backbone_sequence")
        self._require_nonempty_string(insert_name, "insert_name")
        self._require_nonempty_string(insert_sequence, "insert_sequence")

        assembly_strategy = self._normalize_assembly_strategy(assembly_strategy)

# Fail early if seq_params did not resolve properly
        for field_name, seq_value in (
            ("backbone_sequence", backbone_sequence),
            ("insert_sequence", insert_sequence),
        ):
            if isinstance(seq_value, str) and seq_value.strip().startswith("resource://"):
                raise ValueError(
                    f"{field_name} was not resolved from the resource before validation."
                )

        if assembly_strategy not in self.allowed_strategies:
            raise ValueError(
                f"assembly_strategy must be one of {sorted(self.allowed_strategies)}."
            )

        self._validate_user_inputs(
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

        parts = self._build_parts(
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

        validated_parts = self._validate_parts(parts)

        operations = self._build_operations(
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

        validated_operations = self._validate_operations(operations, validated_parts)
        construction_file_txt = self._render_construction_file(
            validated_parts,
            validated_operations
        )

        structured_construction_file = {
            "construct_name": construct_name,
            "assembly_strategy": assembly_strategy,
            "parts": validated_parts,
            "operations": validated_operations,
            "notes": notes,
        }

        file_name = f"{construct_name}_construction.txt"

        return {
            "construct_name": construct_name,
            "assembly_strategy": assembly_strategy,
            "file_name": file_name,
            "structured_construction_file": structured_construction_file,
            "construction_file_txt": construction_file_txt,
            "text": construction_file_txt,
        }
    

    def _require_nonempty_string(self, value: str, field_name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string.")

    def _validate_user_inputs(
        self,
        assembly_strategy: str,
        insert_forward_primer_name: str,
        insert_forward_primer_sequence: str,
        insert_reverse_primer_name: str,
        insert_reverse_primer_sequence: str,
        vector_forward_primer_name: str,
        vector_forward_primer_sequence: str,
        vector_reverse_primer_name: str,
        vector_reverse_primer_sequence: str,
        enzyme: str,
    ) -> None:
        if assembly_strategy in {"GoldenGate", "Gibson"}:
            required_pairs = [
                ("insert_forward_primer", insert_forward_primer_name, insert_forward_primer_sequence),
                ("insert_reverse_primer", insert_reverse_primer_name, insert_reverse_primer_sequence),
                ("vector_forward_primer", vector_forward_primer_name, vector_forward_primer_sequence),
                ("vector_reverse_primer", vector_reverse_primer_name, vector_reverse_primer_sequence),
            ]

            missing_fields = []

            for label, primer_name, primer_seq in required_pairs:
                if not primer_name.strip():
                    missing_fields.append(f"{label}_name")
                if not primer_seq.strip():
                    missing_fields.append(f"{label}_sequence")

            if assembly_strategy == "GoldenGate" and not enzyme.strip():
                missing_fields.append("enzyme")

            if missing_fields:
                raise ValueError(
                    "Missing required fields for "
                    f"{assembly_strategy}: {', '.join(missing_fields)}."
                )

        if assembly_strategy == "GoldenGate" and not enzyme.strip():
            raise ValueError("enzyme is required for GoldenGate workflows.")

    def _build_parts(
        self,
        backbone_name: str,
        backbone_sequence: str,
        insert_name: str,
        insert_sequence: str,
        insert_forward_primer_name: str,
        insert_forward_primer_sequence: str,
        insert_reverse_primer_name: str,
        insert_reverse_primer_sequence: str,
        vector_forward_primer_name: str,
        vector_forward_primer_sequence: str,
        vector_reverse_primer_name: str,
        vector_reverse_primer_sequence: str,
    ) -> list:
        parts = [
            {
                "part_type": "plasmid",
                "name": backbone_name,
                "sequence": self._normalize_sequence(backbone_sequence),
                "description": "Backbone plasmid"
            },
            {
                "part_type": "dsdna",
                "name": insert_name,
                "sequence": self._normalize_sequence(insert_sequence),
                "description": "Insert sequence"
            }
        ]

        primer_entries = [
            ("oligo", insert_forward_primer_name, insert_forward_primer_sequence, "Insert forward primer"),
            ("oligo", insert_reverse_primer_name, insert_reverse_primer_sequence, "Insert reverse primer"),
            ("oligo", vector_forward_primer_name, vector_forward_primer_sequence, "Vector forward primer"),
            ("oligo", vector_reverse_primer_name, vector_reverse_primer_sequence, "Vector reverse primer"),
        ]

        for part_type, name, sequence, description in primer_entries:
            if name.strip() and sequence.strip():
                parts.append(
                    {
                        "part_type": part_type,
                        "name": name,
                        "sequence": self._normalize_sequence(sequence),
                        "description": description
                    }
                )

        return parts

    def _build_operations(
        self,
        construct_name: str,
        assembly_strategy: str,
        backbone_name: str,
        insert_name: str,
        insert_forward_primer_name: str,
        insert_reverse_primer_name: str,
        vector_forward_primer_name: str,
        vector_reverse_primer_name: str,
        enzyme: str,
        cell_strain: str,
        selection: str,
        temperature_c: int,
    ) -> list:
        operations = []

        if assembly_strategy in {"GoldenGate", "Gibson"}:
            insert_pcr_product = f"{insert_name}_pcr"
            vector_pcr_product = f"{backbone_name}_pcr"

            operations.append(
                {
                    "step_number": 1,
                    "step_type": "PCR",
                    "inputs": [insert_forward_primer_name, insert_reverse_primer_name, insert_name],
                    "parameters": {
                        "forward_primer": insert_forward_primer_name,
                        "reverse_primer": insert_reverse_primer_name,
                        "template": insert_name
                    },
                    "output": insert_pcr_product
                }
            )

            operations.append(
                {
                    "step_number": 2,
                    "step_type": "PCR",
                    "inputs": [vector_forward_primer_name, vector_reverse_primer_name, backbone_name],
                    "parameters": {
                        "forward_primer": vector_forward_primer_name,
                        "reverse_primer": vector_reverse_primer_name,
                        "template": backbone_name
                    },
                    "output": vector_pcr_product
                }
            )

            if assembly_strategy == "GoldenGate":
                operations.append(
                    {
                        "step_number": 3,
                        "step_type": "GoldenGate",
                        "inputs": [vector_pcr_product, insert_pcr_product],
                        "parameters": {
                            "enzyme": enzyme
                        },
                        "output": construct_name
                    }
                )

            elif assembly_strategy == "Gibson":
                operations.append(
                    {
                        "step_number": 3,
                        "step_type": "Gibson",
                        "inputs": [vector_pcr_product, insert_pcr_product],
                        "parameters": {
                            "overlap_notes": "Primer-designed Gibson overlaps"
                        },
                        "output": construct_name
                    }
                )

        elif assembly_strategy == "DirectSynthesis":
            operations.append(
                {
                    "step_number": 1,
                    "step_type": "DirectSynthesis",
                    "inputs": [insert_name],
                    "parameters": {},
                    "output": construct_name
                }
            )

        if cell_strain.strip() and selection.strip():
            operations.append(
                {
                    "step_number": len(operations) + 1,
                    "step_type": "Transform",
                    "inputs": [construct_name],
                    "parameters": {
                        "cells": cell_strain,
                        "selection": selection,
                        "temperature_c": temperature_c
                    },
                    "output": f"{construct_name}_e"
                }
            )

        return operations

    def _normalize_sequence(self, sequence: str) -> str:
        if not isinstance(sequence, str) or not sequence.strip():
            raise ValueError("sequence must be a non-empty string.")

        raw = sequence.strip()

        # Reject obvious unresolved placeholders / resource names
        # instead of silently converting them into fake DNA.
        if raw.startswith("resource://"):
            raise ValueError(
                f"sequence '{raw}' was not resolved before normalization."
            )

        cleaned = []
        for char in raw.upper():
            if char.isalpha():
                cleaned.append(char)

        cleaned = "".join(cleaned)

        if not cleaned:
            raise ValueError("sequence became empty after normalization.")

        invalid = set(cleaned) - set("ACGTN")
        if invalid:
            raise ValueError(
                "sequence contains invalid DNA characters or appears to be an unresolved "
                f"resource/placeholder: {sorted(invalid)}"
            )

        return cleaned

    def _validate_parts(self, parts: list) -> list:
        validated = []
        seen_names = set()

        for part in parts:
            if not isinstance(part, dict):
                raise ValueError("Each part must be a dictionary.")

            for field in ("part_type", "name", "sequence"):
                if field not in part:
                    raise ValueError(f"Each part must include '{field}'.")

            part_type = part["part_type"]
            name = part["name"]
            sequence = part["sequence"]
            description = part.get("description", "")

            if part_type not in self.allowed_part_types:
                raise ValueError(f"Invalid part_type '{part_type}'.")

            if name in seen_names:
                raise ValueError(f"Duplicate part name '{name}'.")
            seen_names.add(name)

            cleaned_sequence = self._normalize_sequence(sequence)

            validated.append(
                {
                    "part_type": part_type,
                    "name": name,
                    "sequence": cleaned_sequence,
                    "description": description
                }
            )

        return validated

    def _validate_step_specific_fields(
        self,
        step_number: int,
        step_type: str,
        inputs: list,
        parameters: dict
    ) -> None:
        if step_type == "PCR":
            required = {"forward_primer", "reverse_primer", "template"}
            missing = [field for field in required if field not in parameters]
            if missing:
                raise ValueError(
                    f"PCR step {step_number} missing required parameter(s): {missing}."
                )

        elif step_type == "GoldenGate":
            if len(inputs) < 2:
                raise ValueError(
                    f"GoldenGate step {step_number} requires at least 2 inputs."
                )
            if "enzyme" not in parameters:
                raise ValueError(
                    f"GoldenGate step {step_number} requires 'enzyme'."
                )

        elif step_type == "Gibson":
            if len(inputs) < 2:
                raise ValueError(
                    f"Gibson step {step_number} requires at least 2 inputs."
                )
            if "overlap_bp" not in parameters and "overlap_notes" not in parameters:
                raise ValueError(
                    f"Gibson step {step_number} requires 'overlap_bp' or 'overlap_notes'."
                )

        elif step_type == "DirectSynthesis":
            if len(inputs) != 1:
                raise ValueError(
                    f"DirectSynthesis step {step_number} should have exactly 1 input."
                )

        elif step_type == "Transform":
            if len(inputs) != 1:
                raise ValueError(
                    f"Transform step {step_number} should have exactly 1 input."
                )

            required = {"cells", "selection"}
            missing = [field for field in required if field not in parameters]
            if missing:
                raise ValueError(
                    f"Transform step {step_number} missing required parameter(s): {missing}."
                )

    def _validate_operations(self, operations: list, parts: list) -> list:
        validated = []
        part_names = {part["name"] for part in parts}
        produced_outputs = set()
        seen_steps = set()

        sorted_ops = sorted(operations, key=lambda op: op.get("step_number", 0))

        for op in sorted_ops:
            if not isinstance(op, dict):
                raise ValueError("Each operation must be a dictionary.")

            for field in ("step_number", "step_type", "inputs", "output"):
                if field not in op:
                    raise ValueError(f"Each operation must include '{field}'.")

            step_number = op["step_number"]
            step_type = op["step_type"]
            inputs = op["inputs"]
            output = op["output"]
            parameters = op.get("parameters", {})
            description = op.get("description", "")

            if not isinstance(step_number, int):
                raise ValueError("step_number must be an integer.")

            if step_number in seen_steps:
                raise ValueError(f"Duplicate step_number '{step_number}'.")
            seen_steps.add(step_number)

            if step_type not in self.allowed_step_types:
                raise ValueError(f"Invalid step_type '{step_type}'.")

            if not isinstance(inputs, list):
                raise ValueError("inputs must be a list.")

            if not isinstance(output, str) or not output.strip():
                raise ValueError("output must be a non-empty string.")

            if not isinstance(parameters, dict):
                raise ValueError("parameters must be a dictionary.")

            available_names = part_names | produced_outputs
            for item in inputs:
                if item not in available_names:
                    raise ValueError(
                        f"Operation step {step_number} references unknown input '{item}'."
                    )

            self._validate_step_specific_fields(step_number, step_type, inputs, parameters)

            validated.append(
                {
                    "step_number": step_number,
                    "step_type": step_type,
                    "inputs": inputs,
                    "parameters": parameters,
                    "output": output,
                    "description": description
                }
            )

            produced_outputs.add(output)

        return validated

    def _render_construction_file(self, parts: list, operations: list) -> str:
        lines = []

        def _shorten(seq: str, max_len: int = 40) -> str:
            if len(seq) <= max_len:
                return seq
            return f"{seq[:20]}...{seq[-20:]} ({len(seq)} bp)"

        for op in operations:
            step_type = op["step_type"]
            inputs = op["inputs"]
            parameters = op["parameters"]
            output = op["output"]

            if step_type == "PCR":
                lines.append(
                    f"{'PCR':<14}"
                    f"{parameters.get('forward_primer', ''):<14}"
                    f"{parameters.get('reverse_primer', ''):<14}"
                    f"{parameters.get('template', ''):<18}"
                    f"{output}"
                )

            elif step_type == "GoldenGate":
                lines.append(
                    f"{'GoldenGate':<14}"
                    f"{inputs[0] if len(inputs) > 0 else '':<14}"
                    f"{inputs[1] if len(inputs) > 1 else '':<14}"
                    f"{parameters.get('enzyme', ''):<18}"
                    f"{output}"
                )

            elif step_type == "Gibson":
                overlap_value = str(
                    parameters.get("overlap_bp", parameters.get("overlap_notes", ""))
                )
                lines.append(
                    f"{'Gibson':<14}"
                    f"{inputs[0] if len(inputs) > 0 else '':<14}"
                    f"{inputs[1] if len(inputs) > 1 else '':<14}"
                    f"{overlap_value:<18}"
                    f"{output}"
                )

            elif step_type == "DirectSynthesis":
                lines.append(
                    f"{'DirectSynthesis':<18}"
                    f"{inputs[0] if inputs else '':<16}"
                    f"{output}"
                )

            elif step_type == "Transform":
                lines.append(
                    f"{'Transform':<14}"
                    f"{inputs[0] if inputs else '':<22}"
                    f"{parameters.get('cells', ''):<12}"
                    f"{parameters.get('selection', ''):<10}"
                    f"{str(parameters.get('temperature_c', '')):<8}"
                    f"{output}"
                )

        lines.append("")

        for part in parts:
            if part["part_type"] == "oligo":
                seq_display = part["sequence"]
            else:
                seq_display = _shorten(part["sequence"])

            lines.append(
                f"{part['part_type']:<14}"
                f"{part['name']:<14}"
                f"{seq_display}"
            )

        return "\n".join(lines)
    
    
    def _normalize_assembly_strategy(self, strategy: str) -> str:
        if not isinstance(strategy, str) or not strategy.strip():
            raise ValueError("assembly_strategy must be a non-empty string.")

        s = strategy.strip().lower().replace("_", "").replace(" ", "")

        mapping = {
            "goldengate": "GoldenGate",
            "gibson": "Gibson",
            "directsynthesis": "DirectSynthesis",
        }

        return mapping.get(s, strategy.strip())


_instance = CreateConstructionFile()
_instance.initiate()
create_construction_file = _instance.run

def prompt_optional(prompt_text: str) -> str:
    value = input(prompt_text).strip()
    return value


def prompt_required(prompt_text: str) -> str:
    value = input(prompt_text).strip()
    while not value:
        print("This field is required.")
        value = input(prompt_text).strip()
    return value


def prompt_int(prompt_text: str, default: int = 37) -> int:
    value = input(f"{prompt_text} [{default}]: ").strip()
    if not value:
        return default

    while True:
        try:
            return int(value)
        except ValueError:
            value = input("Please enter an integer: ").strip()


def main() -> None:
    print("=== Construction File Generator ===")
    print("Leave optional fields blank if they are not needed.\n")

    construct_name = prompt_required("Construct name: ")
    assembly_strategy = prompt_required(
        "Assembly strategy (GoldenGate, Gibson, DirectSynthesis): "
    )

    backbone_name = prompt_required("Backbone name: ")
    backbone_sequence = prompt_required("Backbone sequence: ")
    insert_name = prompt_required("Insert name: ")
    insert_sequence = prompt_required("Insert sequence: ")

    insert_forward_primer_name = ""
    insert_forward_primer_sequence = ""
    insert_reverse_primer_name = ""
    insert_reverse_primer_sequence = ""
    vector_forward_primer_name = ""
    vector_forward_primer_sequence = ""
    vector_reverse_primer_name = ""
    vector_reverse_primer_sequence = ""
    enzyme = ""

    if assembly_strategy in {"GoldenGate", "Gibson"}:
        print("\n--- Primer information required for this strategy ---")
        insert_forward_primer_name = prompt_required("Insert forward primer name: ")
        insert_forward_primer_sequence = prompt_required("Insert forward primer sequence: ")
        insert_reverse_primer_name = prompt_required("Insert reverse primer name: ")
        insert_reverse_primer_sequence = prompt_required("Insert reverse primer sequence: ")

        vector_forward_primer_name = prompt_required("Vector forward primer name: ")
        vector_forward_primer_sequence = prompt_required("Vector forward primer sequence: ")
        vector_reverse_primer_name = prompt_required("Vector reverse primer name: ")
        vector_reverse_primer_sequence = prompt_required("Vector reverse primer sequence: ")

    if assembly_strategy == "GoldenGate":
        enzyme = prompt_required("Assembly enzyme: ")

    print("\n--- Optional transformation information ---")
    cell_strain = prompt_optional("Cell strain: ")
    selection = prompt_optional("Selection marker: ")
    temperature_c = prompt_int("Transformation temperature (C)", default=37)
    notes = prompt_optional("Notes: ")

    try:
        result = create_construction_file(
            construct_name=construct_name,
            assembly_strategy=assembly_strategy,
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
            enzyme=enzyme,
            cell_strain=cell_strain,
            selection=selection,
            temperature_c=temperature_c,
            notes=notes,
        )

        print("\n=== Construction file generated ===")
        print(f"File name: {result['file_name']}\n")
        print(result["construction_file_txt"])

        save_choice = input("\nSave to file? (y/n): ").strip().lower()
        if save_choice == "y":
            with open(result["file_name"], "w") as f:
                f.write(result["construction_file_txt"])
            print(f"Saved to {result['file_name']}")

    except ValueError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()