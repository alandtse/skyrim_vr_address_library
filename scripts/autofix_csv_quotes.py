import os
import csv
import io

def process_file(filepath: str) -> int:
    # Read original content
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        original_content = f.read()

    # Parse with csv.reader
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))

    # Write back with csv.writer using QUOTE_MINIMAL
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerows(rows)
    new_content = output.getvalue()

    # Only count lines that actually have different content
    changes_count = 0
    if original_content != new_content:
        original_lines = original_content.strip().split('\n')
        new_lines = new_content.strip().split('\n')

        for orig_line, new_line in zip(original_lines, new_lines):
            # Only count as changed if the content is actually different
            # This catches cases where quoting was added or modified
            if orig_line.strip() != new_line.strip():
                changes_count += 1

        # Write the updated file
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            f.write(new_content)

    return changes_count

def main():
    import sys

    # If specific files are provided as arguments, process only those
    if len(sys.argv) > 1:
        files_to_process = sys.argv[1:]
    else:
        # Default behavior: find all CSV files
        files_to_process = []
        for root, _, files in os.walk('.'):
            for file in files:
                if file.endswith('.csv'):
                    files_to_process.append(os.path.join(root, file))

    total_fixes = 0
    for filepath in files_to_process:
        if filepath.endswith('.csv') and os.path.exists(filepath):
            fixes_count = process_file(filepath)
            if fixes_count > 0:
                entry_word = "entry" if fixes_count == 1 else "entries"
                print(f"✅ Fixed {fixes_count} {entry_word} in: {filepath}")
                total_fixes += fixes_count

    if total_fixes == 0:
        print("✅ No fixes necessary.")

if __name__ == '__main__':
    main()
