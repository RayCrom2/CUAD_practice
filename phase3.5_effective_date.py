"""
Phase 3.5 thin slice: extract the Effective Date from CUAD contracts using
Claude, then score against the gold labels.

This is the second clause type after Governing Law (Phase 1-2). Reuses the
same section-ranking / keyword-windowing snippet-selection infrastructure
and the same forced-tool-use extraction pattern from phase2.2 -- only the
clause-specific patterns, prompt, and tool are new. Deliberately starts
simple (plain token-overlap scoring, no jurisdiction-style fallback yet) so
any fixes added later are justified by real observed failures, not assumed
up front just because Governing Law needed them.

Setup:
    pip3 install anthropic --user
    export ANTHROPIC_API_KEY="sk-ant-..."

Run:
    python3 phase3.5_effective_date.py "/path/to/CUADv1.json" --n 30
    python3 phase3.5_effective_date.py "/path/to/CUADv1.json" --absent --n 20
"""

import sys
import os
import json
import re
import bisect
import string
import argparse

from anthropic import Anthropic

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())  # reads .env in cwd
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

MODEL = "claude-sonnet-4-5"   # fast + capable; fine for extraction
EFFECTIVE_DATE = "Effective Date"

# Strong phrases are a near-certain signal of an actual effective-date
# sentence (the agreement itself becoming effective/commencing), not some
# other date mentioned for an unrelated purpose elsewhere in the contract.
STRONG_EFFECTIVE_DATE_PATTERNS = [
    r"effective date",
    r"effective as of",
    r"become effective",
    r"shall commence",
    r"commence on",
    r"commencing",           # catches "commencing on", "commencing the 1st day of", etc.
    r"entered into as of",
    r"made and entered into",
    r"dated as of",
]
# A bare date string with no surrounding clause language at all is a real,
# observed gold-answer style in CUAD (e.g. "1 August 2011" on its own) --
# this weak pattern exists specifically to catch that case as a fallback
# signal when nothing stronger is found.
WEAK_EFFECTIVE_DATE_PATTERNS = [
    r"\b(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},?\s+\d{4}\b",
    r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4}\b",
    # Abbreviated month names, with or without trailing period (e.g. "19 Jan. 1998", "5 Sep 2003")
    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{4}\b",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
]
EFFECTIVE_DATE_PATTERNS = STRONG_EFFECTIVE_DATE_PATTERNS + WEAK_EFFECTIVE_DATE_PATTERNS

# If a SECTION HEADER itself contains this, that section is almost certainly
# the effective-date clause regardless of what else matched first.
HEADER_EFFECTIVE_DATE_PATTERNS = [
    r"effective date",
]

# Sections whose header marks them as navigation/listing rather than actual
# clause text -- e.g. a Table of Contents that lists "Effective Date" as a
# heading title is not the clause itself and should never be a candidate.
NON_CLAUSE_HEADER_PATTERNS = [
    r"table of contents",
    r"^\s*index\s*$",
]

# A real effective-date sentence is about the agreement itself ("This
# Agreement ... is effective as of ..."), not some other obligation's start
# date ("Deliveries shall commence on ..."). Requiring "this <word>
# agreement" nearby on the same line filters those false positives out --
# same principle used for Governing Law's formation-language false positives.
#
# Two alternatives compiled SEPARATELY to avoid catastrophic backtracking:
# combining them with | in one re.compile() causes alternative #1's {0,4}
# repetition to exhaust the backtracking budget before alternative #2 is
# tried on some inputs, silently failing to match even when alt2 would
# match in isolation.
#   1. “this <0-4 filler words> agreement” -- allows optional quotes and
#      hyphens (e.g. 'this “Agreement”', “this License and Hosting Agreement”)
#   2. “(the “Agreement”)” -- the title/caption defined-term convention used
#      when the document never says “this Agreement” (e.g. “MASTER SUPPLY
#      AGREEMENT (the “Agreement”) dated November 1, 2019”)
_THIS_AGREEMENT_1 = re.compile(
    r'\bthis\s+(?:[\x22\']?[a-z][a-z\-]*[\x22\']?\s+){0,4}[\x22\']?agreement[\x22\']?\b',
    re.IGNORECASE,
)
# Parenthetical defined-term form: (the “Agreement”).
# Uses \x22 (hex for ASCII double-quote 0x22) instead of a literal “ so that
# editors cannot silently convert the straight quote to a Unicode curly-quote,
# which would cause the pattern to stop matching contracts that use plain ASCII.
_THIS_AGREEMENT_2 = re.compile(
    r'\(\s*\x22?the\x22?\s+\x22?agreement\x22?\s*\)',
    re.IGNORECASE,
)


