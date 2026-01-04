"""PoC Compiler for Schema → IR compilation."""

from .compiler import compile_project
from .models import CompiledBundle

__all__ = ["compile_project", "CompiledBundle"]

