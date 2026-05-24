# LuaLaTeX-based PDF pipeline (reledmac/reledpar critical-edition typesetting).
#
# Required packages:
#   - texlive-luatex:           lualatex engine + lua* libraries
#   - texlive-latex-extra:      reledmac, reledpar, polyglossia helpers
#   - texlive-bibtex-extra:     biblatex with the biber backend
#   - texlive-fonts-extra:      fallback font shapes used by polyglossia
#   - texlive-lang-other:       Hebrew (and other RTL) language support
#   - texlive-lang-european:    Latin-script babel support
#   - latexmk:                  drives multi-pass lualatex/biber loop
#   - biber:                    biblatex's bibliography backend
apt-get update -y
apt-get install -y \
  texlive-luatex \
  texlive-latex-extra \
  texlive-bibtex-extra \
  texlive-fonts-extra \
  texlive-humanities \
  texlive-lang-other \
  texlive-lang-european \
  latexmk \
  biber

# Refresh TeX filename database (usually handled by postinst, but cheap/safe).
mktexlsr
