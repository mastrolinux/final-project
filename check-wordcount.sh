#!/bin/bash

# Word count checker for preliminary report
# This script helps verify each chapter is within word limits

echo "=============================================="
echo "Preliminary Report Word Count Analysis"
echo "=============================================="
echo ""

QMD_FILE="preliminary-report.qmd"

if [ ! -f "$QMD_FILE" ]; then
    echo "Error: $QMD_FILE not found"
    exit 1
fi

# Function to count words in a section
count_section() {
    local start_pattern="$1"
    local end_pattern="$2"
    local section_name="$3"
    local max_words="$4"
    
    # Extract section and count words (excluding code blocks and YAML)
    count=$(sed -n "/$start_pattern/,/$end_pattern/p" "$QMD_FILE" | \
            grep -v '```' | \
            grep -v '^---$' | \
            grep -v '^#' | \
            wc -w | \
            tr -d ' ')
    
    echo "$section_name"
    echo "  Words: $count / $max_words"
    
    if [ "$count" -gt "$max_words" ]; then
        over=$((count - max_words))
        echo "  ⚠️  OVER by $over words"
    else
        under=$((max_words - count))
        echo "  ✓ Under limit ($under words remaining)"
    fi
    echo ""
}

# Approximate word counts (this is an estimate - use actual PDF for accurate count)
echo "Note: These are estimates. For accurate counts, use:"
echo "  - Copy chapter text from PDF and use word processor"
echo "  - Or use: detex preliminary-report.tex | wc -w"
echo ""
echo "=============================================="
echo ""

# Chapter 1: Introduction
count_section "# Introduction" "# Literature Review" "Chapter 1: Introduction" 1000

# Chapter 2: Literature Review  
count_section "# Literature Review" "# Design" "Chapter 2: Literature Review" 2500

# Chapter 3: Design
count_section "# Design" "# Feature Prototype" "Chapter 3: Design" 2000

# Chapter 4: Feature Prototype
count_section "# Feature Prototype" "# Work Plan and Evaluation" "Chapter 4: Feature Prototype" 1500

# Chapter 5: Work Plan and Evaluation
count_section "# Work Plan and Evaluation" "# References" "Chapter 5: Work Plan and Evaluation" 2000

echo "=============================================="
echo "Overall limit: 4500 words (original)"
echo "With feature prototype: 6000 words"
echo "Per-chapter maximums allow flexibility up to 7000"
echo "=============================================="

