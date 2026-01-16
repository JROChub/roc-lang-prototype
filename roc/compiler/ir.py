from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class IRFunction:
  name: str
  params: List[str]
  return_type: Optional[str] = None
  body: List[str] = field(default_factory=list)

@dataclass
class IRModule:
  functions: List[IRFunction] = field(default_factory=list)

  def pretty(self) -> str:
    lines = []
    for fn in self.functions:
      ret = f" -> {fn.return_type}" if fn.return_type is not None else ""
      lines.append(f"fn {fn.name}({', '.join(fn.params)}){ret} {{")
      for stmt in fn.body:
        lines.append(f"  {stmt}")
      lines.append("}\n")
    return "\n".join(lines)
