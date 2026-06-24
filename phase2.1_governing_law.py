"""
Phase 1 thin slice: extract the Governing Law clause from CUAD contracts
using Claude, then score against the gold labels.

Goal: produce ONE number (accuracy) end-to-end. No retrieval, no agent yet.

Setup:
    pip3 install anthropic --user
    export ANTHROPIC_API_KEY="sk-ant-..."

Run:
    python3 phase1_governing_law.py "/path/to/CUADv1.json"
    python3 phase1_governing_law.py "/path/to/CUADv1.json" --n 30
"""

import sys
import os
import json
import re
import bisect
import argparse

from anthropic import Anthropic

from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())  # reads .env in cwd
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

MODEL = "claude-sonnet-4-5"   # fast + capable; fine for extraction
GOVERNING_LAW = "Governing Law"

# A small dictionary of US states + a few countries so we can check, leniently,
# whether the model identified the right jurisdiction. CUAD answers are almost
# always "the State of X" or a country. This is intentionally simple for Phase 1.
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine",
    "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
    "Washington", "West Virginia", "Wisconsin", "Wyoming",
]
COUNTRIES = [
    "United States", "Canada", "England", "United Kingdom", "Germany",
    "France", "Switzerland", "Ireland", "Australia", "Singapore", "China",
    "Hong Kong", "Japan", "Netherlands", "Israel", "Bermuda",
]
JURISDICTIONS = US_STATES + COUNTRIES

# Strong phrases are a near-certain signal of an actual governing-law sentence.
# Weak phrases (bare "jurisdiction"/"venue") show up constantly in unrelated
# clauses (indemnification, dispute resolution) and were the root cause of
# losing the real GL section in long contracts -- see _section_tier below.
STRONG_GOVERNING_LAW_PATTERNS = [
    r"governed by",
    r"governing law",
    r"laws of the state",
    r"shall be governed",
    r"shall be construed",
    r"law of the state",
]
WEAK_GOVERNING_LAW_PATTERNS = [
    r"jurisdiction",
    r"\bvenue\b",  # word boundary -- bare "venue" without it matches inside "Avenue", "revenue"
]
GOVERNING_LAW_PATTERNS = STRONG_GOVERNING_LAW_PATTERNS + WEAK_GOVERNING_LAW_PATTERNS

# If a SECTION HEADER itself contains one of these, that section is almost
# certainly the governing-law clause regardless of what else matched first.
HEADER_GOVERNING_LAW_PATTERNS = [
    r"governing law",
    r"applicable law",
    r"choice of law",
]

# Sections whose header marks them as navigation/listing rather than actual
# clause text -- e.g. a Table of Contents that lists "Governing Law" as a
# heading title is not the clause itself and should never be a candidate.
NON_CLAUSE_HEADER_PATTERNS = [
    r"table of contents",
    r"^\s*index\s*$",
]

# A real governing-law sentence is about the agreement itself ("This
# Agreement ... shall be governed by ..."). Phrases like "laws of the State
# of X" also show up constantly in unrelated boilerplate -- entity formation
# ("validly existing ... under the laws of the State of Delaware"), mediator
# qualifications, etc. Requiring "this <word> agreement" nearby on the same
# line filters those false positives out.
THIS_AGREEMENT_PATTERN = re.compile(r"\bthis\s+(?:[a-z]+\s+){0,2}agreement\b", re.IGNORECASE)

SECTION_HEADER_PATTERNS = [
    re.compile(r"^\s*Exhibit\s+\d+(?:\.\d+)*\b.*$", re.IGNORECASE),
    re.compile(r"^\s*\d+(?:\.\d+)*\.?\s+[A-Z0-9][A-Z0-9\s,&()'\-/]{2,}$"),
    re.compile(r"^\s*[A-Z0-9][A-Z0-9\s,&()'\-/]{8,}$"),
]


# A few common abbreviations/alternate names that should canonicalize to an
# entry already in JURISDICTIONS, so two clauses naming the same place in
# different words (e.g. "PRC" vs "People's Republic of China") still count
# as the same jurisdiction for scoring purposes.
JURISDICTION_ALIASES = {
    "PRC": "China",
}


