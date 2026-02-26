#!/usr/bin/env python3
"""
Track data changes and log execution history for keyPenangMetrics.
Detects actual data changes vs. script execution.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path


def compute_data_hash(data):
    """
    Compute MD5 hash of metrics data for change detection.

    Args:
        data: List of metric dictionaries

    Returns:
        str: Hexadecimal hash string
    """
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()


def load_history():
    """
    Load execution history from data_history/history.json.

    Returns:
        list: List of historical execution records
    """
    history_file = Path('data_history/history.json')
    if history_file.exists():
        with open(history_file) as f:
            return json.load(f)
    return []


def detect_changes(current_data):
    """
    Compare current data with last execution to detect changes.

    Args:
        current_data: List of current metric dictionaries

    Returns:
        dict: Dictionary mapping metric names to change details
    """
    history = load_history()

    if not history:
        return {'_initial': 'First run - no previous data to compare'}

    last_run = history[-1]
    changes = {}

    for metric in current_data:
        metric_name = metric['dataset']

        # Find corresponding metric in last run
        last_metric = next(
            (m for m in last_run['data'] if m['dataset'] == metric_name),
            None
        )

        if last_metric:
            # Check if value or date changed
            value_changed = metric['value'] != last_metric['value']
            date_changed = metric['date_format'] != last_metric['date_format']

            if value_changed or date_changed:
                changes[metric_name] = {
                    'old_value': last_metric['value'],
                    'new_value': metric['value'],
                    'old_date': last_metric['date_format'],
                    'new_date': metric['date_format'],
                    'value_changed': value_changed,
                    'date_changed': date_changed
                }
        else:
            # New metric not in previous run
            changes[metric_name] = {
                'new_value': metric['value'],
                'new_date': metric['date_format'],
                'status': 'new_metric'
            }

    return changes


def log_execution(data, changes, success=True, error=None, duration=None):
    """
    Log execution details to data_history/history.json.

    Args:
        data: List of metric dictionaries
        changes: Dictionary of detected changes
        success: Boolean indicating if execution succeeded
        error: Error message if execution failed
        duration: Execution time in seconds
    """
    history = load_history()

    # Create execution record
    record = {
        'timestamp': datetime.now().isoformat(),
        'data': data,
        'data_hash': compute_data_hash(data),
        'changes': changes,
        'success': success,
        'error': str(error) if error else None,
        'duration_seconds': duration
    }

    history.append(record)

    # Keep last 100 executions to avoid file bloat
    history = history[-100:]

    # Ensure directory exists
    Path('data_history').mkdir(exist_ok=True)

    # Save updated history
    with open('data_history/history.json', 'w') as f:
        json.dump(history, f, indent=2)


def get_change_summary(changes):
    """
    Generate human-readable summary of changes.

    Args:
        changes: Dictionary of changes from detect_changes()

    Returns:
        str: Formatted summary string
    """
    if not changes:
        return "No changes detected"

    if '_initial' in changes:
        return changes['_initial']

    summary_parts = []
    for metric_name, change_details in changes.items():
        if 'status' in change_details and change_details['status'] == 'new_metric':
            summary_parts.append(f"{metric_name}: NEW")
        else:
            parts = []
            if change_details.get('value_changed'):
                parts.append(f"value {change_details['old_value']} → {change_details['new_value']}")
            if change_details.get('date_changed'):
                parts.append(f"date {change_details['old_date']} → {change_details['new_date']}")
            summary_parts.append(f"{metric_name}: {', '.join(parts)}")

    return "; ".join(summary_parts)


if __name__ == "__main__":
    # Test change detection
    print("Testing change detection...")

    test_data = [
        {'dataset': 'Population', 'value': '1.80mil', 'date_format': '2025'},
        {'dataset': 'GDP growth', 'value': '3.27%', 'date_format': '2023'}
    ]

    changes = detect_changes(test_data)
    print(f"Changes detected: {changes}")
    print(f"Summary: {get_change_summary(changes)}")

    log_execution(test_data, changes, success=True, duration=10.5)
    print("Logged execution to data_history/history.json")
