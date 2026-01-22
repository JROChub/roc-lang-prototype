from typing import Optional

from .ast import SourceLoc


def render_diagnostic(
    kind: str,
    message: str,
    source: str,
    loc: Optional[SourceLoc],
    path: Optional[str] = None,
) -> str:
    lines = [f"{kind}: {message}"]
    if loc is None:
        return "\n".join(lines)
    location = f"{loc.line}:{loc.column}"
    if path:
        location = f"{path}:{location}"
    lines.append(f"--> {location}")
    snippet = _format_snippet(source, loc)
    if snippet:
        lines.append(snippet)
    return "\n".join(lines)


def _format_snippet(source: str, loc: SourceLoc) -> str:
    line_index = loc.line - 1
    if line_index < 0:
        return ""
    source_lines = source.splitlines()
    if line_index >= len(source_lines):
        return ""
    line_text = source_lines[line_index]
    width = len(str(loc.line))
    col = max(1, loc.column)
    caret_pos = min(col - 1, len(line_text))
    line_prefix = f"{loc.line:>{width}} | "
    caret_prefix = " " * width + " | "
    caret_line = caret_prefix + (" " * caret_pos) + "^"
    return "\n".join([line_prefix + line_text, caret_line])
