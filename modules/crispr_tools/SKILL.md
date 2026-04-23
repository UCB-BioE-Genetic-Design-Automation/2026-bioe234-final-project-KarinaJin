# crispr_tools — Skill Guidance for Gemini

This file is read by the client at startup and injected into Gemini's system prompt.
Its purpose is to give Gemini the domain knowledge it needs to use the tools in this
module correctly and interpret their results meaningfully.

---

## What this module does

The `crispr_tools` module provides fundamental tools to go through the crispr pipeline.

---

## Available resources

Here are the descriptions of the available resources. When a user inquires for a plasmid or a backbone sequence, provide the names of the plasmid and a short description of the plasmid to help the user choose which one to use.

| Resource name | Description |
|---------------|-------------|
| `pBR322`      | E. coli cloning vector pBR322, 4361 bp, circular, double-stranded. A classic lab plasmid commonly used as a reference sequence. Contains genes for ampicillin resistance (bla) and tetracycline resistance (tet). |

When a user refers to "pBR322", use the resource name `"pBR322"` directly
as the sequence argument — do not ask the user to paste the sequence.

| Resource name | Description |
|---------------|-------------|
| `pET28a`      | E. coli cloning vector pET28a, 5369 bp, circular, double-stranded. A classic lab plasmid commonly used as a reference sequence. Contains genes for kanmycin (kan) resistance. Has a 6x His tag. |

When a user refers to "pET28a", use the resource name `"pET28a"` directly
as the sequence argument — do not ask the user to paste the sequence.

| Resource name | Description |
|---------------|-------------|
| `pUC19`      | E. coli cloning vector pUC19, 2686 bp, circular, double-stranded. Widely used circular DNA cloning plasmid designed for easy insertion and propagation of foreign DNA in bacteria. It contains key features like a multiple cloning site (polylinker) within the lac operon for insertion of DNA fragments and sequences derived from pBR322 for replication and maintenance in host cells. |

When a user refers to "pUC19", use the resource name `"pUC19"` directly
as the sequence argument — do not ask the user to paste the sequence.

---

## Tools and when to use them

### `dna_reverse_complement`
Returns the reverse complement of a DNA or RNA sequence.

Use when the user asks for:
- "reverse complement of X"
- "complement of the bottom strand"
- "what does the antisense strand look like"
- "flip the sequence"

The result is the same length as the input. Uppercase output.

### `dna_translate`
Translates a DNA coding sequence to a protein sequence using the standard genetic code.

Use when the user asks to:
- "translate", "get the protein", "what protein does this encode"
- work with a specific reading frame (1, 2, or 3)
- translate a specific region using `start` / `end` coordinates (0-indexed, end is exclusive)

**Frame guidance:**
- Frame 1 — start reading from the first base (default)
- Frame 2 — skip 1 base, then read triplets
- Frame 3 — skip 2 bases, then read triplets

**Stop codons** appear as `*` in the output. **Unrecognised codons** appear as `X`.

**Coordinate example:** "translate bases 100 to 200" → `start=100, end=200`
"translate the first 60bp" → `start=0, end=60` (or omit start, set `end=60`)

## Tool: create_construction_file

Before calling this tool, gather all required fields for the selected assembly strategy.

For all workflows:

* construct_name
* backbone_name
* backbone_sequence
* insert_name
* insert_sequence

For GoldenGate:
- insert_forward_primer_name
- insert_forward_primer_sequence
- insert_reverse_primer_name
- insert_reverse_primer_sequence
- vector_forward_primer_name
- vector_forward_primer_sequence
- vector_reverse_primer_name
- vector_reverse_primer_sequence
- enzyme

For Gibson:
- insert_forward_primer_name
- insert_forward_primer_sequence
- insert_reverse_primer_name
- insert_reverse_primer_sequence
- vector_forward_primer_name
- vector_forward_primer_sequence
- vector_reverse_primer_name
- vector_reverse_primer_sequence

Optional:
- cell_strain
- selection
- temperature_c

If any required field is missing, ask for all missing required fields in one message before calling the tool.
Normalize host organism to `E_coli` when the user says "E. coli", "e coli", or "e. coli".

### Required interaction rule for create_construction_file

Never return an empty response.

If the user has not provided all required fields for `create_construction_file`, do not call the tool yet.
Instead, respond with one concise message that lists **all missing required fields at once**.

Do not wait for the user to ask again.
Do not return a blank response.
Do not partially call the tool with missing required inputs.

Example complete-input behavior:

