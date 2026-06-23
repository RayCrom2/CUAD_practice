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

GOVERNING_LAW_PATTERNS = [
    r"governed by",
    r"governing law",
    r"laws of the state",
    r"shall be governed",
    r"shall be construed",
    r"law of the state",
    r"jurisdiction",
    r"venue",
]

SECTION_HEADER_PATTERNS = [
    re.compile(r"^\s*Exhibit\s+\d+(?:\.\d+)*\b.*$", re.IGNORECASE),
    re.compile(r"^\s*\d+(?:\.\d+)*\.?\s+[A-Z0-9][A-Z0-9\s,&()'\-/]{2,}$"),
    re.compile(r"^\s*[A-Z0-9][A-Z0-9\s,&()'\-/]{8,}$"),
]


def clause_overlap(pred, gold):
    """Score prediction vs gold by token overlap (lenient baseline)."""
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
    
    # Hit if at least 50% of the smaller set overlaps
    return overlap / min_len > 0.5


def jurisdiction_in(text):
    """Return the set of known jurisdictions mentioned in a piece of text."""
    if not text:
        return set()
    found = set()
    for j in JURISDICTIONS:
        # word-boundary, case-insensitive
        if re.search(r"\b" + re.escape(j) + r"\b", text, flags=re.IGNORECASE):
            found.add(j)
    return found


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
    """Return spans for likely document sections based on text headers."""
    lines = context.splitlines()
    if not lines:
        return [(0, len(context))]

    line_starts = []
    cursor = 0
    for line in lines:
        line_starts.append(cursor)
        cursor += len(line) + 1

    header_indices = [i for i, line in enumerate(lines) if is_section_header(line)]
    if not header_indices:
        return [(0, len(context))]

    spans = []
    for idx, header_idx in enumerate(header_indices):
        start = line_starts[header_idx]
        end = len(context)
        if idx + 1 < len(header_indices):
            end = line_starts[header_indices[idx + 1]]
        spans.append((start, end))

    return spans


def build_candidate_snippets(context, max_sections=3):
    """Return whole section text around likely governing-law phrases.

    Returns:
        (snippets, used_section_match)
    """
    if not context:
        return [""], False

    section_spans = build_section_spans(context)
    lines = context.splitlines()
    if not lines:
        return [context[:900].strip()], False

    line_starts = []
    cursor = 0
    for line in lines:
        line_starts.append(cursor)
        cursor += len(line) + 1

    candidate_section_indices = []
    lower_lines = [line.lower() for line in lines]
    for i, line in enumerate(lower_lines):
        if any(pattern in line for pattern in GOVERNING_LAW_PATTERNS):
            for section_idx, (start, end) in enumerate(section_spans):
                if start <= line_starts[i] < end:
                    candidate_section_indices.append(section_idx)
                    break

    if not candidate_section_indices:
        # Fallback: return the full contract so the model has maximum context.
        return [context.strip()], False

    snippets = []
    seen = set()
    for section_idx in candidate_section_indices:
        start, end = section_spans[section_idx]
        snippet = context[start:end].strip()
        if snippet and snippet not in seen:
            snippets.append(snippet)
            seen.add(snippet)
        if len(snippets) >= max_sections:
            break

    return (snippets or [context.strip()]), True


def load_governing_law_examples(json_path, n):
    """Return up to n (title, context, gold_text) tuples that HAVE a GL clause."""
    with open(json_path) as f:
        cuad = json.load(f)

    examples = []
    for contract in cuad["data"]:
        for para in contract["paragraphs"]:
            for qa in para["qas"]:
                if GOVERNING_LAW in qa["question"] and qa["answers"]:
                    gold = qa["answers"][0]["text"]
                    examples.append((contract["title"], para["context"], gold))
                    break  # one GL question per contract
        if len(examples) >= n:
            break
    return examples[:n]


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

    Return ONLY the exact clause text from the contract, nothing else. No JSON, no explanation, just the clause.
    If no governing law clause is found, return an empty response.

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
    return resp.content[0].text.strip(), usage_summary, used_section_match


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", help="Path to CUADv1.json")
    ap.add_argument("--n", type=int, default=20, help="How many contracts to test")
    ap.add_argument("--show-usage", action="store_true", help="Print token usage per request")
    ap.add_argument("--input-price-per-1m", type=float, default=0.0, help="Optional input token price per 1M tokens")
    ap.add_argument("--output-price-per-1m", type=float, default=0.0, help="Optional output token price per 1M tokens")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: set ANTHROPIC_API_KEY first:  export ANTHROPIC_API_KEY=...")
        sys.exit(1)

    client = Anthropic()
    examples = load_governing_law_examples(args.json_path, args.n)
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
    for i, (title, context, gold) in enumerate(examples, 1):
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
        print(f"[{i:2}/{len(examples)}] {status} {short_title}")
        print(f"        gold  : {gold[:80]!r}")
        print(f"        pred  : {pred[:80]!r}")
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