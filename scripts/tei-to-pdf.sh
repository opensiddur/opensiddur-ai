#!/bin/bash

# This script converts a TEI file to a PDF file using the Open Siddur TEI to PDF converter.

# Usage:
# ./tei-to-pdf.sh <project> <file_name> <output-file>

# Example:
# ./tei-to-pdf.sh  output.pdf

# The input file should be a valid TEI file.
# The output file will be a PDF file.


poetry run python -m opensiddur.exporter.compiler -p $1 -f $2 -o $3.xml
poetry run python -m opensiddur.exporter.pdf.pdf $3.xml $3 
rm -f $3.xml
