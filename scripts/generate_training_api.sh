#!/bin/bash

# Check for required parameters
if [ "$#" -ne 2 ]; then
    echo "❌ Usage: $0 <input_directory> <output_directory>"
    exit 1
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"

# Check if input directory exists
if [ ! -d "$INPUT_DIR" ]; then
    echo "❌ Error: Input directory '$INPUT_DIR' does not exist."
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Process PDF files
find "$INPUT_DIR" -name '*.pdf' | while read -r x; do
    filename=$(basename "$x" .pdf)
    output="${OUTPUT_DIR}/${filename}.zip"

    echo "📄 Processing: $x → $output"

    curl --silent --location 'https://lfoppiano-grobid-dev-dh-law.hf.space/api/createTraining' \
         --form "input=@${x}" \
         --output "$output"
done

