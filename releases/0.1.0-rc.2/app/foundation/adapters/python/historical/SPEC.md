# C0081-03 SPEC

Catalog prompt: `../../Combined-Prompt-Workflow-Catalog/Prompt-Workflow-Catalog-v3.0.0/COMP-component-prompts-and-workflows/core/C0081/C0081-03-assistant-token-count.md` (sha256 0d63cd8645a42aff9aa37363fbc2f26694292d53d2db39076a2f02d5eb3b36c7)

Work type: Measurement

## Purpose
Assistant(-generated) token count n.

## Verified definition
n = number of model-generated tokens (reasoning + natural language + tool calls); tool observations/prompt excluded

## Source locators
- Uploaded article 'Exhaustive Analysis of Technological Concepts and Modes in Compact Coding Agents.pdf' (catalog sources/article.pdf; image-only, no text layer), pp. 2-3 (catalog citation)
- arXiv 2609.07925v2 Sec.4.2 Efficiency Reward

## Input/output contract
- inputs: per-token role labels
- output: int n

## Assumptions and implementation choices (labelled; not source-stated unless cited)
- role taxonomy (reasoning,text,tool_call | prompt,observation) is the fixture's labelling

## Configuration decisions
```json
{}
```

## Acceptance criteria
- Component completion criterion of the catalog prompt (valid/invalid/boundary or measured outcome as applicable) via the independent checks in VALIDATION.md.
- Catalog acceptance checks A1-A6 (evidence/acceptance.json).
