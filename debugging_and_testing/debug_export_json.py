# debugging_and_testing/debug_export_json.py
import os
import sqlite3
import json
import sys

# Ensure synapse is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from debugging_and_testing.debug_database import DEBUG_PROGRESS_DB, DEBUG_WORKSPACE_DB

def export_db(db_path, output_json):
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. Skipping.")
        return

    export_data = {}
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for t in tables:
            table_name = t['name']
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            table_data = []
            for row in rows:
                row_dict = dict(row)
                
                # Attempt to parse json strings so the final structure is deeply nested and readable
                for key, val in row_dict.items():
                    if isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                        try:
                            row_dict[key] = json.loads(val)
                        except json.JSONDecodeError:
                            pass # Keep as string if it isn't valid JSON
                            
                table_data.append(row_dict)
                
            export_data[table_name] = table_data
            
    with open(output_json, 'w') as f:
        json.dump(export_data, f, indent=4)
        
    print(f"Exported {db_path} to {output_json}")

if __name__ == "__main__":
    export_db(DEBUG_PROGRESS_DB, "debugging_and_testing/debug_progress_dump.json")
    export_db(DEBUG_WORKSPACE_DB, "debugging_and_testing/debug_workspace_dump.json")
    print("Database export complete.")