def jurisdiction_in(text):
    """Return the set of known jurisdictions (canonical names) mentioned in
    a piece of text, including a few common aliases (see JURISDICTION_ALIASES)."""
    if not text:
        return set()
    found = set()
    for j in JURISDICTIONS:
        # word-boundary, case-insensitive
        if re.search(r"\b" + re.escape(j) + r"\b", text, flags=re.IGNORECASE):
            found.add(j)
    for alias, canonical in JURISDICTION_ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", text, flags=re.IGNORECASE):
            found.add(canonical)
    return found


def clause_overlap(pred, gold):
    """Score prediction vs gold: a hit if the clause text overlaps OR they
    name the same jurisdiction. A contract can have more than one sentence
    that correctly states its governing law (e.g. a separate termination-
    agreement clause, or a restated clause elsewhere) -- raw token overlap
    alone penalizes a verbatim, correct extraction just for landing on a
    different (but equally valid) sentence than the one CUAD happened to
    label.
    """
    if not pred and not gold:
        return True  # both empty is correct
    if not pred or not gold:
        return False  # one empty, one not

    pred_words = set(pred.lower().split())
    gold_words = set(gold.lower().split())

    if not pred_words or not gold_words:
        return False

    overlap = len(pred_words & gold_words)
    min_len = min(len(pred_words), len(gold_words))
    text_hit = overlap / min_len > 0.75

    same_jurisdiction = bool(jurisdiction_in(pred) & jurisdiction_in(gold))

    return text_hit or same_jurisdiction


def is_section_header(line):
    """Heuristically detect common contract section headers."""
    stripped = line.strip()
    if not stripped:
        return False

    for pattern in SECTION_HEADER_PATTERNS:
        if pattern.match(stripped):
            return True

    return False


def build_section_spans(context):
    """Return (start, end, header_text) spans for likely document sections."""
    lines = context.splitlines()
    if not lines:
        return [(0, len(context), "")]

    line_starts = []
    cursor = 0
    for line in lines:
        line_starts.append(cursor)
        cursor += len(line) + 1

    header_indices = [i for i, line in enumerate(lines) if is_section_header(line)]
    if not header_indices:
        return [(0, len(context), "")]

    spans = []
    for idx, header_idx in enumerate(header_indices):
        start = line_starts[header_idx]
        end = len(context)
        if idx + 1 < len(header_indices):
            end = line_starts[header_indices[idx + 1]]
        spans.append((start, end, lines[header_idx]))

    return spans


def _line_tier(line, header_text):
    """Rank a single line's signal strength: 2 = its section header names
    governing law outright, 1 = a strong phrase whose subject is the
    agreement itself ("this Agreement ... shall be governed by ..."), 0 =
    a weak/generic match (bare "jurisdiction"/"venue", or "laws of the
    State of X" describing something other than the agreement, e.g. a
    party's formation or a mediator's qualifications)."""
    if any(re.search(p, header_text, re.IGNORECASE) for p in HEADER_GOVERNING_LAW_PATTERNS):
        return 2
    if THIS_AGREEMENT_PATTERN.search(line) and any(
        re.search(p, line, re.IGNORECASE) for p in STRONG_GOVERNING_LAW_PATTERNS
    ):
        return 1
    return 0


