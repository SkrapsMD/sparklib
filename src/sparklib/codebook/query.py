import copy
from pathlib import Path
from typing import Iterator

import pandas as pd

from sparklib.utils.logging.core import log
from sparklib.utils.aesthetics.palettes import LogColors as LC

from .detect_vargroups import infer_sep, find_prefix_groups, ungrouped, peel_one


def get_value_labels(value_counts: pd.Series) -> dict:
    """
    Display a table of unique values (value, count, share) and prompt the user
    for a human-readable label for each value via questionary.

    Parameters:
    value_counts - pd.Series with unique values as index and counts as values.

    Returns:
    dict mapping each original value to the label the user provided.
    """
    try:
        import questionary
    except ImportError:
        log(f"{LC.WARN}Install codebook extras: pip install sparklib[codebook]{LC.END}")
        return {v: str(v) for v in value_counts.index}

    total = int(value_counts.sum())
    values = list(value_counts.index)
    counts = [int(c) for c in value_counts.values]
    shares = [f"{(c / total * 100.0 if total else 0.0):.2f}%" for c in counts]

    val_w = max(len("Value"), max((len(str(v)) for v in values), default=0))
    cnt_w = max(len("Count"), max((len(str(c)) for c in counts), default=0))
    shr_w = max(len("Share"), max((len(s) for s in shares), default=0))

    with log.section(f"{LC.FUNC}Value Labels{LC.END}"):
        log(f"{LC.BOLD}{'Value':<{val_w}}  {'Count':>{cnt_w}}  {'Share':>{shr_w}}{LC.END}")
        log(f"{LC.DBG}{'-' * (val_w + cnt_w + shr_w + 4)}{LC.END}")
        for v, c, s in zip(values, counts, shares):
            log(
                f"{LC.PATH}{str(v):<{val_w}}{LC.END}  "
                f"{LC.VAL}{c:>{cnt_w}}{LC.END}  "
                f"{LC.METR}{s:>{shr_w}}{LC.END}"
            )

        labels: dict = {}
        for v in values:
            ans = questionary.text(
                f"Label for value '{v}':",
                default=str(v),
            ).ask()
            if ans is None:
                log(f"{LC.INFO}Cancelled; remaining values fall back to their string form.{LC.END}")
                for w in values:
                    labels.setdefault(w, str(w))
                return labels
            labels[v] = ans.strip() or str(v)
        return labels


# ── Variable-group detection orchestrator ────────────────────────────────────

def _strip_root(var: str, root: str, sep: str | None) -> str:
    residual = var[len(root):]
    if sep is not None:
        residual = residual.lstrip(sep)
    return residual


def _format_member(member: str, root: str) -> str:
    residual = member[len(root):]
    return f"{LC.INFO}{root}{LC.PATH}{residual}{LC.END}"


def _confirm_separator(var_names: list[str]) -> str | None:
    import questionary
    detected = infer_sep(var_names)
    if detected is None:
        log(f"{LC.INFO}No separator detected (camelCase or concatenated names).{LC.END}")
        ans = questionary.text(
            "Enter a separator, or press Enter for character-mode peeling:",
            default="",
        ).ask()
        return ans if ans else None
    log(f"{LC.INFO}Detected separator: {LC.VAL}'{detected}'{LC.END}")
    keep = questionary.confirm(f"Use '{detected}' as the separator?", default=True).ask()
    if keep:
        return detected
    ans = questionary.text(
        "Enter a separator, or press Enter for character-mode peeling:",
        default="",
    ).ask()
    return ans if ans else None


def _prompt_description(key: str, known: dict[str, str], prompt: str) -> str:
    import questionary
    default = known.get(key, "")
    if default:
        log(f"{LC.INFO}'{key}' previously described as: {LC.VAL}{default}{LC.END}")
    ans = questionary.text(prompt, default=default).ask()
    desc = (ans or "").strip() or default
    known[key] = desc
    return desc


