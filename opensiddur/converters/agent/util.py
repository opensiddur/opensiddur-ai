"""
Simple validation utility for testing purposes.
"""

from typing import Tuple, List


def validate(xml: str, schema: str = None, schematron: str = None) -> Tuple[bool, List[str]]:
    """
    Simple validation function for testing.
    Always returns True with no errors for now.
    """
    return True, []
