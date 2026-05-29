"""
JPS1917 MediaWiki processor (compatibility wrapper).

The implementation lives in `opensiddur.importer.util.mediawiki_processor` so it
can be reused by other importers.
"""

from opensiddur.importer.util.mediawiki_processor import (  # noqa: F401
    ConversionResult,
    MediaWikiProcessor,
    create_processor,
    process_page,
)

