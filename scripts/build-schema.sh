#!/bin/bash

scripts/tei-stylesheets.sh teitorelaxng jlptei.odd.xml jlptei.odd.xml.relaxng
scripts/tei-stylesheets.sh teitoschematron jlptei.odd.xml jlptei.odd.xml.schematron
poetry run python opensiddur/common/xslt.py -o schema/jlptei.odd.xml.schematron.xslt scripts/schxslt2/transpile.xsl schema/jlptei.odd.xml.schematron