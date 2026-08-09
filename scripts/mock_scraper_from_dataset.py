import json
import sys
import os

def mock_cache(problem_id):
    best_record = None
    with open('dataset.jsonl', 'r') as f:
        for line in f:
            if not line.strip(): continue
            record = json.loads(line)
            if record['problem_id'] == problem_id:
                best_record = record

    if not best_record:
        print(f"Problem {problem_id} not found in dataset.jsonl")
        return False

    ref = best_record['reference_solution']
    meta = best_record['problem_metadata']
    # Reconstruct the codeforces API 'submission' object as expected by data assembly
    submission_object = {
        'id': ref['submission_id'],
        'contestId': ref['submission_url'].split('/contest/')[1].split('/')[0] if '/contest/' in ref['submission_url'] else problem_id[:-1],
        'problem': {
            'contestId': ref['submission_url'].split('/contest/')[1].split('/')[0] if '/contest/' in ref['submission_url'] else problem_id[:-1],
            'index': problem_id[-1],
            'name': meta['name'],
            'tags': meta['tags']
        },
        'author': {
            'members': [{'handle': ref['author_handle']}],
            'rating': ref.get('author_rating')
        },
        'programmingLanguage': ref['language']
    }

    cache_data = {
        "ingestion": {
            "problem_id": problem_id,
            "page_details": {
                "problem_statement_html": best_record['problem_statement_html'],
                "time_limit_raw": f"{meta['time_limit_ms']} ms",
                "memory_limit_raw": f"{meta['memory_limit_kb']} kb",
                "example_pretests": best_record['pretests']
            },
            "successful_solutions": [
                {
                    "submission_object": submission_object,
                    "source_code": ref['code']
                } for _ in range(5)
            ],
            "pretests": best_record['pretests']
        }
    }

    cache_file = f"debug_v2_cache_{problem_id}.json"
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)
    print(f"Mocked scraper cache for {problem_id} into {cache_file}")
    return True

if __name__ == '__main__':
    for p in sys.argv[1:]:
        mock_cache(p)
