"""Export questionnaire data from SQLite to CSV.

This script reads all questionnaire responses from the questionnaire.db database
and exports them to a CSV file for further analysis.
"""

import sqlite3
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def connect_to_database(db_path: str) -> sqlite3.Connection:
    """Connect to the questionnaire database."""
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Database not found at: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def flatten_json_field(data: Any, prefix: str) -> Dict[str, Any]:
    """Flatten a JSON object into a flat dictionary with prefixed keys."""
    if not data or data == '{}' or data == '[]':
        return {}

    flattened = {}

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{prefix}_{key}"
            if isinstance(value, (dict, list)):
                flattened[new_key] = json.dumps(value)
            else:
                flattened[new_key] = value
    elif isinstance(data, list):
        flattened[prefix] = json.dumps(data)
    else:
        flattened[prefix] = data

    return flattened


def parse_row(row: sqlite3.Row) -> Dict[str, Any]:
    """Parse a database row and flatten JSON fields."""
    row_dict = dict(row)
    parsed = {}

    # JSON fields that need to be parsed and flattened
    json_fields = {
        'task_type': 'task_type',
        'task_success': 'task_success',
        'info_finding': 'info_finding',
        'doc_quality': 'doc_quality',
        'info_adequacy': 'info_adequacy',
        'ueq_s': 'ueq_s',
        'trust_scale': 'trust_scale',
        'nasa_tlx': 'nasa_tlx',
        'conversational_quality': 'conversational_quality',
        'stp_evaluation': 'stp_evaluation',
        'kg_visualization': 'kg_visualization',
        'multilingual': 'multilingual',
        'rag_transparency': 'rag_transparency',
        'behavioral_intentions': 'behavioral_intentions',
        'time_per_section': 'time_per_section'
    }

    # Simple fields - copy directly
    simple_fields = [
        'id', 'participant_id', 'email', 'age_range', 'education_level',
        'country', 'native_language', 'prior_climate_knowledge',
        'prior_ai_experience', 'consent_all', 'primary_purpose',
        'other_purpose', 'used_kg_viz', 'used_non_english',
        'most_useful_features', 'suggested_improvements',
        'additional_comments', 'submission_date', 'time_started',
        'total_time_seconds', 'created_at'
    ]

    for field in simple_fields:
        if field in row_dict:
            parsed[field] = row_dict[field]

    # Parse and flatten JSON fields
    for field, prefix in json_fields.items():
        if field in row_dict and row_dict[field]:
            try:
                json_data = json.loads(row_dict[field])
                flattened = flatten_json_field(json_data, prefix)
                parsed.update(flattened)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, store as string
                parsed[field] = row_dict[field]

    return parsed


def export_to_csv(db_path: str, output_path: str):
    """Export questionnaire data to CSV file."""
    print(f"Connecting to database: {db_path}")
    conn = connect_to_database(db_path)

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM questionnaire_responses ORDER BY created_at DESC")
        rows = cursor.fetchall()

        if not rows:
            print("No questionnaire responses found in database.")
            return

        print(f"Found {len(rows)} questionnaire response(s)")

        # Parse all rows
        parsed_rows = [parse_row(row) for row in rows]

        # Collect all unique column names across all rows
        all_columns = set()
        for row in parsed_rows:
            all_columns.update(row.keys())

        # Sort columns for consistent ordering
        columns = sorted(all_columns)

        # Write to CSV
        print(f"Writing to CSV: {output_path}")
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            writer.writerows(parsed_rows)

        print(f"✅ Successfully exported {len(rows)} responses to {output_path}")
        print(f"   Total columns: {len(columns)}")

    except Exception as e:
        print(f"❌ Error during export: {e}")
        raise
    finally:
        conn.close()


def main():
    """Main function to export questionnaire data."""
    # Set paths relative to script location
    script_dir = Path(__file__).parent
    db_path = script_dir.parent / "data" / "questionnaire.db"

    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = script_dir / f"questionnaire_export_{timestamp}.csv"

    try:
        export_to_csv(str(db_path), str(output_path))
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print(f"   Please ensure the database exists at: {db_path}")
    except Exception as e:
        print(f"❌ Export failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
