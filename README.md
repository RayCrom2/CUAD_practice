# CUAD Contract Clause Extraction

An LLM-based agent that extracts legal clauses from real commercial contracts, evaluated against
expert annotations from the [CUAD](https://www.atticusprojectai.org/cuad) dataset. The goal isn't a
one-shot demo — it's a measured pipeline: extract, score against expert ground truth, find specific
failure modes, fix them, and show the numbers move.

**Dataset**: CUAD (Contract Understanding Atticus Dataset) — 510 real commercial contracts pulled
from SEC filings, with 13,000+ expert-attorney annotations across 41 legal clause types. CC-BY 4.0
licensed; not included in this repo (see [Setup](#setup)).

## Current status: Phase 1.3 complete (Governing Law clause)

The project deliberately scoped down to a single clause type — Governing Law — to build out the
full extract → evaluate → diagnose → fix loop on a tractable problem before scaling to others.

| Version | Approach | Accuracy (n=50) | Input tokens | Est. cost |
|---|---|---|---|---|
| 1.1 | Send the entire contract as context | 100% (baseline) | 712,453 | ~$2.18 |
| 1.2 | Send only the matching section (first N keyword hits, in document order) | 94% (47/50) | 446,812 | ~$1.38 |
| 1.3 | Ranked section selection + keyword-windowing fallback + hardened prompt + jurisdiction-aware scoring | **100% (50/50)** | **261,920** | **~$0.82** |

1.2 cut cost but lost accuracy. 1.3 recovers full accuracy *and* roughly doubles the token savings
versus 1.2 — see [output/](output/) for the full per-contract run logs behind each number.

### What 1.3 actually fixed (not just re-tuned)

- **Ranked section selection, not first-N-in-document-order.** Candidate sections are scored (a
  header that literally says "Governing Law" > a line stating "this Agreement ... shall be governed
  by ..." > a bare keyword like "jurisdiction"/"venue" used for something unrelated) instead of
  greedily keeping the first 3 keyword hits. Generic phrases like "jurisdiction" and "laws of the
  State of X" show up constantly in unrelated boilerplate (indemnification, entity formation,
  mediator qualifications) and were crowding the real clause out of the section budget.
- **Keyword-windowing fallback for unstructured contracts.** 19 of the 50 contracts have no real
  internal line-break structure to split on — section detection degenerates to "the whole document
  is one section," which means sending 100% of it. These now get ~100-word windows around each
  governing-law-style match instead. This was the single largest driver of the additional token
  reduction in 1.3.
- **Anti-paraphrase, anti-commentary prompt.** The model was occasionally finding the right
  jurisdiction but rephrasing the clause in its own words (failing a verbatim-match scorer), or
  returning explanatory text instead of an empty response when it found nothing. The prompt now
  explicitly forbids both.
- **Jurisdiction-aware scoring fallback.** Some contracts have more than one real, verbatim,
  jurisdiction-correct governing-law sentence (e.g. a termination-agreement clause *and* a main
  agreement clause), and CUAD only labels one. A prediction now also counts as correct if it names
  the same jurisdiction as gold, even when the exact clause text differs — this is a one-way safety
  net (it can only convert a miss into a hit, never the reverse) but is a real loosening of what
  "accuracy" means, documented in the run log.

## Repo structure

```
inspect_cuad.py                  Load & inspect the raw CUAD_v1.json structure
inspect_contract_structure.py    Print one contract with clause/section markers for manual review
phase1.1_governing_law.py        Baseline: full-context extraction + scoring
phase1.2_governing_law.py        Token-reduction iteration (section snippets)
phase1.3_governing_law.py        Current: ranked sections, windowing fallback, hardened prompt,
                                  jurisdiction-aware scoring, --indices for targeted re-tests
phase2.1_governing_law.py        Starting point for Phase 2 (hallucination-rate testing)
output/                          Raw run logs for each version
```

## Setup

```bash
python3 -m pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."   # or put it in a .env file (gitignored)
```

Download `CUAD_v1.json` from the [Atticus Project's GitHub](https://github.com/TheAtticusProject/cuad)
(`data/CUAD_v1.json`) — it's not bundled in this repo.

## Usage

```bash
# Full run with token/cost tracking
python3 phase1.3_governing_law.py /path/to/CUAD_v1.json --n 50 --show-usage \
    --input-price-per-1m 3.0 --output-price-per-1m 15.0

# Re-test specific contracts only (cheap — useful for debugging a known miss)
python3 phase1.3_governing_law.py /path/to/CUAD_v1.json --indices 22 23 39

# Inspect a single contract's raw structure (1-based, same numbering as --indices)
python3 inspect_contract_structure.py /path/to/CUAD_v1.json 22
```

## Roadmap

- **Phase 2** (in progress): formal eval harness — hallucination-rate testing on the 73 contracts
  with no Governing Law clause, plus precision/recall/F1.
- **Phase 3**: scale to the other starter clause types (Effective Date, Term, Termination for
  Convenience, Cap on Liability) and add retrieval for long contracts.
- **Phase 4**: failure analysis and iteration across all clause types.
- **Phase 5**: agentic orchestration (tool use, retries) + a feedback loop.
- **Phase 6**: polish for presentation.