def _matches_agreement(text):
    return bool(_THIS_AGREEMENT_1.search(text) or _THIS_AGREEMENT_2.search(text))

SECTION_HEADER_PATTERNS = [
    re.compile(r"^\s*Exhibit\s+\d+(?:\.\d+)*\b.*$", re.IGNORECASE),
    re.compile(r"^\s*\d+(?:\.\d+)*\.?\s+[A-Z0-9][A-Z0-9\s,&()'\-/]{2,}$"),
    re.compile(r"^\s*[A-Z0-9][A-Z0-9\s,&()'\-/]{8,}$"),
]

# A tier-2 section whose header names the clause (e.g. "EFFECTIVE DATE") but
# whose body is smaller than this threshold is almost certainly a table-of-
# contents line, not an actual clause section. Downgrade to tier-0 so it
# only surfaces as a last-resort fallback rather than crowding out real content.
_MIN_TIER2_SECTION_CHARS = 400

# TOC entries often end with a bare page number: "3. EFFECTIVE DATE     5"
_TOC_PAGE_RE = re.compile(r'\s+\d{1,3}\s*$')


def _tokenize(text):
    """Lowercase, split on whitespace, and strip surrounding punctuation off
    each token (e.g. "2007;" -> "2007", '"agreement"' -> "agreement").

    Punctuation is only stripped from token edges, not the middle, so dates
    that genuinely differ -- "2007" vs "2008" -- still don't match. This is
    deliberately narrower than a character-level similarity metric: that
    would also call "August 10, 2007" and "August 11, 2007" a near-total
    match (one character apart) despite being a different calendar date
    entirely, which is exactly the kind of error this scorer needs to catch.
    """
    tokens = {w.strip(string.punctuation) for w in text.lower().split()}
    tokens.discard("")
    return tokens


def clause_overlap(pred, gold):
    """Score prediction vs gold by plain token overlap.

    Deliberately simpler than Governing Law's scorer for now -- no
    date-normalization fallback (e.g. treating "1/1/2020" and "January 1,
    2020" as equivalent) until a real run shows that's actually needed.
    """
    if not pred and not gold:
        return True  # both empty is correct
    if not pred or not gold:
        return False  # one empty, one not

    pred_words = _tokenize(pred)
    gold_words = _tokenize(gold)

    if not pred_words or not gold_words:
        return False

    overlap = len(pred_words & gold_words)
    min_len = min(len(pred_words), len(gold_words))
    return overlap / min_len > 0.75


def is_section_header(line):
    """Heuristically detect common contract section headers."""
    stripped = line.strip()
    if not stripped:
        return False

    for pattern in SECTION_HEADER_PATTERNS:
        if pattern.match(stripped):
            return True

    return False


