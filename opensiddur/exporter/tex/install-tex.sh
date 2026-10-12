#!/bin/bash
# LuaLaTeX-based PDF pipeline (reledmac/reledpar critical-edition typesetting).
#
# Required packages:
#   - texlive-luatex:           lualatex engine + lua* libraries
#   - texlive-latex-extra:      reledmac, reledpar, fancyhdr, xurl, polyglossia helpers
#   - texlive-bibtex-extra:     biblatex (run with backend=bibtex)
#   - texlive-fonts-extra:      fallback font shapes used by polyglossia
#   - texlive-lang-other:       Hebrew (and other RTL) language support
#   - texlive-lang-european:    Latin-script babel support
#   - texlive-lang-arabic:      luabidi, which polyglossia's Hebrew module loads under LuaLaTeX
#
# The exporter runs lualatex and bibtex itself (pdf.py), so neither latexmk nor
# biber is needed; bibtex comes with texlive-binaries, which texlive-luatex pulls in.
set -euo pipefail

apt-get update -y
apt-get install -y \
  texlive-luatex \
  texlive-latex-extra \
  texlive-bibtex-extra \
  texlive-fonts-extra \
  texlive-humanities \
  texlive-lang-other \
  texlive-lang-european \
  texlive-lang-arabic

# Refresh TeX filename database (usually handled by postinst, but cheap/safe).
mktexlsr