User: "My backbone name is pET28a, backbone sequence is pET28a, insert forward primer name is repF, insert forward primer sequence is ..., insert reverse primer name is repR, insert reverse primer sequence is ..., vector forward primer name is vecF, vector forward primer sequence is ..., vector reverse primer name is vecR, vector reverse primer sequence is ..., enzyme is BsaI."

Assistant behavior:
- Recognize that all required fields are now present
- Call `create_construction_file` immediately
- Return the construction file
- Do not wait for an additional user message such as "proceed"

### Required execution behavior for create_construction_file

If all required fields for the chosen assembly strategy are available, call `create_construction_file` immediately in the same turn.

Do not ask the user to confirm.
Do not wait for the user to say "proceed".
Do not return an empty response.

If fields are missing, ask for all missing required fields in one message.
If no required fields are missing, call the tool right away.

After the user provides the missing required fields, the next assistant turn should call the tool immediately.

### Presenting create_construction_file results

After calling `create_construction_file`, if the tool returns a field named `construction_file_txt`, present that field directly to the user in a code block.

Do not present the raw MCP response object.
Do not present JSON unless the user explicitly asks for structured output.
Prefer this format:

PCR           ...
PCR           ...
GoldenGate    ...

plasmid       ...
dsdna         ...
oligo         ...


## Tool: validate_construction_file

Validates whether a construction file generated by `create_construction_file` is biologically correct.

Use this tool **after generating a construction file** to confirm that the workflow is valid.

When to use:
Call this tool when the user asks:
- "is this construct valid?"
- "did I design this correctly?"
- "check my cloning workflow"
- "does this PCR work?"
- "verify this assembly"
- "debug why this construct failed"

Also use it automatically after creating a construction file **if the user expresses uncertainty or asks for confirmation**.