def _build_keyword_window_snippets(context, window_words=100):
    """Window ~window_words words on either side of each governing-law-style
    match, for contracts with no real internal section structure (no line
    breaks between clauses, so build_section_spans can't split anything).
    Sending the single all-encompassing "section" in that case means sending
    the entire document; windowing keeps just the relevant neighborhoods
    instead. Falls back to the full contract if nothing matches at all.
    """
    word_spans = [(m.start(), m.end()) for m in re.finditer(r"\S+", context)]
    if not word_spans:
        return [context.strip()], False

    match_starts = sorted(
        m.start()
        for pattern in GOVERNING_LAW_PATTERNS
        for m in re.finditer(pattern, context, re.IGNORECASE)
    )
    if not match_starts:
        return [context.strip()], False

    word_starts = [s for s, _ in word_spans]
    windows = []
    for pos in match_starts:
        word_idx = max(0, bisect.bisect_right(word_starts, pos) - 1)
        lo = max(0, word_idx - window_words)
        hi = min(len(word_spans) - 1, word_idx + window_words)
        windows.append((word_spans[lo][0], word_spans[hi][1]))

    windows.sort()
    merged = [windows[0]]
    for start, end in windows[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    snippets = [context[start:end].strip() for start, end in merged]
    return snippets, True


def build_candidate_snippets(context, max_sections=3, window_words=100):
    """Return whole section text around likely governing-law phrases.

    Candidate sections are ranked by their best line (header match > "this
    Agreement ... governed by ..." > generic keyword) instead of just taking
    the first N hits in document order. Tier 1+ matches are never dropped by
    the section budget -- a contract normally has only one real Governing Law
    section, but generic phrases like "jurisdiction"/"venue"/"laws of the
    State of X" show up repeatedly elsewhere (indemnification, dispute
    resolution, entity-formation boilerplate) and were crowding out the real
    section before the budget was ever reached. The budget only caps how many
    low-signal (tier 0) sections get pulled in as a fallback when no strong
    match exists at all.

    Returns:
        (snippets, used_section_match)
    """
    if not context:
        return [""], False

    section_spans = build_section_spans(context)

    if len(section_spans) <= 1:
        # No real internal structure was found (0 or 1 header line in the
        # whole document, e.g. a contract with no line breaks between
        # clauses -- just inline numbered markers within one giant
        # paragraph). That single span covers the entire document, so
        # falling through to the header-based logic below would just send
        # everything. Window around matches instead.
        return _build_keyword_window_snippets(context, window_words)

    lines = context.splitlines()
    if not lines:
        return [context[:900].strip()], False

    line_starts = []
    cursor = 0
    for line in lines:
        line_starts.append(cursor)
        cursor += len(line) + 1

    section_best_tier = {}  # section_idx -> best tier seen, document order of first match
    section_order = []
    for i, line in enumerate(lines):
        if any(re.search(p, line, re.IGNORECASE) for p in GOVERNING_LAW_PATTERNS):
            for section_idx, (start, end, header_text) in enumerate(section_spans):
                if start <= line_starts[i] < end:
                    if re.search("|".join(NON_CLAUSE_HEADER_PATTERNS), header_text, re.IGNORECASE):
                        break  # table of contents / index entries are never real clause text
                    tier = _line_tier(line, header_text)
                    if section_idx not in section_best_tier:
                        section_order.append(section_idx)
                    section_best_tier[section_idx] = max(tier, section_best_tier.get(section_idx, -1))
                    break

    if not section_best_tier:
        # Fallback: return the full contract so the model has maximum context.
        return [context.strip()], False

    strong = [idx for idx in section_order if section_best_tier[idx] >= 1]
    weak = [idx for idx in section_order if section_best_tier[idx] == 0]

    # Strong matches are kept in full (there's normally only one). Weak
    # matches are only used as a fallback, capped, when nothing strong exists.
    chosen_indices = strong if strong else weak[:max_sections]

    kept = {}
    for section_idx in chosen_indices:
        start, end, _header = section_spans[section_idx]
        snippet = context[start:end].strip()
        if snippet and snippet not in kept.values():
            kept[section_idx] = snippet

    snippets = [kept[idx] for idx in sorted(kept)]
    return (snippets or [context.strip()]), True


def _find_governing_law_qa(contract):
    """Return (context, gold_or_None) for the first Governing Law question
    found in this contract, or None if the contract has no such question at
    all. gold_or_None is the answer text if CUAD labels one, or None if the
    question exists but the answers list is empty (clause genuinely absent).
    """
    for para in contract["paragraphs"]:
        for qa in para["qas"]:
            if GOVERNING_LAW in qa["question"]:
                gold = qa["answers"][0]["text"] if qa["answers"] else None
                return para["context"], gold
    return None


def load_governing_law_examples(json_path, n=None, indices=None, require_present=True):
    """Return (position, title, context, gold_text) tuples.

    By default (require_present=True) only contracts that HAVE a Governing
    Law clause are returned -- gold_text is the labeled clause. With
    require_present=False, returns contracts where the clause is genuinely
    ABSENT (CUAD's answers list is empty) -- gold_text is "" for every
    example. That set exists to measure hallucination rate: does the model
    invent a clause when none is actually present?

    `position` is the 1-based index into the matching ordered list (present
    or absent, whichever was requested) -- the same numbering shown in a
    run's "(contract #i)" output, so you can re-run specific contracts later
    with --indices.

    If `indices` is given, return exactly those positions (skipping any out
    of range, with a warning), in the order requested. Otherwise return the
    first `n`.
    """
    with open(json_path) as f:
        cuad = json.load(f)

    examples = []
    for contract in cuad["data"]:
        found = _find_governing_law_qa(contract)
        if found is None:
            continue
        context, gold = found
        if (gold is not None) != require_present:
            continue
        examples.append((contract["title"], context, gold or ""))
        # Without --indices we can stop early once we have n; with --indices
        # we don't know which positions are needed until the full list exists.
        if indices is None and n is not None and len(examples) >= n:
            break

    if indices is not None:
        selected = []
        for pos in indices:
            if 1 <= pos <= len(examples):
                title, context, gold = examples[pos - 1]
                selected.append((pos, title, context, gold))
            else:
                clause_state = "have a Governing Law clause" if require_present else "are missing a Governing Law clause"
                print(f"WARNING: --indices {pos} is out of range "
                      f"(only {len(examples)} contracts {clause_state}) -- skipping.")
        return selected

    limited = examples[:n] if n is not None else examples
    return [(pos, title, context, gold) for pos, (title, context, gold) in enumerate(limited, 1)]


def extract_governing_law(client, context):
    """Ask Claude to extract the governing-law clause text from the contract."""
    snippets, used_section_match = build_candidate_snippets(context)
    snippet_block = "\n\n---\n\n".join(
        f"<excerpt {i+1}>\n{snippet}\n</excerpt {i+1}>"
        for i, snippet in enumerate(snippets)
    )

    prompt = f"""You are reviewing a commercial contract. Find the GOVERNING LAW clause:
    the sentence that states which state's or country's law governs the agreement.

    The input may be either a single section excerpt or the full contract. Use whatever
    context is provided, and do not assume that missing sections are available elsewhere.

    Return ONLY the exact clause text, copied verbatim character-for-character from the
    contract. Do NOT paraphrase, summarize, or rephrase it in your own words, even if you
    are confident about the meaning -- copy the original sentence exactly as written.

    If no governing law clause is present, respond with exactly the single word NONE and
    nothing else: no explanation of what the excerpt does or doesn't contain, no apology,
    no punctuation. Just the word NONE on its own.

    Relevant excerpts from the contract:
    {snippet_block}"""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    usage = getattr(resp, "usage", None)
    usage_summary = {
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
    }
    if not resp.content:
        # Claude occasionally ends the turn with zero content blocks (seen on
        # contracts with no real governing-law signal at all) -- treat that
        # the same as an explicit empty response rather than crashing.
        print(f"        (empty response, stop_reason={resp.stop_reason!r})")
        return "", usage_summary, used_section_match
    text = resp.content[0].text.strip()
    if text.upper() == "NONE":
        # Normalize the not-found sentinel to empty so clause_overlap scores it
        # the same way as a genuinely empty response.
        text = ""
    return text, usage_summary, used_section_match


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", help="Path to CUADv1.json")
    selection = ap.add_mutually_exclusive_group()
    selection.add_argument("--n", type=int, default=20, help="How many contracts to test (first N with a Governing Law clause)")
    selection.add_argument("--indices", type=int, nargs="+",
                            help="Test only these 1-based contract positions, e.g. --indices 22 23 39 "
                                 "(matches the \"(contract #i)\" numbering printed by a previous run)")
    ap.add_argument("--absent", action="store_true",
                     help="Test contracts with NO Governing Law clause instead, to measure hallucination rate")
    ap.add_argument("--show-usage", action="store_true", help="Print token usage per request")
    ap.add_argument("--input-price-per-1m", type=float, default=0.0, help="Optional input token price per 1M tokens")
    ap.add_argument("--output-price-per-1m", type=float, default=0.0, help="Optional output token price per 1M tokens")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: set ANTHROPIC_API_KEY first:  export ANTHROPIC_API_KEY=...")
        sys.exit(1)

    require_present = not args.absent
    client = Anthropic()
    if args.indices:
        examples = load_governing_law_examples(args.json_path, indices=args.indices, require_present=require_present)
        print(f"Testing {len(examples)} specific contract(s): {args.indices}\n")
    elif args.absent:
        examples = load_governing_law_examples(args.json_path, n=args.n, require_present=False)
        print(f"Testing {len(examples)} contracts with NO Governing Law clause (hallucination-rate check).\n")
    else:
        examples = load_governing_law_examples(args.json_path, n=args.n, require_present=True)
        print(f"Testing {len(examples)} contracts that have a Governing Law clause.\n")

    correct = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_context_chars = 0
    total_snippet_chars = 0
    section_match_count = 0
    fallback_count = 0
    section_match_input_tokens = 0
    fallback_input_tokens = 0
    for run_i, (pos, title, context, gold) in enumerate(examples, 1):
        snippets, used_section_match = build_candidate_snippets(context)
        snippet_text = "\n\n---\n\n".join(snippets)
        total_context_chars += len(context)
        total_snippet_chars += len(snippet_text)

        pred, usage, used_section_match = extract_governing_law(client, context)
        total_input_tokens += usage["input_tokens"]
        total_output_tokens += usage["output_tokens"]
        if used_section_match:
            section_match_count += 1
            section_match_input_tokens += usage["input_tokens"]
        else:
            fallback_count += 1
            fallback_input_tokens += usage["input_tokens"]
        
        # Score: token overlap >= 50% of smaller set
        hit = clause_overlap(pred, gold)
        correct += hit

        short_title = (title[:45] + "...") if len(title) > 45 else title
        status = "OK " if hit else "MISS"
        section_status = "section-match" if used_section_match else "full-contract fallback"
        print(f"[{run_i:2}/{len(examples)}] (contract #{pos}) {status} {short_title}")
        if hit:
            print(f"        gold  : {gold[:80]!r}")
            print(f"        pred  : {pred[:80]!r}")
        else:
            # Show the full text (not truncated) on a miss so failure analysis isn't blind.
            print(f"        gold  : {gold!r}")
            print(f"        pred  : {pred!r}")
            matched_patterns = [p for p in GOVERNING_LAW_PATTERNS if re.search(p, pred, re.IGNORECASE)]
            print(f"        pred matched patterns: {matched_patterns or 'NONE'}")
        print(f"        src   : {section_status}")
        print(f"        ctx   : {len(context)} chars -> {len(snippet_text)} chars sent")
        if args.show_usage:
            print(f"        usage : in={usage['input_tokens']} out={usage['output_tokens']} total={usage['input_tokens'] + usage['output_tokens']}")

    acc = correct / len(examples) if examples else 0
    estimated_cost = (
        (total_input_tokens / 1_000_000) * args.input_price_per_1m
        + (total_output_tokens / 1_000_000) * args.output_price_per_1m
    )
    avg_input_tokens = total_input_tokens / len(examples) if examples else 0
    avg_section_match_input_tokens = (
        section_match_input_tokens / section_match_count if section_match_count else 0
    )
    avg_fallback_input_tokens = fallback_input_tokens / fallback_count if fallback_count else 0
    print("\n" + "=" * 50)
    if args.absent:
        hallucinations = len(examples) - correct
        hall_rate = hallucinations / len(examples) if examples else 0
        print(f"HALLUCINATION RATE: {hallucinations}/{len(examples)} = {hall_rate:.0%}")
        print(f"CORRECTLY ABSTAINED: {correct}/{len(examples)} = {acc:.0%}")
    else:
        print(f"ACCURACY: {correct}/{len(examples)} = {acc:.0%}")
    print(f"SECTION MATCHES: {section_match_count}/{len(examples)}")
    print(f"FALLBACKS: {fallback_count}/{len(examples)}")
    print(f"TOKENS: input={total_input_tokens} output={total_output_tokens} total={total_input_tokens + total_output_tokens}")
    print(f"AVG INPUT TOKENS / CONTRACT: {avg_input_tokens:.1f}")
    print(f"AVG INPUT TOKENS / SECTION MATCH: {avg_section_match_input_tokens:.1f}")
    print(f"AVG INPUT TOKENS / FALLBACK: {avg_fallback_input_tokens:.1f}")
    print(f"CONTEXT CHARS: full={total_context_chars} snippets={total_snippet_chars}")
    if args.input_price_per_1m > 0 or args.output_price_per_1m > 0:
        print(f"ESTIMATED COST: ${estimated_cost:.4f}")
    print("=" * 50)


if __name__ == "__main__":
    main()