def _scan_sections_and_keywords(context):
    """Build section spans AND find effective-date keyword matches in one pass.

    Previously two separate passes: build_section_spans() walked all lines to
    find headers, then build_candidate_snippets() walked all lines again to
    find keyword matches and compute tiers. This does both simultaneously by
    tracking the current open section as we go.

    Returns:
        section_spans    : list of (start, end, header_text)
        section_best_tier: dict of section_idx -> best tier seen for any line in it
        section_order    : list of section indices in order of first keyword match
        has_sections     : False when no header lines were found -- caller should
                           use the keyword-windowing path instead
    """
    lines = context.splitlines()
    if not lines:
        return [], {}, [], False

    line_starts = []
    cursor = 0
    for line in lines:
        line_starts.append(cursor)
        cursor += len(line) + 1

    section_spans = []
    section_best_tier = {}
    section_order = []
    has_sections = False

    current_start = 0
    current_header = ""

    for i, line in enumerate(lines):
        line_start = line_starts[i]

        if is_section_header(line):
            # Close the current open section if it has content, then open a new one.
            # Pre-header preamble (current_header="") is preserved as section 0
            # when the first header doesn't start at offset 0 -- this fixes the
            # preamble-orphaning bug where the opening paragraph was silently dropped.
            if line_start > current_start:
                section_spans.append((current_start, line_start, current_header))
            current_start = line_start
            current_header = line
            has_sections = True

        # Check for effective-date keyword match on this line.
        if any(re.search(p, line, re.IGNORECASE) for p in EFFECTIVE_DATE_PATTERNS):
            if re.search("|".join(NON_CLAUSE_HEADER_PATTERNS), current_header, re.IGNORECASE):
                continue  # table of contents / index entries are never real clause text
            # The current section is still open, so its future index is len(section_spans).
            sidx = len(section_spans)
            tier = _line_tier(line, current_header)
            if sidx not in section_best_tier:
                section_order.append(sidx)
            section_best_tier[sidx] = max(tier, section_best_tier.get(sidx, -1))

    # Close the last open section.
    section_spans.append((current_start, len(context), current_header))

    return section_spans, section_best_tier, section_order, has_sections


def _line_tier(line, header_text):
    """Rank a single line's signal strength: 2 = its section header names
    the effective date outright, 1 = a strong phrase whose subject is the
    agreement itself ("this Agreement ... is effective as of ..."), 0 = a
    weak/generic match (a bare date string, or commencement language about
    something other than the agreement, e.g. a specific deliverable)."""
    if any(re.search(p, header_text, re.IGNORECASE) for p in HEADER_EFFECTIVE_DATE_PATTERNS):
        return 2
    # "effective date" as a phrase is specific enough that its presence on a
    # line reliably signals the clause itself -- e.g. the preamble caption
    # "TITLE AGREEMENT dated as of [date] (the Effective Date)" or a
    # definitions line '"EFFECTIVE DATE" - January 21, 2002'. Unlike "dated
    # as of" or "shall commence", which show up for unrelated obligations,
    # "effective date" almost exclusively labels the agreement's own start.
    # Skip the _matches_agreement co-occurrence requirement when it's present.
    if re.search(r'\beffective\s+date\b', line, re.IGNORECASE) and any(
        re.search(p, line, re.IGNORECASE) for p in STRONG_EFFECTIVE_DATE_PATTERNS
    ):
        return 1
    if _matches_agreement(line) and any(
        re.search(p, line, re.IGNORECASE) for p in STRONG_EFFECTIVE_DATE_PATTERNS
    ):
        return 1
    return 0