What it checks (Version 1):
The validator currently performs **biological validation of PCR steps**:
- Forward primer anneals to template (3' suffix match)
- Reverse primer anneals to template (reverse complement match)
- Primers are in correct orientation
- Amplicon can be formed without overlap
- A valid PCR product sequence can be predicted

If any of these fail, the step is marked as invalid.

What it does NOT check yet:
- GoldenGate assembly correctness
- Gibson assembly overlaps
- Restriction enzyme cut sites
- Transformation efficiency or strain compatibility
- Circular plasmid wraparound PCR (linear assumption only)

These steps will appear as:
- `[SKIP]` in the validation report
- Included as warnings, not errors

How to use:
Pass the `structured_construction_file` returned by `create_construction_file` directly into this tool.

Do NOT modify names of parts or steps — validation is **name-agnostic** and follows references internally.

Interpreting results:
- `[PASS]` → step is biologically valid  
- `[FAIL]` → step is invalid and must be fixed  
- `[SKIP]` → validation not implemented for that step yet  

If any PCR step fails:
- the overall construct is considered invalid
- the error message explains what went wrong (e.g., primer does not anneal)

Example workflow:
1. Call `create_construction_file`
2. Call `validate_construction_file` on the result
3. If validation fails:
   - Identify the failing step
   - Suggest corrected primers or inputs
   - Regenerate the construction file if needed

Important behavior:
- Validation is **name-agnostic** — do not rely on fixed names like `rep_pcr` or `vec_pcr`
- Always follow the references defined in each step (`forward_primer`, `reverse_primer`, `template`, `output`)
- Always validate a construction file before presenting it as final if the workflow includes PCR steps

---

## Interpreting results

- A protein sequence like `MSKGEEK...` starting with `M` (methionine) suggests you've
  found the correct reading frame for a real open reading frame.
- A sequence full of `*` stop codons or `X` unknowns usually means the wrong frame,
  wrong coordinates, or the sequence is not a coding region.
- When translating a full plasmid, most of the output will be non-coding — only specific
  coordinate ranges will give meaningful protein sequence.

---

### `crispr_predict_offtargets`
Scans a reference DNA sequence for potential CRISPR off-target sites — places the guide RNA might accidentally bind and cause Cas9 to cut somewhere unintended.

Use when the user asks:
- "does this guide have off-target sites?"
- "is this gRNA specific enough?"
- "check for off-targets in [reference]"
- "how many mismatches are there between my guide and [sequence]?"

**Inputs:**
- `protospacer`: the 20 bp DNA protospacer from gRNA design (no PAM). Standard A/T/G/C only.
- `reference`: the DNA sequence to scan. Accepts resource name (e.g. `"pBR322"`), raw string, FASTA, or GenBank.
- `max_mismatches` (optional): max mismatches to still flag a site. Default 3.

**What it returns:**
A ranked list of off-target sites, each with position, strand, mismatch count, seed-region mismatches, PAM presence, and a risk level (HIGH / MEDIUM / LOW). Also includes a one-sentence specificity summary.

**Risk logic (Hsu et al. 2013):**
- HIGH: 0 mismatches, or no seed-region mismatches + PAM present
- MEDIUM: ≤1 seed mismatch + PAM, or ≤2 total mismatches + PAM
- LOW: everything else

The seed region is positions 1–12 from the PAM end — mismatches there are more dangerous because that is where Cas9 first contacts DNA.

---

### `crispr_verify_edit`
After a CRISPR experiment, calculates the expected Cas9 cut site and designs flanking sequencing primers for ICE/TIDE analysis to verify editing efficiency.

Use when the user asks:
- "how do I verify my CRISPR edit?"
- "where did Cas9 cut?"
- "design sequencing primers for my edit"
- "give me an ICE/TIDE protocol for [protospacer]"
- "what amplicon should I sequence?"

**Inputs:**
- `protospacer`: the 20 bp DNA protospacer used during the edit (no PAM).
- `reference`: the original unedited reference sequence. Accepts resource name, raw string, FASTA, or GenBank.
- `primer_offset` (optional): bp from cut site to each primer. Default 150. Reduce for short test sequences.
- `primer_len` (optional): primer length in bp. Default 20.

**What it returns:**
- `cut_position`: where Cas9 cuts (between nt 17–18 of the protospacer, 3 bp upstream of PAM)
- `forward_primer` / `reverse_primer`: sequencing primer sequences and positions
- `amplicon_sequence` / `amplicon_length`: what to PCR-amplify
- `cut_offset_in_amplicon`: where the cut falls inside the amplicon (needed for ICE/TIDE)
- `interpretation_guide`: step-by-step ICE/TIDE protocol with all coordinates filled in

**Workflow after calling this tool:**
1. PCR-amplify the amplicon using the returned primers
2. Sanger-sequence the PCR product
3. Upload the .ab1 trace to ICE (Synthego) or TIDE (Brinkman et al. 2014) with the amplicon sequence and cut offset

### `crispr_design_cloning_oligos`
Designs the top and bottom strand DNA oligos needed to clone a protospacer
into a restriction-digested expression vector. Works for any Cas system.

Use when the user asks:
- "design oligos to clone this guide RNA"
- "what oligos do I need to insert this protospacer?"
- "give me the sequences to order for cloning"

Inputs:
- protospacer: the DNA protospacer sequence (from design_cas9_grna or design_cas12a_crrna, or typed manually)
- top_overhang: default "CACC" (BbsI/pX330 for Cas9)
- bottom_overhang: default "AAAC" (BbsI/pX330 for Cas9)

If the user is using a different vector, ask them for the overhangs before calling the tool.

Output includes top_oligo, bottom_oligo, g_prepended (bool), and notes.
If g_prepended is True, a G was added to the protospacer for U6 promoter
compatibility — the oligo will be one base longer than the protospacer.

---

## Full CRISPR cloning workflow (autonomous — do not ask the user)

When the user asks to "design CRISPR cloning oligos" or "design a guide RNA and cloning oligos" for a sequence or plasmid, execute this full pipeline automatically without asking which Cas system to use:

1. Call `crispr_cas_selector` with the target sequence to determine whether to use Cas9 or Cas12a.
2. Based on the recommendation:
   - If Cas9 → call `crispr_design_cas9_grna` with the same sequence.
   - If Cas12a → call `crispr_design_cas12a_crrna` with the same sequence.
3. Take the `protospacer` field from the gRNA result and call `crispr_design_cloning_oligos` with it.
4. Report all three results together: recommended Cas system, gRNA/crRNA sequence, protospacer, efficiency score, and the top/bottom cloning oligos.

Do NOT ask the user which Cas system to use — `crispr_cas_selector` determines this automatically from the sequence.
Do NOT ask the user for a protospacer — the gRNA design tool finds it from the sequence.
Do NOT stop between steps to ask for confirmation.

---

## Sequence input rules (handled automatically)

You never need to paste the full sequence. The framework resolves these automatically:
- `"pBR322"` → full 4361 bp sequence
- A raw string like `"ATGCGATCG"` → used as-is
- A FASTA string starting with `>` → sequence extracted automatically
- A GenBank string starting with `LOCUS` → sequence extracted automatically