"""
Load a contract from CUAD and print it in human-readable format
to understand section structure and clause positioning.
"""

import json
import sys

def inspect_contract(json_path, contract_position=1):
    """Load and print a contract with Governing Law clause.

    contract_position is 1-based, into the full ordered list of GL-bearing
    contracts -- matching the (contract #i) numbering printed by
    phase1.3_governing_law.py's --indices flag, so the same number refers
    to the same contract in both scripts.
    """
    with open(json_path) as f:
        cuad = json.load(f)

    # Find contracts with Governing Law clauses
    gl_contracts = []
    for i, contract in enumerate(cuad["data"]):
        for para in contract["paragraphs"]:
            for qa in para["qas"]:
                if "Governing Law" in qa["question"] and qa["answers"]:
                    gl_contracts.append((i, contract))
                    break

    if not gl_contracts:
        print("No contracts with Governing Law clauses found.")
        return

    if not (1 <= contract_position <= len(gl_contracts)):
        print(f"WARNING: contract_position {contract_position} is out of range "
              f"(only {len(gl_contracts)} contracts have a Governing Law clause); clamping.")
    position = min(max(contract_position, 1), len(gl_contracts))
    idx, contract = gl_contracts[position - 1]

    print("=" * 80)
    print(f"CONTRACT: {contract['title']}")
    print("=" * 80)
    print()

    # Print all paragraphs with markers
    for para_idx, para in enumerate(contract["paragraphs"]):
        context = para["context"]
        
        # Look for the Governing Law QA in this paragraph
        gl_qa = None
        for qa in para["qas"]:
            if "Governing Law" in qa["question"] and qa["answers"]:
                gl_qa = qa
                break

        if gl_qa:
            print(f"--- PARAGRAPH {para_idx} (contains Governing Law) ---")
            gold_text = gl_qa["answers"][0]["text"]
            gold_start = gl_qa["answers"][0]["answer_start"]
            gold_end = gold_start + len(gold_text)
            
            # Print context with markers around the answer
            print(context[:gold_start], end="")
            print(f"\n>>> [{gold_text}] <<<\n", end="")
            print(context[gold_end:])
        else:
            print(f"\n\n--- PARAGRAPH {para_idx} ---")
            print(context[:500])
            if len(context) > 500:
                print(f"... ({len(context) - 500} more chars)")

        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_contract_structure.py /path/to/CUADv1.json [contract_position]")
        print("  contract_position is 1-based (e.g. 22 for the 22nd Governing-Law contract,")
        print("  matching the (contract #i) numbering from phase1.3_governing_law.py --indices)")
        sys.exit(1)

    json_path = sys.argv[1]
    contract_position = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    inspect_contract(json_path, contract_position)