def _build_keyword_window_snippets(context, window_words=100):
    """Window ~window_words words on either side of each effective-date-style
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
        for pattern in EFFECTIVE_DATE_PATTERNS
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


def _rank_candidate_sections(section_spans, section_best_tier, section_order,
                             max_sections):
    """Apply the TOC downgrade and produce the final selection order.

    Shared by build_candidate_snippets and diagnose_section_candidates so the
    diagnostic view can never drift from what actually gets selected.

    Downgrade tier-2 sections that are table-of-contents entries. A tier-2
    section has a header that literally names the clause ("Effective Date"),
    but TOC lines share that same header text while containing no actual
    clause body. Two signals: body smaller than _MIN_TIER2_SECTION_CHARS,
    or a trailing page number in the header ("3. EFFECTIVE DATE     5").
    Downgraded indices sort last in the weak pool -- an organic tier-0
    section (never had a strong header signal) is a better candidate than
    one that was tier-2 but turned out to be a TOC entry.

    Mutates section_best_tier in place (downgraded entries become 0).

    Returns:
        strong    : tier 1+ indices in first-match order
        weak      : tier-0 indices, organic first, downgraded last
        downgraded: set of indices demoted by the TOC downgrade
        chosen    : the indices that will actually be sent to the model
    """
    downgraded = set()
    for idx in list(section_best_tier.keys()):
        if section_best_tier[idx] >= 2:
            start, end, header = section_spans[idx]
            if (end - start) < _MIN_TIER2_SECTION_CHARS or _TOC_PAGE_RE.search(header):
                section_best_tier[idx] = 0
                downgraded.add(idx)

    strong = [idx for idx in section_order if section_best_tier[idx] >= 1]
    weak   = [idx for idx in section_order if section_best_tier[idx] == 0]
    # Organic tier-0 sections precede downgraded ones; document order preserved
    # within each group so the most relevant keyword neighbourhood comes first.
    weak = [idx for idx in weak if idx not in downgraded] + \
           [idx for idx in weak if idx in downgraded]
    chosen = strong if strong else weak[:max_sections]
    return strong, weak, downgraded, chosen


def build_candidate_snippets(context, max_sections=3, window_words=100):
    """Return whole section text around likely effective-date phrases.

    Candidate sections are ranked by their best line (header match > "this
    Agreement ... effective as of ..." > generic keyword) instead of just
    taking the first N hits in document order. Tier 1+ matches are never
    dropped by the section budget. The budget only caps how many low-signal
    (tier 0) sections get pulled in as a fallback when no strong match
    exists at all.

    Returns:
        (snippets, used_section_match)
    """
    if not context:
        return [""], False

    section_spans, section_best_tier, section_order, has_sections = (
        _scan_sections_and_keywords(context)
    )

    if not has_sections:
        return _build_keyword_window_snippets(context, window_words)

    if not section_best_tier:
        return [context.strip()], False

    _strong, _weak, _downgraded, chosen_indices = _rank_candidate_sections(
        section_spans, section_best_tier, section_order, max_sections
    )

    kept = {}
    for section_idx in chosen_indices:
        start, end, _header = section_spans[section_idx]
        snippet = context[start:end].strip()
        if snippet and snippet not in kept.values():
            kept[section_idx] = snippet

    snippets = [kept[idx] for idx in sorted(kept)]
    return (snippets or [context.strip()]), True


def _find_effective_date_qa(contract):
    """Return (context, gold_or_None) for the first Effective Date question
    found in this contract, or None if the contract has no such question at
    all. gold_or_None is the answer text if CUAD labels one, or None if the
    question exists but the answers list is empty (clause genuinely absent).
    """
    for para in contract["paragraphs"]:
        for qa in para["qas"]:
            if EFFECTIVE_DATE in qa["question"]:
                gold = qa["answers"][0]["text"] if qa["answers"] else None
                return para["context"], gold
    return None


def load_effective_date_examples(json_path, n=None, indices=None, require_present=True):
    """Return (position, title, context, gold_text) tuples.

    By default (require_present=True) only contracts that HAVE an Effective
    Date clause are returned -- gold_text is the labeled clause. With
    require_present=False, returns contracts where the clause is genuinely
    ABSENT -- gold_text is "" for every example.

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
        found = _find_effective_date_qa(contract)
        if found is None:
            continue
        context, gold = found
        if (gold is not None) != require_present:
            continue
        examples.append((contract["title"], context, gold or ""))
        if indices is None and n is not None and len(examples) >= n:
            break

    if indices is not None:
        selected = []
        for pos in indices:
            if 1 <= pos <= len(examples):
                title, context, gold = examples[pos - 1]
                selected.append((pos, title, context, gold))
            else:
                clause_state = "have an Effective Date clause" if require_present else "are missing an Effective Date clause"
                print(f"WARNING: --indices {pos} is out of range "
                      f"(only {len(examples)} contracts {clause_state}) -- skipping.")
        return selected

    limited = examples[:n] if n is not None else examples
    return [(pos, title, context, gold) for pos, (title, context, gold) in enumerate(limited, 1)]


def diagnose_section_candidates(context, gold, max_sections=3):
    """Return a diagnostic view of ALL sections that matched any keyword.

    Tells you:
    - How each section was ranked (tier 2/1/0)
    - Whether it was SELECTED or DROPPED (by the max_sections cap)
    - Whether the gold text actually lives inside it

    Designed to answer: is the cap cutting off the right section, or is
    the right section simply not generating any keyword match at all?
    """
    section_spans, section_best_tier, section_order, has_sections = (
        _scan_sections_and_keywords(context)
    )

    # Windowing path -- no real section structure
    if not has_sections:
        windows, _ = _build_keyword_window_snippets(context)
        gold_key = gold.strip()[:40] if gold else ""
        results = [
            {"path": "windowing", "window_idx": i, "chars": len(w),
             "gold_present": bool(gold_key and gold_key in w), "preview": w[:80]}
            for i, w in enumerate(windows)
        ]
        return {"path": "windowing", "windows": results}

    if not section_best_tier:
        return {"path": "sections", "no_matches": True, "candidates": []}

    strong, weak, downgraded, chosen_indices = _rank_candidate_sections(
        section_spans, section_best_tier, section_order, max_sections
    )
    chosen = set(chosen_indices)

    gold_key = gold.strip()[:40] if gold else ""
    candidates = []
    for idx in section_order:
        start, end, header = section_spans[idx]
        snippet = context[start:end].strip()
        candidates.append({
            "section_idx": idx,
            "tier": section_best_tier[idx],
            "downgraded": idx in downgraded,
            "header": header[:60] or "(preamble)",
            "chars": len(snippet),
            "selected": idx in chosen,
            "gold_present": bool(gold_key and gold_key in snippet),
        })
    candidates.sort(key=lambda c: (-c["tier"], c["downgraded"], c["section_idx"]))

    return {"path": "sections", "no_matches": False, "candidates": candidates,
            "strong_count": len(strong), "weak_count": len(weak)}


EFFECTIVE_DATE_TOOL = {
    "name": "report_effective_date",
    "description": "Report whether an effective date was found in the contract text, and what it says.",
    "input_schema": {
        "type": "object",
        "properties": {
            "found": {
                "type": "boolean",
                "description": "True if the agreement's effective date is stated in the provided text, false otherwise.",
            },
            "clause_text": {
                "type": "string",
                "description": (
                    "The exact effective-date text, copied verbatim character-for-character "
                    "from the contract. Empty string if found is false."
                ),
            },
        },
        "required": ["found", "clause_text"],
    },
}


def extract_effective_date(client, context):
    """Ask Claude to extract the effective-date text from the contract.

    Uses forced tool use (same pattern as Governing Law's phase2.2): the
    model must call report_effective_date with a typed {found: bool,
    clause_text: str} payload, so there's no free-text wrapper for
    commentary to leak through.
    """
    snippets, used_section_match = build_candidate_snippets(context)
    snippet_block = "\n\n---\n\n".join(
        f"<excerpt {i+1}>\n{snippet}\n</excerpt {i+1}>"
        for i, snippet in enumerate(snippets)
    )

    prompt = f"""You are reviewing a commercial contract. Find the EFFECTIVE DATE: the date
    this Agreement itself becomes effective or its term begins (e.g. "This Agreement is
    effective as of January 1, 2020", "made and entered into as of the 1st day of March,
    2020", or a date stated in the opening paragraph as when the parties enter into the
    agreement). In most contracts there is only one such date, and it is both when the
    document was signed and when it takes effect -- in that common case, that one date is
    the correct answer.

    Some contracts explicitly separate two dates: an "Execution Date" (or "Agreement Date")
    -- when the document was physically signed -- from a distinctly-labeled "Effective
    Date" or Term-commencement date that can fall on a different day. If the contract draws
    that distinction, report the EFFECTIVE DATE / commencement date, NOT the execution or
    signing date.

    If you are convinved that the language used in a particular contract is 
    likely to be the effective date, but there is information that seems redacted, 
    return that if no other date is present. For example, if the contract says 
    "This Agreement is made and entered into as of [*****]", return the entire clause_text as the declaration of the effective date.

    Do NOT confuse this with other dates that may appear in the contract for unrelated
    purposes -- a termination/expiration date, a specific deliverable's due date, a renewal
    date, or the date of a later amendment. Only the date this Agreement itself becomes
    effective or commences.

    The input may be either a portion of or the full contract. Use whatever
    context is provided, and do not assume that missing sections are available elsewhere.

    Call the report_effective_date tool with your finding. If you find it, copy it verbatim
    character-for-character from the contract -- do not paraphrase, summarize, or reformat
    the date, even if you are confident about the meaning.

    Relevant excerpts from the contract:
    {snippet_block}"""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        tools=[EFFECTIVE_DATE_TOOL],
        tool_choice={"type": "tool", "name": "report_effective_date"},
        messages=[{"role": "user", "content": prompt}],
    )
    usage = getattr(resp, "usage", None)
    usage_summary = {
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
    }

    tool_call = next((block for block in resp.content if block.type == "tool_use"), None)
    if tool_call is None:
        print(f"        (no tool call, stop_reason={resp.stop_reason!r})")
        return "", usage_summary, used_section_match

    found = bool(tool_call.input.get("found", False))
    clause_text = (tool_call.input.get("clause_text") or "").strip()
    return (clause_text if found else ""), usage_summary, used_section_match


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", help="Path to CUADv1.json")
    selection = ap.add_mutually_exclusive_group()
    selection.add_argument("--n", type=int, default=20, help="How many contracts to test (first N with an Effective Date clause)")
    selection.add_argument("--indices", type=int, nargs="+",
                            help="Test only these 1-based contract positions, e.g. --indices 22 23 39 "
                                 "(matches the \"(contract #i)\" numbering printed by a previous run)")
    ap.add_argument("--absent", action="store_true",
                     help="Test contracts with NO Effective Date clause instead, to measure hallucination rate")
    ap.add_argument("--show-usage", action="store_true", help="Print token usage per request")
    ap.add_argument("--diagnose", action="store_true",
                     help="On miss or weak-only selection, print all candidate sections with their tier "
                          "and whether the gold text is present -- use to determine if the selection cap "
                          "is hiding the right clause or if the right clause has no keyword match at all")
    ap.add_argument("--input-price-per-1m", type=float, default=0.0, help="Optional input token price per 1M tokens")
    ap.add_argument("--output-price-per-1m", type=float, default=0.0, help="Optional output token price per 1M tokens")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: set ANTHROPIC_API_KEY first:  export ANTHROPIC_API_KEY=...")
        sys.exit(1)

    require_present = not args.absent
    client = Anthropic()
    if args.indices:
        examples = load_effective_date_examples(args.json_path, indices=args.indices, require_present=require_present)
        print(f"Testing {len(examples)} specific contract(s): {args.indices}\n")
    elif args.absent:
        examples = load_effective_date_examples(args.json_path, n=args.n, require_present=False)
        print(f"Testing {len(examples)} contracts with NO Effective Date clause (hallucination-rate check).\n")
    else:
        examples = load_effective_date_examples(args.json_path, n=args.n, require_present=True)
        print(f"Testing {len(examples)} contracts that have an Effective Date clause.\n")

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

        pred, usage, used_section_match = extract_effective_date(client, context)
        total_input_tokens += usage["input_tokens"]
        total_output_tokens += usage["output_tokens"]
        if used_section_match:
            section_match_count += 1
            section_match_input_tokens += usage["input_tokens"]
        else:
            fallback_count += 1
            fallback_input_tokens += usage["input_tokens"]

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
            matched_patterns = [p for p in EFFECTIVE_DATE_PATTERNS if re.search(p, pred, re.IGNORECASE)]
            print(f"        pred matched patterns: {matched_patterns or 'NONE'}")
        print(f"        src   : {section_status}")
        print(f"        ctx   : {len(context)} chars -> {len(snippet_text)} chars sent")

        if args.diagnose and (not hit or not used_section_match):
            diag = diagnose_section_candidates(context, gold)
            if diag["path"] == "windowing":
                print(f"        DIAG [windowing]: {len(diag['windows'])} window(s)")
                for w in diag["windows"]:
                    tag = "GOLD HERE" if w["gold_present"] else "no gold"
                    print(f"          window {w['window_idx']}: {w['chars']} chars [{tag}] {w['preview']!r}")
            elif diag["no_matches"]:
                print(f"        DIAG [no keyword matches]: gold clause has no pattern match anywhere in this contract")
            else:
                cands = diag["candidates"]
                print(f"        DIAG [sections]: {diag['strong_count']} strong / {diag['weak_count']} weak candidate(s) found")
                for c in cands:
                    sel = "SELECTED" if c["selected"] else "dropped  "
                    gold_tag = " <-- GOLD HERE" if c["gold_present"] else ""
                    tier_label = {2: "tier2(header)", 1: "tier1(strong)", 0: "tier0(weak)"}[c["tier"]]
                    if c["downgraded"]:
                        tier_label = "tier0(toc-downgraded)"
                    print(f"          [{sel}] {tier_label} | {c['chars']:6} chars | {c['header']!r}{gold_tag}")

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
