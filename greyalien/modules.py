from dataclasses import dataclass
from typing import Dict

from . import ast


@dataclass(frozen=True)
class ModuleExports:
    name: str
    functions: Dict[str, ast.FunctionDef]
    enums: Dict[str, ast.EnumDef]
    variants: Dict[str, str]
    exported_functions: Dict[str, ast.FunctionDef]
    exported_enums: Dict[str, ast.EnumDef]
    exported_variants: Dict[str, str]


@dataclass(frozen=True)
class ModuleInfo:
    name: str
    program: ast.Program
    path: str
    imports: Dict[str, str]
    exports: ModuleExports
