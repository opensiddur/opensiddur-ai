#!/bin/bash

#command can be teitorelaxng, teitornc, teitomarkdown, teitohtml5, teitopdf, teitoschematron
COMMAND="/usr/local/share/xml/tei/stylesheet/bin/$1"
INPUT="$2"
OUTPUT="$3"

podman pull ghcr.io/joeytakeda/docker-tei-stylesheets:main
podman run --rm -v $(pwd)/schema:/tei ghcr.io/joeytakeda/docker-tei-stylesheets:main "$COMMAND" --odd "$INPUT" "$OUTPUT"
