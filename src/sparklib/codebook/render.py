"""Placeholder LaTeX rendering for a completed codebook state."""
from collections import defaultdict
from pathlib import Path

_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",  "%": r"\%",  "$": r"\$",  "#": r"\#",
    "_": r"\_",  "{": r"\{",  "}": r"\}",
    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}

def _esc(s) -> str:
    if s is None:
        return ""
    return "".join(_ESCAPES.get(c, c) for c in str(s))


def _render_stats(stats: dict) -> list[str]:
    kind = stats.get("kind")
    lines: list[str] = []
    if kind == "continuous":
        lines.append(
            f"Count: {stats.get('count')}, "
            f"Mean: {stats.get('mean'):.3g}, "
            f"SD: {stats.get('sd'):.3g}, "
            f"Min: {stats.get('min'):.3g}, "
            f"Max: {stats.get('max'):.3g}"
        )
    elif kind == "categorical":
        lines.append(r"\begin{tabular}{rll}")
        lines.append(r"\# & Label & Count \\ \hline")
        for num, lbl, cnt in zip(
            stats.get("value_number", []),
            stats.get("value_label", []),
            stats.get("value_count", []),
        ):
            lines.append(f"{num} & {_esc(lbl)} & {cnt} \\\\")
        lines.append(r"\end{tabular}")
    fig = stats.get("distribution_path")
    if fig:
        lines.append(f"\\includegraphics[width=0.6\\textwidth]{{{fig}}}")
    return lines


def _render_variable(name: str, info: dict) -> list[str]:
    lines = [f"\\subsubsection*{{{_esc(name)}}}"]
    if info.get("description"):
        lines.append(_esc(info["description"]))

    lines.extend(_render_stats(info.get("stats") or {}))

    variants = info.get("suffix_variants") or {}
    if variants:
        lines.append(r"\paragraph{Suffix variants.}")
        for vkey, vinfo in variants.items():
            lines.append(
                f"\\textbf{{+{_esc(vkey)}}} "
                f"(\\texttt{{{_esc(vinfo.get('name', ''))}}})\\\\"
            )
            lines.extend(_render_stats(vinfo.get("stats") or {}))
    return lines


def render_latex(state: dict, output_path: str | Path | None = None) -> str:
    """
    Render a codebook state (final yield of get_variable_groups) to a minimal
    LaTeX document. Each top-level variable is a core with its own description
    and stats; suffix variants nested under it get stats-only blocks. Family
    level suffix meanings come from family.available_suffixes.
    """
    variables: dict[str, dict] = state.get("variables", {})

    grouped: dict[str, list[str]]               = defaultdict(list)
    family_desc: dict[str, str]                 = {}
    family_available: dict[str, dict[str, str]] = {}
    leftovers: list[str] = []

    for name, info in variables.items():
        family = info.get("family")
        if family:
            root = family["root"]
            grouped[root].append(name)
            family_desc.setdefault(root, family.get("family_description", ""))
            family_available.setdefault(root, family.get("available_suffixes", {}) or {})
        else:
            leftovers.append(name)

    lines: list[str] = [
        r"\documentclass{article}",
        r"\usepackage{graphicx}",
        r"\begin{document}",
    ]

    for root, members in grouped.items():
        lines.append(f"\\section{{{_esc(root)}}}")
        if family_desc.get(root):
            lines.append(_esc(family_desc[root]))
        suffixes = family_available.get(root, {})
        if suffixes:
            lines.append(r"\subsection*{Available suffixes}")
            lines.append(r"\begin{itemize}")
            for val, desc in suffixes.items():
                lines.append(f"  \\item \\texttt{{{_esc(val)}}} --- {_esc(desc)}")
            lines.append(r"\end{itemize}")
        lines.append(r"\subsection*{Variables}")
        for var in members:
            lines.extend(_render_variable(var, variables[var]))

    if leftovers:
        lines.append(r"\section{Other Variables}")
        for var in leftovers:
            lines.extend(_render_variable(var, variables[var]))

    lines.append(r"\end{document}")

    out = "\n".join(lines) + "\n"
    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out)
    return out
