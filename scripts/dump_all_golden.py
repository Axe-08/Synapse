import json

final_records = {}
with open('/home/akshit/Projects/Synapse/dataset.jsonl') as f:
    for line in f:
        if line.strip():
            rec = json.loads(line)
            final_records[rec['problem_id']] = rec

with open('/home/akshit/Projects/Synapse/Records/all_golden_records.md', 'w') as out:
    out.write('# Final V2 Assembled Golden Records\n\n')
    for pid, rec in final_records.items():
        out.write(f'## Problem: {pid}\n\n')
        out.write('```json\n')
        out.write(json.dumps(rec, indent=2))
        out.write('\n```\n\n')
