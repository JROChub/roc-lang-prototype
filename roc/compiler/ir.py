from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class IREnum:
  name: str
  variants: List[str]

@dataclass
class IRFunction:
  name: str
  params: List[str]
  return_type: Optional[str] = None
  body: List[str] = field(default_factory=list)

@dataclass
class IRModule:
  functions: List[IRFunction] = field(default_factory=list)
  enums: List[IREnum] = field(default_factory=list)
  imports: List[str] = field(default_factory=list)
  exports: List[List[str]] = field(default_factory=list)

  def pretty(self) -> str:
    lines = []
    for imp in self.imports:
      lines.append(f"import {imp};")
    for names in self.exports:
      items = ", ".join(names)
      lines.append(f"export {{ {items} }};")
    if self.imports or self.exports:
      lines.append("")
    for enum in self.enums:
      variants = ", ".join(enum.variants)
      lines.append(f"enum {enum.name} {{ {variants} }}\n")
    for fn in self.functions:
      ret = f" -> {fn.return_type}" if fn.return_type is not None else ""
      lines.append(f"fn {fn.name}({', '.join(fn.params)}){ret} {{")
      for stmt in fn.body:
        lines.append(f"  {stmt}")
      lines.append("}\n")
    return "\n".join(lines)
