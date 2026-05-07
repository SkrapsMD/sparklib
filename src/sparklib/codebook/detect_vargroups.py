"""
detect.py — Pure detection functions for variable name structure.

All functions are stateless: data in, structure out, no I/O.
Frozen dataclasses for return types. No class methods.

Two-stage pipeline:
    1. Prefix detection  — find_prefix_groups()
    2. Suffix peeling     — peel_one() / peel_all()

The suffix algorithm works right-to-left: it finds the longest
trailing token sequence that partitions the family into shared
groups, peels it off, and repeats.

When a separator is available (inferred or explicit), tokenization
splits on that character — clean and reliable. When no separator
exists (camelCase, concatenated names), tokenization falls back to
individual characters. Since every suffix is confirmed by the user
in the interactive layer, aggressive detection is safe.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Hashable


# ── Data Containers ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SuffixLayer:
    """
    One peeled suffix, possibly multi-token.

    depth:  Number of tokens from the right (1 = last token, 2 = last two, …).
            When operating in character mode, depth = number of characters.
    values: The distinct suffix strings found.
    """
    depth:  int
    values: frozenset[str]


@dataclass(frozen=True)
class PeelResult:
    """
    Full right-to-left suffix analysis of a variable family.

    layers:    Suffix layers in the order they were peeled (rightmost first).
    cores:     Mapping of variable → residual string left after all peels.
               Empty string means the variable was fully decomposed.
    short:     Variables whose residuals were too short to participate
               in a peel round.
    bare_root: True if the root itself (no suffix at all) is a member.
    sep:       The separator used (None if character-level fallback).
    """
    root:      str
    variables: tuple[str, ...]
    layers:    tuple[SuffixLayer, ...]
    cores:     dict[str, str]
    short:     tuple[str, ...]    = ()
    bare_root: bool               = False
    sep:       str | None         = None


# ── Tokenization ─────────────────────────────────────────────────────────────

def infer_sep(strings: list[str]) -> str | None:
    """
    Infer the delimiter from a list of strings.

    Returns the most frequent non-alphanumeric character, or None
    if no such character exists (camelCase, concatenated names, etc.).
    """
    counts: dict[str, int] = defaultdict(int)
    for s in strings:
        for ch in s:
            if not ch.isalnum():
                counts[ch] += 1
    return max(counts, key=counts.get) if counts else None


def _tokenize(s: str, sep: str | None) -> tuple[str, ...]:
    """Split by sep, or into individual characters if sep is None."""
    if sep is not None:
        return tuple(s.split(sep))
    return tuple(s)


def _join(tokens: tuple[str, ...] | list[str], sep: str | None) -> str:
    """Inverse of _tokenize."""
    if sep is not None:
        return sep.join(tokens)
    return "".join(tokens)


# ── Prefix Detection ─────────────────────────────────────────────────────────

def _common_prefix(strings: list[str]) -> str:
    """Longest common prefix via lexicographic sort trick."""
    if not strings:
        return ""
    s = sorted(strings)
    first, last = s[0], s[-1]
    for i, ch in enumerate(first):
        if i >= len(last) or ch != last[i]:
            return first[:i]
    return first


def find_prefix_groups(
    var_names:         list[str],
    min_group_size:    int = 4,
    min_prefix_length: int = 4,
    max_prefix_scan:   int = 20,
    sep:               str | None = None,
) -> dict[str, list[str]]:
    """
    Greedy longest-prefix-first grouping of variable names.

    Sweeps prefix lengths from max_prefix_scan down to min_prefix_length.
    At each length k, bins variables by their first k characters, keeps bins
    with >= min_group_size members, refines each via _common_prefix, strips
    trailing separators, and marks matched variables as used.

    Bare roots (a variable whose name equals a discovered root) are absorbed.

    If sep is None, it is inferred from the data. If no separator is found,
    prefix stripping uses character boundaries only (no trailing-sep cleanup).

    Returns:
        dict[str, list[str]] — root → sorted members, insertion-ordered
        longest-prefix-first.
    """
    if sep is None:
        sep = infer_sep(var_names)

    used:    set[str]             = set()
    groups:  dict[str, list[str]] = {}
    var_set: set[str]             = set(var_names)

    for k in range(max_prefix_scan, min_prefix_length - 1, -1):
        remaining = [v for v in var_names if v not in used]

        bins: dict[str, list[str]] = defaultdict(list)
        for v in remaining:
            if len(v) >= k:
                bins[v[:k]].append(v)

        for _prefix, members in bins.items():
            if len(members) < min_group_size:
                continue

            root = _common_prefix(members)
            if sep is not None:
                root = root.rstrip(sep)
            if len(root) < min_prefix_length:
                continue

            if any(v in used for v in members):
                continue

            groups[root] = sorted(members)
            used.update(members)

    # Absorb bare roots
    for root, members in groups.items():
        if root not in used and root in var_set:
            groups[root] = sorted(members + [root])
            used.add(root)

    return groups


def ungrouped(var_names: list[str], groups: dict[str, list[str]]) -> list[str]:
    """Variables not claimed by any group."""
    claimed = set()
    for members in groups.values():
        claimed.update(members)
    return [v for v in var_names if v not in claimed]


# ── Suffix Peeling ───────────────────────────────────────────────────────────

def _strip_root(var: str, root: str, sep: str | None) -> str:
    """Remove root prefix and leading separators."""
    residual = var[len(root):]
    if sep is not None:
        residual = residual.lstrip(sep)
    return residual


def peel_one(
    residuals:  dict[Hashable, str],
    sep:        str | None = None,
    min_shared: int = 2,
) -> tuple[SuffixLayer, dict[Hashable, str], dict[Hashable, str]] | None:
    """
    Find and strip the rightmost suffix from a keyed set of residuals.

    Keys are opaque — variable names, indices, anything hashable.
    This function never inspects them; it just passes them through.

    When sep is a string, residuals are tokenized by that delimiter.
    When sep is None, each character is a token (character-level peeling).

    Algorithm:
        1. Tokenize each residual.
        2. Starting at depth=1, group by trailing d tokens.
        3. Valid suffix: >= 2 distinct values, at least one shared >= min_shared times.
        4. Increase depth while the number of groups does not increase.
        5. When groups fragment, stop — previous depth is the suffix.

    Returns:
        (layer, peeled, short) or None if no suffix detected.

        layer:  SuffixLayer with the detected suffix values.
        peeled: key → residual with suffix stripped.
        short:  key → original residual, for keys too short to participate.
    """
    if not residuals:
        return None

    # Tokenize
    keyed: list[tuple[Hashable, str, tuple[str, ...]]] = []
    for key, res in residuals.items():
        if res:
            keyed.append((key, res, _tokenize(res, sep)))

    if len(keyed) < min_shared:
        return None

    # ── Sweep depths ─────────────────────────────────────────────────
    best_depth    = 0
    best_n_groups = None
    max_len       = max(len(toks) for _, _, toks in keyed)

    for d in range(1, max_len + 1):
        eligible = [(k, r, t) for k, r, t in keyed if len(t) >= d]

        if len(eligible) < min_shared:
            break

        groups: dict[tuple[str, ...], int] = defaultdict(int)
        for _, _, toks in eligible:
            groups[toks[-d:]] += 1

        n_groups   = len(groups)
        n_eligible = len(eligible)

        if n_groups >= n_eligible:
            if best_depth > 0:
                break
            break
        if n_groups < 2:
            if best_depth > 0:
                break
            continue

        if not any(c >= min_shared for c in groups.values()):
            if best_depth > 0:
                break
            continue

        if best_n_groups is not None and n_groups > best_n_groups:
            break

        best_depth    = d
        best_n_groups = n_groups

    if best_depth == 0:
        return None

    # ── Build result ─────────────────────────────────────────────────
    suffix_values: set[str] = set()
    peeled: dict[Hashable, str] = {}
    short:  dict[Hashable, str] = {}

    for key, res, toks in keyed:
        if len(toks) >= best_depth:
            trailing  = _join(toks[-best_depth:], sep)
            remainder = _join(toks[:-best_depth], sep) if len(toks) > best_depth else ""
            suffix_values.add(trailing)
            peeled[key] = remainder
        else:
            short[key] = res

    layer = SuffixLayer(depth=best_depth, values=frozenset(suffix_values))
    return layer, peeled, short


def peel_all(
    root:       str,
    variables:  list[str],
    sep:        str | None = None,
    min_shared: int = 2,
) -> PeelResult:
    """
    Repeatedly peel suffixes right-to-left until no more are found.

    If sep is None, it is inferred from the residuals (after stripping root).
    """
    bare   = False
    active: dict[str, str] = {}

    # Infer sep from the residuals, not the full variable names,
    # since the root portion may have different separator patterns.
    raw_residuals = []
    for v in variables:
        residual = _strip_root(v, root, sep)
        if not residual:
            bare = True
        else:
            active[v] = residual
            raw_residuals.append(residual)

    if sep is None:
        sep = infer_sep(raw_residuals)

    # Re-strip with the inferred sep (leading sep chars may need trimming)
    if sep is not None:
        active = {}
        for v in variables:
            residual = _strip_root(v, root, sep)
            if residual:
                active[v] = residual

    layers:    list[SuffixLayer] = []
    all_short: dict[str, str]    = {}

    while active:
        result = peel_one(active, sep=sep, min_shared=min_shared)
        if result is None:
            break

        layer, peeled, short = result
        layers.append(layer)
        all_short.update(short)
        active = peeled

    cores = dict(sorted({**active, **all_short}.items()))

    return PeelResult(
        root      = root,
        variables = tuple(sorted(variables)),
        layers    = tuple(layers),
        cores     = cores,
        short     = tuple(sorted(all_short.keys())),
        bare_root = bare,
        sep       = sep,
    )


# ── Pipeline ─────────────────────────────────────────────────────────────────

def detect_all(
    var_names:         list[str],
    min_group_size:    int = 4,
    min_prefix_length: int = 4,
    sep:               str | None = None,
) -> tuple[list[PeelResult], list[str]]:
    """
    Full pipeline: prefix grouping → suffix peeling for each group.

    If sep is None, it is inferred from the variable names.

    Returns:
        (results, leftover) where leftover = ungrouped variable names.
    """
    if sep is None:
        sep = infer_sep(var_names)

    groups   = find_prefix_groups(var_names, min_group_size, min_prefix_length, sep=sep)
    results  = [peel_all(root, members, sep=sep) for root, members in groups.items()]
    leftover = ungrouped(var_names, groups)
    return results, leftover
