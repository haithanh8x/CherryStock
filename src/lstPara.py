"""Compatibility bridge for legacy absolute imports.

This module lets existing `from lstPara import ...` imports work when
executing scripts directly from the src tree.
"""

from Ults.lstPara import *  # noqa: F401,F403
