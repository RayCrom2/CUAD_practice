"""
Phase 0: Understand CUAD by reading its raw JSON (SQuAD format).
This bypasses the flaky `datasets` loader entirely.

CUAD_v1.json structure (SQuAD-style):
{
  "data": [
    {
      "title": "<contract filename>",
      "paragraphs": [
        {
          "context": "<full contract text>",
          "qas": [
            {
              "id": "...",
              "question": "Highlight the parts ... related to 'Governing Law' ...",
              "answers": [{"text": "...", "answer_start": 1234}, ...],
              "is_impossible": false   # true means the clause is absent
            },
            ...
          ]
        }
      ]
    },
    ...
  ]
}

Usage:
    1. Find your CUAD_v1.json (see find step below), then:
    python3 inspect_cuad.py /path/to/CUAD_v1.json
"""
import sys, json, glob, os

# ---------------------------------------------------------------------------
# 0. LOCATE CUAD_v1.json
# ---------------------------------------------------------------------------
if len(sys.argv) > 1:
    json_path = sys.argv[1]
else:
    # try to auto-find it in the HF cache or current dir
    candidates = []
    candidates += glob.glob(os.path.expanduser("~/.cache/huggingface/**/CUAD_v1.json"), recursive=True)
    candidates += glob.glob("**/CUAD_v1.json", recursive=True)
    if not candidates:
        print("Could not auto-find CUAD_v1.json.")
        print("Run:  find ~ -name 'CUAD_v1.json' 2>/dev/null")
        print("Then: python3 inspect_cuad.py /the/path/CUAD_v1.json")
        sys.exit(1)
    json_path = candidates[0]
    print(f"Auto-found: {json_path}\n")

with open(json_path) as f:
    cuad = json.load(f)

data = cuad["data"]

# ---------------------------------------------------------------------------
# 1. OVERALL SHAPE
# ---------------------------------------------------------------------------
print("=" * 70)
print("OVERALL STRUCTURE")
print("=" * 70)
print("Number of contracts:", len(data))
total_qas = sum(len(p["qas"]) for c in data for p in c["paragraphs"])
print("Total question-answer pairs:", total_qas)
print("Clause questions per contract:", total_qas // len(data))
print()

# ---------------------------------------------------------------------------
# 2. ONE CONTRACT
# ---------------------------------------------------------------------------
c0 = data[0]
p0 = c0["paragraphs"][0]
print("=" * 70)
print("FIRST CONTRACT")
print("=" * 70)
print("Title (filename):", c0["title"])
print("Context length (chars):", len(p0["context"]))
print("Context preview:", p0["context"][:300], "...")
print("Number of questions for this contract:", len(p0["qas"]))
print()

# ---------------------------------------------------------------------------
# 3. CLAUSE TYPES (the 41 categories)
# ---------------------------------------------------------------------------
print("=" * 70)
print("THE 41 CLAUSE QUESTIONS")
print("=" * 70)
for qa in p0["qas"]:
    print("-", qa["question"][:110])
print()

# ---------------------------------------------------------------------------
# 4. A GOVERNING LAW EXAMPLE WITH AN ANSWER
# ---------------------------------------------------------------------------
print("=" * 70)
print("FIRST 'Governing Law' QA THAT HAS AN ANSWER")
print("=" * 70)
found = False
for c in data:
    for p in c["paragraphs"]:
        for qa in p["qas"]:
            if "Governing Law" in qa["question"] and qa["answers"]:
                ans = qa["answers"][0]
                print("Contract:", c["title"])
                print("Question:", qa["question"][:140])
                print()
                print("LABELED ANSWER:", repr(ans["text"][:300]))
                print("answer_start offset:", ans["answer_start"])
                # verify the offset
                start = ans["answer_start"]
                sliced = p["context"][start:start + len(ans["text"])]
                print()
                print("VERIFY context[start:start+len]:", repr(sliced[:300]))
                print("Offset matches answer text:", sliced == ans["text"])
                found = True
                break
        if found: break
    if found: break

# ---------------------------------------------------------------------------
# 5. HOW MANY CONTRACTS ACTUALLY HAVE A GOVERNING LAW CLAUSE?
#    (is_impossible / empty answers = clause absent -> hallucination-rate material)
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("GOVERNING LAW COVERAGE ACROSS ALL CONTRACTS")
print("=" * 70)
present = absent = 0
for c in data:
    for p in c["paragraphs"]:
        for qa in p["qas"]:
            if "Governing Law" in qa["question"]:
                if qa["answers"]:
                    present += 1
                else:
                    absent += 1
print(f"Contracts WITH a labeled Governing Law clause: {present}")
print(f"Contracts WITHOUT one (empty answer):          {absent}")