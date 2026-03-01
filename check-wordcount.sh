#!/bin/bash

# Word count checker for draft/final report
# This script helps verify each chapter is within word limits

echo "=============================================="
echo "Final Report Word Count Analysis"
echo "=============================================="
echo ""

QMD_FILE="draft-report.qmd"

if [ ! -f "$QMD_FILE" ]; then
    echo "Error: $QMD_FILE not found"
    exit 1
fi

# Function to count words in a section (excluding code blocks, mermaid, YAML, LaTeX)
count_section() {
    local start_pattern="$1"
    local end_pattern="$2"
    local section_name="$3"
    local max_words="$4"

    # Extract section, remove code blocks (``` to ```), headings, YAML, LaTeX commands
    count=$(sed -n "/$start_pattern/,/$end_pattern/p" "$QMD_FILE" | \
            sed '/^```/,/^```/d' | \
            grep -v '```' | \
            grep -v '^---$' | \
            grep -v '^#' | \
            grep -v '^\\\\' | \
            grep -v '^%%|' | \
            grep -v '^|' | \
            grep -v '^\!' | \
            grep -v '^:' | \
            wc -w | \
            tr -d ' ')

    echo "$section_name"
    echo "  Words: $count / $max_words"

    if [ "$count" -gt "$max_words" ]; then
        over=$((count - max_words))
        echo "  OVER by $over words"
    else
        under=$((max_words - count))
        echo "  Under limit ($under words remaining)"
    fi
    echo ""
}

echo "Note: These are estimates excluding code blocks, tables,"
echo "      figures, mermaid diagrams, and LaTeX commands."
echo "      For accurate counts, use the rendered PDF."
echo ""
echo "=============================================="
echo ""

# Chapter 1: Introduction
count_section "# Introduction" "# Literature Review" "Chapter 1: Introduction" 1000

# Chapter 2: Literature Review
count_section "# Literature Review" "# Design" "Chapter 2: Literature Review" 2500

# Chapter 3: Design
count_section "# Design" "# Implementation" "Chapter 3: Design" 2000

# Chapter 4: Implementation
count_section "# Implementation" "# Evaluation" "Chapter 4: Implementation" 2500

# Chapter 5: Evaluation
count_section "# Evaluation" "# Conclusion" "Chapter 5: Evaluation" 2500

# Chapter 6: Conclusion
count_section "# Conclusion" "# Appendix A" "Chapter 6: Conclusion" 1000

# Calculate total
total=0
for section in "# Introduction:# Literature Review" "# Literature Review:# Design" "# Design:# Implementation" "# Implementation:# Evaluation" "# Evaluation:# Conclusion" "# Conclusion:# Appendix A"; do
    start=$(echo "$section" | cut -d: -f1)
    end=$(echo "$section" | cut -d: -f2)
    c=$(sed -n "/$start/,/$end/p" "$QMD_FILE" | \
        sed '/^```/,/^```/d' | \
        grep -v '```' | \
        grep -v '^---$' | \
        grep -v '^#' | \
        grep -v '^\\\\' | \
        grep -v '^%%|' | \
        grep -v '^|' | \
        grep -v '^\!' | \
        grep -v '^:' | \
        wc -w | \
        tr -d ' ')
    total=$((total + c))
done

echo "=============================================="
echo "Total (main body): $total / 10500"
if [ "$total" -gt 10500 ]; then
    over=$((total - 10500))
    echo "OVER TOTAL LIMIT by $over words"
else
    under=$((10500 - total))
    echo "Under total limit ($under words remaining)"
fi
echo "=============================================="
