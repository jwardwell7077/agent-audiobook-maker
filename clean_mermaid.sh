#!/bin/bash

# Fix duplicate mermaid tags and other syntax issues in Mermaid files

cd /home/jon/repos/agent-audiobook-maker/docs/04-diagrams

for file in $(find . -name "*.mmd"); do
    echo "Cleaning $file..."
    
    # Remove duplicate ```mermaid lines and fix structure
    temp_file="${file}.tmp"
    
    # Process the file
    in_code_block=false
    first_mermaid_seen=false
    
    while IFS= read -r line; do
        if [[ "$line" == '```mermaid' ]]; then
            if ! $first_mermaid_seen; then
                echo "$line" >> "$temp_file"
                first_mermaid_seen=true
                in_code_block=true
            fi
            # Skip subsequent ```mermaid lines
        elif [[ "$line" == '```plaintext' ]]; then
            if ! $first_mermaid_seen; then
                echo '```mermaid' >> "$temp_file"
                first_mermaid_seen=true
                in_code_block=true
            fi
            # Skip plaintext tags
        elif [[ "$line" == '```' ]]; then
            if $in_code_block; then
                echo "$line" >> "$temp_file"
                in_code_block=false
            fi
        else
            # Regular content line
            if ! $first_mermaid_seen; then
                # File doesn't start with code block, add it
                echo '```mermaid' >> "$temp_file"
                first_mermaid_seen=true
                in_code_block=true
            fi
            echo "$line" >> "$temp_file"
        fi
    done < "$file"
    
    # If we never closed the code block, close it
    if $in_code_block; then
        echo '```' >> "$temp_file"
    fi
    
    # Replace original file
    mv "$temp_file" "$file"
    echo "  Cleaned $file"
done

echo "All Mermaid files cleaned!"
