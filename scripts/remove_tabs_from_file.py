import sys

if len(sys.argv) != 2:
    print("Usage: python remove_tabs_from_file.py <file_path>")
    sys.exit(1)

file_path = sys.argv[1]

with open(file_path, encoding="utf-8") as f:
    lines = f.readlines()

with open(file_path, "w", encoding="utf-8") as f:
    for line in lines:
        f.write(line.replace("\t", "    "))