def _prompt_with_default(key: str, known: dict[str, str], prompt: str, default: str) -> str:
    """Prompt with an explicit pre-composed default (no `known` lookup for default)."""
    import questionary
    if default:
        log(f"{LC.INFO}Suggested: {LC.VAL}{default}{LC.END}")
    ans = questionary.text(prompt, default=default).ask()
    desc = (ans or "").strip() or default
    known[key] = desc
    return desc


def _compose_default(family_desc: str, applied: dict[str, str]) -> str:
    """
    Compose a per-variable default description as
    'family_desc — outer_suffix_desc — … — inner_suffix_desc'.
    `applied` is expected in left-to-right reading order.
    """
    parts: list[str] = []
    if family_desc:
        parts.append(family_desc)
    for _val, desc in applied.items():
        if desc:
            parts.append(desc)
    return " — ".join(parts)


def _save_fig(fig, figs_dir, var: str) -> Path:
    d = Path(figs_dir)
    d.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in var)
    path = d / f"{safe}.png"
    fig.savefig(path, dpi=100, bbox_inches="tight")
    return path


def _serialize_stats(stats, fig_path: Path | None) -> dict:
    from .sumstats import CategoricalStats
    base = {
        "kind":     "categorical" if isinstance(stats, CategoricalStats) else "continuous",
        "count":    stats.count,
        "na_type":  stats.na_type,
        "na_count": stats.na_count,
    }
    if isinstance(stats, CategoricalStats):
        base.update({
            "value_number": list(stats.value_number),
            "value_label":  list(stats.value_label),
            "value_count":  list(stats.value_count),
            "label_map":    {str(k): v for k, v in stats.label_map.items()},
        })
    else:
        base.update({
            "mean": float(stats.mean),
            "sd":   float(stats.sd),
            "min":  float(stats.min),
            "max":  float(stats.max),
        })
    base["distribution_path"] = str(fig_path) if fig_path else None
    return base


def _applied_value(old_res: str, new_res: str, sep: str | None) -> str:
    """The trailing chunk peeled off `old_res` to produce `new_res`."""
    if not new_res:
        return old_res
    trailing = old_res[len(new_res):]
    return trailing.lstrip(sep) if sep else trailing


