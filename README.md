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

## Phase 2: hallucination-rate testing (in progress)

Phase 1.3 was only ever tested against the 437 contracts confirmed to *have* a Governing
Law clause. Phase 2 closes that blind spot: does the pipeline invent a clause on the 73
contracts where CUAD confirms none exists? Versioned the same way as Phase 1 — each
milestone is its own file and its own dated output log.

| Version | Approach | Absent-set hallucination rate | Present-set accuracy | F1 (both populations) |
|---|---|---|---|---|
| 2.1 | Free-text `NONE` sentinel (iterated from the 1.3 prompt) + a regex bugfix (`venue` matching inside "Avenue") | 14% (10/73) | 100% (50/50) — clean win, no tradeoff | 90.9% |
| 2.2 | Forced tool use (`report_governing_law(found, clause_text)`) instead of free-text parsing, plus a sharpened prompt distinguishing governing-law from forum/venue/dispute-resolution clauses | **3% (2/73)** | **98% (49/50)** | **97.0%** |

The F1 column treats both populations as one binary classification + extraction task —
**precision** (of every contract the model claimed to find a clause in, what fraction were
right: TP/(TP+FP)) and **recall** (of every contract that actually has a clause, what
fraction did it find: TP/(TP+FN)), combined via their harmonic mean rather than a simple
average so an imbalance between the two can't hide behind an artificially decent-looking
score. It turns "8 false positives fixed, 1 false negative introduced" into one honest
number: F1 rose from 90.9% to 97.0%, confirming 2.2's tradeoff was a real net improvement,
not a wash. Computed directly from the saved run logs in
[`explore.ipynb`](explore.ipynb) — no extra API calls. Full derivation in
[output/2.2_output_GL_73.md](output/2.2_output_GL_73.md#precision--recall--f1-across-both-populations).

2.1's free-text sentinel still let commentary leak through in edge cases (e.g. the model
writing a full explanation and only appending `NONE` at the very end, which an exact-match
check didn't catch) — a formatting problem, not a reasoning one. 2.2's tool use eliminates
that category structurally: `found` is read off a typed field instead of inferred from
whether a string happens to be empty. The remaining failures were a real, consistent
pattern: the model confidently mislabeling forum-selection/venue clauses as governing law
(e.g. "any disputes shall be settled in a court in Florida"). Sharpening that distinction
fixed 8 of these — but cost one new miss on the present-clause set (BorrowMoney), whose
CUAD-labeled answer is structurally almost identical to the entity-formation language 1.3
had already taught the model to reject. A genuine precision/recall tradeoff, not a bug —
see [output/2.1_output_GL_73.md](output/2.1_output_GL_73.md)
and [output/2.2_output_GL_73.md](output/2.2_output_GL_73.md)
for both full raw runs.

The 2 remaining absent-set misses in 2.2 aren't model errors: one is a CUAD
labeling-boundary case (the same legal filing split into a base agreement and two
amendments, with the clause labeled only on the base agreement), the other is a
"Guarantee" document with a genuinely variable jurisdiction rather than a fixed named
state.

## Repo structure

```
inspect_cuad.py                  Load & inspect the raw CUADv1.json structure
inspect_contract_structure.py    Print one contract with clause/section markers for manual review
phase1.1_governing_law.py        Baseline: full-context extraction + scoring
phase1.2_governing_law.py        Token-reduction iteration (section snippets)
phase1.3_governing_law.py        Current: ranked sections, windowing fallback, hardened prompt,
                                  jurisdiction-aware scoring, --indices for targeted re-tests
phase2.1_governing_law.py        Phase 2.1: free-text NONE sentinel, hallucination-rate testing
phase2.2_governing_law.py        Phase 2.2: forced tool use + sharpened governing-law-vs-venue
                                  prompt -- current hallucination-rate result
output/                          Raw run logs for each version
```

## Setup

```bash
python3 -m pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."   # or put it in a .env file (gitignored)
```

Download `CUADv1.json` from the [Atticus Project's GitHub](https://github.com/TheAtticusProject/cuad)
(`data/CUADv1.json`) — it's not bundled in this repo.

## Usage

```bash
# Phase 1.3: full run with token/cost tracking
# Prices will vary on model; these prices are based on claude-sonnet-4-5
# Parameter following '--n' is the number of contracts to test (default 20 if not specified)
python3 phase1.3_governing_law.py /path/to/CUADv1.json --n 50 --show-usage \
    --input-price-per-1m 3.0 --output-price-per-1m 15.0

# Re-test specific contracts only (cheap — useful for debugging a known miss)
python3 phase1.3_governing_law.py /path/to/CUADv1.json --indices 22 23 39

# Inspect a single contract's raw structure (1-based, same numbering as --indices)
python3 inspect_contract_structure.py /path/to/CUADv1.json 22

# Phase 2.2: hallucination-rate test on all 73 contracts with no Governing Law clause
python3 phase2.2_governing_law.py /path/to/CUADv1.json --absent --n 73 --show-usage \
    --input-price-per-1m 3.0 --output-price-per-1m 15.0
```

## Roadmap

- **Phase 2** (complete): formal eval harness — hallucination-rate testing (3% on the full
  73-contract absent set) and precision/recall/F1 across both populations (97.0%, see above).
- **Phase 3**: scale to the other starter clause types (Effective Date, Term, Termination for
  Convenience, Cap on Liability) and add retrieval for long contracts.
- **Phase 4**: failure analysis and iteration across all clause types.
- **Phase 5**: agentic orchestration (tool use, retries) + a feedback loop.
- **Phase 6**: polish for presentation.
