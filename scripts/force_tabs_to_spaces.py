import sys

if len(sys.argv) != 2:
    print("Usage: python force_tabs_to_spaces.py <file_path>")
    sys.exit(1)

file_path = sys.argv[1]

with open(file_path, encoding="utf-8") as f:
    content = f.read()

# Replace all tab characters with four spaces
content = content.replace("\t", "    ")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
