"""Switching the settings registry off, for tests whose feature names are made up.

A test about the settings stack or condition logic often invents `opensiddur:` features
rather than borrowing real ones, and the registry would refuse them. Decorate such a test
or test class with `unchecked_registry()`, or use it as a context manager. The registry's
own tests, and any test about what it refuses, leave it on.
"""

from unittest.mock import patch


def unchecked_registry():
    """A patch under which every setting passes the registry."""
    return patch.multiple(
        "opensiddur.exporter.feature_registry",
        check_fs_element=lambda *args, **kwargs: [],
        check_yaml_value=lambda *args, **kwargs: [],
    )
