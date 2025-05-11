import os
import csv

def field_needs_quotes(field: str) -> bool:
    # If the field contains a comma, parentheses, or quotes and is not quoted already
    return (',' in field or '(' in field or ')' in field or '"' in field) and not (field.startswith('"') and field.endswith('"'))

def quote_field(field: str) -> str:
    # Escape internal quotes and surround with quotes
    return '"' + field.replace('"', '""') + '"'

def process_file(filepath: str) -> bool:
    changed = False
    with open(filepath, newline='', encoding='utf-8') as f:
        lines = list(csv.reader(f))

    new_lines = []
    for row in lines:
        if len(row) < 5:
            new_lines.append(row)
            continue
        name = ','.join(row[4:]).strip()
        if field_needs_quotes(name):
            quoted_name = quote_field(name)
            row = row[:4] + [quoted_name]
            changed = True
        new_lines.append(row)

    if changed:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(new_lines)

    return changed

def main():
    modified = False
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.csv'):
                path = os.path.join(root, file)
                if process_file(path):
                    print(f"✅ Fixed: {path}")
                    modified = True

    if not modified:
        print("✅ No fixes necessary.")

if __name__ == '__main__':
    main()
