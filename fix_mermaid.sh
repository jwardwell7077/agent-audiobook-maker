#!/bin/bash

# Fix all Mermaid diagram files to have proper syntax

cd /home/jon/repos/agent-audiobook-maker/docs/04-diagrams

for file in $(find . -name "*.mmd"); do
    echo "Fixing $file..."
    
    # Check if file starts with ```mermaid already
    if head -1 "$file" | grep -q "^```mermaid"; then
        echo "  Already has mermaid tag"
        continue
    fi
    
    # Check if file starts with plaintext tag
    if head -1 "$file" | grep -q "^```plaintext"; then
        echo "  Converting plaintext to mermaid"
        sed -i '1s/^```plaintext$/```mermaid/' "$file"
        continue
    fi
    
    # File doesn't have any code block tags, add them
    echo "  Adding mermaid code blocks"
    
    # Create temp file with mermaid wrapper
    {
        echo '```mermaid'
        cat "$file"
        echo '```'
    } > "${file}.tmp"
    
    mv "${file}.tmp" "$file"
    echo "  Fixed $file"
done

echo "All Mermaid files processed!"