def _show_peel_candidate(root: str, residuals: dict, peeled: dict, sep: str | None,
                          value_counts: dict[str, int]):
    pairs = sorted(value_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    log(f"{LC.INFO}Candidate suffix values (trailing-token frequency):{LC.END}")
    for val, cnt in pairs:
        log(f"  {LC.VAL}{val}{LC.END} {LC.DBG}× {cnt}{LC.END}")
    log(f"{LC.INFO}Residuals if peeled:{LC.END}")
    joiner = sep if sep is not None else ""
    for var, new_res in peeled.items():
        applied = _applied_value(residuals[var], new_res, sep)
        if new_res:
            log(
                f"  {LC.INFO}{root}{LC.PATH}{joiner}{new_res}{LC.END} "
                f"{LC.DBG}(from {var}, peels '{applied}'){LC.END}"
            )
        else:
            log(
                f"  {LC.INFO}{root}{LC.END} "
                f"{LC.DBG}(from {var}, peels '{applied}', fully peeled){LC.END}"
            )


def _finalize_group(root, description, sep, members, layers, cores, short, bare_root,
                    applied_per_variable):
    return {
        "root":                  root,
        "description":           description,
        "sep":                   sep,
        "variables":             sorted(members),
        "layers":                layers,
        "cores":                 cores,
        "short":                 short,
        "bare_root":             bare_root,
        "applied_per_variable":  applied_per_variable,
    }


def _rebuild_known_descriptions(groups, variables, in_progress):
    known: dict[str, str] = {}
    for g in groups:
        if g.get("description"):
            known[g["root"]] = g["description"]
        for layer in g.get("layers", []):
            for val, desc in layer.get("values", {}).items():
                if desc:
                    known[val] = desc
    if in_progress:
        if in_progress.get("description"):
            known[in_progress["root"]] = in_progress["description"]
        for layer in in_progress.get("layers", []):
            for val, desc in layer.get("values", {}).items():
                if desc:
                    known[val] = desc
    for var, info in variables.items():
        desc = info.get("description") if isinstance(info, dict) else None
        if desc:
            known[var] = desc
    return known


def _snapshot(sep, groups, in_progress, variables):
    return {
        "status":            "in_progress",
        "sep":               sep,
        "groups":            copy.deepcopy(groups),
        "in_progress_group": copy.deepcopy(in_progress) if in_progress is not None else None,
        "variables":         copy.deepcopy(variables),
    }


def _peel_loop(in_progress: dict, known: dict[str, str], snap):
    """
    Run the interactive peel loop for a group. At each layer, the candidate
    trailing-token values are shown with counts and the user picks (via
    questionary.checkbox) which are *actually* suffixes. Variables whose
    trailing isn't picked stop peeling here and their residuals go to cores.

    Yields a snapshot after each accepted layer. Returns the finalized group
    dict (with applied_per_variable).
    """
    import questionary

    root                 = in_progress["root"]
    sep                  = in_progress["sep"]
    residuals            = dict(in_progress["residuals"])
    all_short            = dict(in_progress["all_short"])
    layers               = list(in_progress["layers"])
    bare_root            = in_progress["bare_root"]
    applied_per_variable = {k: dict(v) for k, v in in_progress.get("applied_per_variable", {}).items()}
    stopped_cores        = dict(in_progress.get("stopped_cores", {}))

    while residuals:
        result = peel_one(residuals, sep=sep)
        if result is None:
            log(f"{LC.INFO}No more suffixes detected.{LC.END}")
            break

        layer, peeled, short = result

        # Count how often each trailing value appears across the peeled vars.
        value_counts: dict[str, int] = {}
        for var, new_res in peeled.items():
            applied = _applied_value(residuals[var], new_res, sep)
            value_counts[applied] = value_counts.get(applied, 0) + 1

        _show_peel_candidate(root, residuals, peeled, sep, value_counts)

        # Multi-select: real suffixes get peeled, the rest become cores.
        ordered_vals = sorted(value_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        choices = [
            questionary.Choice(
                title=f"{val}  (× {cnt})",
                value=val,
                checked=(cnt > 1),
            )
            for val, cnt in ordered_vals
        ]
        selected = questionary.checkbox(
            "Select which trailing values are real suffixes — unchecked ones become cores:",
            choices=choices,
        ).ask()

        if selected is None or len(selected) == 0:
            log(f"{LC.INFO}No suffixes selected. Stopping peel for this group.{LC.END}")
            break

        selected_set = set(selected)
        # Partition peeled: keep chosen, drop unchosen into stopped_cores.
        new_peeled: dict[str, str] = {}
        for var, new_res in peeled.items():
            applied = _applied_value(residuals[var], new_res, sep)
            if applied in selected_set:
                new_peeled[var] = new_res
            else:
                stopped_cores[var] = residuals[var]

        # Descriptions only for the selected values.
        layer_values: dict[str, str] = {}
        with log.section(f"{LC.FUNC}Describe suffix values{LC.END}"):
            for val in sorted(selected_set):
                layer_values[val] = _prompt_description(
                    val, known, f"Description for suffix '{val}':"
                )

        # Applied-per-variable only for vars that actually peeled.
        for var, new_res in new_peeled.items():
            applied = _applied_value(residuals[var], new_res, sep)
            applied_per_variable.setdefault(var, {})[applied] = layer_values.get(applied, "")

        layers.append({"values": layer_values})
        all_short.update(short)
        residuals = new_peeled

        in_progress = {
            **in_progress,
            "layers":               list(layers),
            "residuals":            dict(residuals),
            "all_short":            dict(all_short),
            "applied_per_variable": {k: dict(v) for k, v in applied_per_variable.items()},
            "stopped_cores":        dict(stopped_cores),
        }
        yield snap(in_progress)

    cores = dict(sorted({**residuals, **all_short, **stopped_cores}.items()))
    return _finalize_group(
        root, in_progress["description"], sep, in_progress["variables"],
        layers, cores, sorted(all_short.keys()), bare_root, applied_per_variable,
    )


def _process_group(root: str, members: list[str], sep: str | None,
                   known: dict[str, str], snap):
    """
    Interactive flow for a fresh group (accept/reject → description → has-suffixes).
    Yields snapshots when mid-peel state changes. Returns the finalized group dict,
    or None if the user rejected the group.
    """
    import questionary

    with log.section(f"{LC.FUNC}Group: {LC.INFO}{root}{LC.END}"):
        log(f"{LC.INFO}Members ({len(members)}):{LC.END}")
        for m in members:
            log(f"  {_format_member(m, root)}")

        if not questionary.confirm(
            f"Accept '{root}' as a variable group?", default=True
        ).ask():
            log(f"{LC.INFO}Rejected. Members returned to ungrouped pool.{LC.END}")
            return None

        root_desc = _prompt_description(root, known, f"Describe the '{root}' family:")

        has_suffixes = questionary.confirm(
            "Are there suffixes in this group?", default=True
        ).ask()

        if not has_suffixes:
            stripped  = {v: _strip_root(v, root, sep) for v in members}
            bare_root = any(r == "" for r in stripped.values())
            cores     = {v: r for v, r in stripped.items() if r}
            return _finalize_group(root, root_desc, sep, members, [], cores, [], bare_root, {})

        bare_root = False
        residuals: dict[str, str] = {}
        for v in members:
            stripped = _strip_root(v, root, sep)
            if not stripped:
                bare_root = True
            else:
                residuals[v] = stripped

        in_progress = {
            "root":                 root,
            "description":          root_desc,
            "sep":                  sep,
            "variables":            sorted(members),
            "layers":               [],
            "residuals":            dict(residuals),
            "all_short":            {},
            "bare_root":            bare_root,
            "applied_per_variable": {},
            "stopped_cores":        {},
        }
        yield snap(in_progress)

        return (yield from _peel_loop(in_progress, known, snap))


def _resume_group(in_progress: dict, known: dict[str, str], snap):
    """Continue an in-progress group's peel loop from a saved checkpoint."""
    with log.section(f"{LC.FUNC}Resuming group: {LC.INFO}{in_progress['root']}{LC.END}"):
        log(
            f"{LC.INFO}Restored {LC.VAL}{len(in_progress['layers'])}{LC.INFO} "
            f"layer(s); {LC.VAL}{len(in_progress['residuals'])}{LC.INFO} residual(s) pending.{LC.END}"
        )
        return (yield from _peel_loop(in_progress, known, snap))


def _process_variable(var: str, df: pd.DataFrame, family_info: dict | None,
                      known: dict[str, str], figs_dir, variables: dict, snap):
    """Compute stats, save figure, prompt per-variable description. Initializes
    suffix_variants to an empty dict on the entry."""
    from .sumstats import make_var_stats

    with log.section(f"{LC.FUNC}Variable: {LC.INFO}{var}{LC.END}"):
        stats = make_var_stats(df[[var]])

        fig_path = None
        if figs_dir is not None and getattr(stats, "distribution", None) is not None:
            fig_path = _save_fig(stats.distribution, figs_dir, var)
            log(f"{LC.DBG}Saved figure: {LC.PATH}{fig_path}{LC.END}")

        if family_info is not None:
            default = _compose_default(
                family_info.get("family_description", ""),
                family_info.get("applied_suffixes", {}),
            )
        else:
            default = known.get(var, "")

        desc = _prompt_with_default(var, known, f"Description for '{var}':", default)

        variables[var] = {
            "description":     desc,
            "family":          family_info,
            "suffix_variants": {},
            "stats":           _serialize_stats(stats, fig_path),
        }
        yield snap(None)


def _process_variant(variant: str, variant_key: str, core: str, df: pd.DataFrame,
                     figs_dir, variables: dict, snap):
    """Compute stats for a suffix variant of `core`. No description prompt —
    the core owns the description. Stats are stored under
    variables[core]['suffix_variants'][variant_key]."""
    from .sumstats import make_var_stats

    with log.section(f"{LC.FUNC}Variant: {LC.INFO}{variant}{LC.END} {LC.DBG}(suffix: {variant_key}){LC.END}"):
        stats = make_var_stats(df[[variant]])
        fig_path = None
        if figs_dir is not None and getattr(stats, "distribution", None) is not None:
            fig_path = _save_fig(stats.distribution, figs_dir, variant)
            log(f"{LC.DBG}Saved figure: {LC.PATH}{fig_path}{LC.END}")
        variables[core].setdefault("suffix_variants", {})[variant_key] = {
            "name":  variant,
            "stats": _serialize_stats(stats, fig_path),
        }
        yield snap(None)


def _build_variant_key(applied: dict[str, str], sep: str | None) -> str:
    """Concatenate applied suffix values in left-to-right reading order.
    `applied` insertion order is peel order (rightmost-first); we reverse it."""
    keys_ltr = list(reversed(list(applied.keys())))
    joiner = sep if sep is not None else "_"
    return joiner.join(keys_ltr)


def _process_group_variables(group: dict, df: pd.DataFrame, known: dict[str, str],
                             figs_dir, variables: dict, snap):
    """
    Per-variable pass for a finalized group. Groups members by their final
    residual; within each residual bucket, the member with no applied suffixes
    is the core (others are variants folded under it). If no zero-suffix member
    exists in a bucket, each member is processed as its own standalone.
    """
    root        = group["root"]
    family_desc = group.get("description", "")
    applied_map = group.get("applied_per_variable", {})
    members     = group["variables"]
    sep         = group.get("sep")
    cores_dict  = group.get("cores", {})

    # Group-wide available_suffixes: union of every var's applied_per_variable.
    available_suffixes: dict[str, str] = {}
    for var in members:
        for k, v in applied_map.get(var, {}).items():
            if v:
                available_suffixes.setdefault(k, v)

    # Bucket members by final residual. A member missing from cores_dict has
    # an empty residual (bare root or fully peeled).
    buckets: dict[str, list[str]] = {}
    for m in members:
        buckets.setdefault(cores_dict.get(m, ""), []).append(m)

    with log.section(f"{LC.FUNC}Describe variables in '{root}'{LC.END}"):
        handled: set[str] = set()
        for m in sorted(members):
            if m in handled:
                continue
            bucket = buckets.get(cores_dict.get(m, ""), [m])

            # Core = sorted-first member with no applied suffixes; else no core.
            core_candidates = sorted(v for v in bucket if not applied_map.get(v))
            if core_candidates:
                core     = core_candidates[0]
                variants = sorted(v for v in bucket if v != core)
            else:
                # No pure core in this bucket — treat `m` alone as a standalone.
                core     = m
                variants = []

            if core not in variables:
                core_applied_raw = applied_map.get(core, {})
                core_applied_ltr = {k: v for k, v in reversed(list(core_applied_raw.items()))}
                family_info = {
                    "root":               root,
                    "family_description": family_desc,
                    "available_suffixes": dict(available_suffixes),
                    "applied_suffixes":   core_applied_ltr,
                }
                yield from _process_variable(core, df, family_info, known, figs_dir, variables, snap)

            variables[core].setdefault("suffix_variants", {})

            for variant in variants:
                vkey = _build_variant_key(applied_map.get(variant, {}), sep)
                if vkey in variables[core]["suffix_variants"]:
                    continue
                yield from _process_variant(variant, vkey, core, df, figs_dir, variables, snap)

            handled.add(core)
            handled.update(variants)


def get_variable_groups(
    df:                 pd.DataFrame,
    resume_state:       dict | None = None,
    known_descriptions: dict[str, str] | None = None,
    sep:                str | None = None,
    figs_dir:           str | Path | None = None,
) -> Iterator[dict]:
    """
    Interactive codebook session: separator confirmation → prefix-group detection
    → suffix peeling (layer-by-layer with descriptions) → per-variable summary
    stats + description for every variable (grouped and ungrouped).

    Yields a state dict after each meaningful step so the caller can checkpoint
    to disk. The final yielded state is a pivoted variables-indexed JSON. If
    `resume_state` is provided (from a saved checkpoint), the generator picks
    up where the previous session stopped — including mid-peel or partway
    through a group's per-variable pass.

    Parameters:
    df                 - the input DataFrame; var_names are derived from columns.
    resume_state       - a previously yielded state dict loaded from JSON.
    known_descriptions - optional seed of {token: description}; merged with any
                         descriptions recovered from resume_state.
    sep                - optional pre-confirmed separator; overridden by
                         resume_state if it has a sep set.
    figs_dir           - directory to write distribution figures (one PNG per
                         variable). If None, figures are not persisted and the
                         JSON's distribution_path will be null.

    Yields state dicts. Intermediate yields contain working group state plus
    the growing variables dict. The final yield has status='complete' and a
    variables-indexed shape.
    """
    var_names = list(df.columns)

    if resume_state and resume_state.get("status") == "complete":
        # Session already finished — nothing to do beyond re-emitting.
        yield dict(resume_state)
        return

    accepted:    list[dict]  = list(resume_state.get("groups", []))            if resume_state else []
    variables:   dict[str, dict] = dict(resume_state.get("variables", {}))      if resume_state else {}
    in_progress: dict | None = resume_state.get("in_progress_group")            if resume_state else None
    if resume_state and resume_state.get("sep") is not None:
        sep = resume_state["sep"]

    known: dict[str, str] = _rebuild_known_descriptions(accepted, variables, in_progress)
    if known_descriptions:
        known.update(known_descriptions)

    def snap(ip):
        return _snapshot(sep, accepted, ip, variables)

    try:
        import questionary
    except ImportError:
        log(f"{LC.WARN}Install codebook extras: pip install sparklib[codebook]{LC.END}")
        yield {"status": "complete", "variables": variables}
        return

    with log.section(f"{LC.FUNC}Variable Group Detection{LC.END}"):
        # Phase 1 — separator (skipped on resume if already set)
        if sep is None:
            sep = _confirm_separator(var_names)
        log(f"{LC.DBG}Using separator: {LC.VAL}{sep!r}{LC.END}")
        yield snap(in_progress)

        # Phase 2 — detect
        groups_dict = find_prefix_groups(var_names, sep=sep)
        done_roots = {g["root"] for g in accepted}
        log(
            f"{LC.INFO}Detected {LC.VAL}{len(groups_dict)}{LC.INFO} candidate group(s); "
            f"{LC.VAL}{len(ungrouped(var_names, groups_dict))}{LC.INFO} variable(s) ungrouped.{LC.END}"
        )

        leftover_from_rejects: list[str] = []

        # Resume the in-progress group first (if any)
        if in_progress is not None:
            completed = yield from _resume_group(in_progress, known, snap)
            accepted.append(completed)
            done_roots.add(completed["root"])
            in_progress = None
            yield snap(None)
            yield from _process_group_variables(completed, df, known, figs_dir, variables, snap)

        # Process remaining candidate groups
        for root, members in groups_dict.items():
            if root in done_roots:
                # Already-accepted from a prior session — complete any unfinished
                # per-variable pass for its members.
                group = next(g for g in accepted if g["root"] == root)
                yield from _process_group_variables(group, df, known, figs_dir, variables, snap)
                continue
            result = yield from _process_group(root, members, sep, known, snap)
            if result is None:
                leftover_from_rejects.extend(members)
            else:
                accepted.append(result)
                yield snap(None)
                yield from _process_group_variables(result, df, known, figs_dir, variables, snap)

        # Phase 5 — leftover variables (family=None)
        base_leftover = ungrouped(var_names, groups_dict)
        full_leftover = list(dict.fromkeys(base_leftover + leftover_from_rejects))
        todo = [v for v in full_leftover if v not in variables]
        if todo:
            with log.section(f"{LC.FUNC}Ungrouped Variables{LC.END}"):
                log(f"{LC.INFO}{len(todo)} ungrouped variable(s) to describe.{LC.END}")
                for v in todo:
                    yield from _process_variable(v, df, None, known, figs_dir, variables, snap)

    # Final pivot — variables-indexed shape, status complete.
    yield {"status": "complete", "variables": copy.deepcopy(variables)}
