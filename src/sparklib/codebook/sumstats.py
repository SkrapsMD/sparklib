from dataclasses import dataclass
from typing import Iterable, Optional, Union
import matplotlib.figure


@dataclass
class VarSumStats:
    count:    int
    na_type:  str
    na_count: int

@dataclass
class CategoricalStats(VarSumStats):
    value_number: list[int]
    value_label:  list[str]
    value_count:  list[int]
    label_map:    dict
    distribution: Optional[matplotlib.figure.Figure] = None

@dataclass
class ContinuousStats(VarSumStats):
    mean:         float
    sd:           float
    min:          float
    max:          float
    distribution: Optional[matplotlib.figure.Figure] = None
#────────────────────────────────────────────────────────────────
# Construct the counts
#────────────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .query import get_value_labels

def make_var_stats(
    df: pd.DataFrame,
    force_categorical:  Optional[bool]     = None,
    na_sentinels:       Optional[Iterable] = None,
    cat_threshold:      float              = 0.05
) -> Union[CategoricalStats, ContinuousStats]:
    """
    Build summary stats from a single-column DataFrame.

    force_categorical:  override type inference,
    na_sentinels:       values to treat as NA (e.g. [-99, "", "N/A"])
    cat_threshold:      if nunique/count < this, infer categorical. Only applies to Numeric Columns when force is None.
    """
    assert df.shape[1] == 1, f"Expected 1 column, got {df.shape[1]}"
    s = df.iloc[:, 0].copy()

    na_type = "native"
    if na_sentinels:
        sentinel_mask           = s.isin(list(na_sentinels))
        if sentinel_mask.any():
            na_type             = str(na_sentinels)
            s[sentinel_mask]    = np.nan
    na_count    = int(s.isna().sum())
    s_clean     = s.dropna()
    count       = len(s_clean)

    if force_categorical is not None:
        is_cat = force_categorical
    elif s_clean.dtype == "category" or s_clean.dtype == object or s_clean.dtype == bool:
        is_cat = True
    elif pd.api.types.is_numeric_dtype(s_clean):
        is_cat = (s_clean.nunique() / max(count, 1)) < cat_threshold
    else:
        is_cat = True

    if is_cat:
        vc = s_clean.value_counts(sort = False)


        label_map = get_value_labels(vc)

        bar_labels = [label_map[v] for v in vc.index]
        fig, ax = plt.subplots(figsize=(4, 2.5))
        ax.barh(bar_labels, vc.values)
        ax.set_title(df.columns[0])
        ax.invert_yaxis()
        fig.tight_layout()
        plt.close(fig)

        return CategoricalStats(
            count       = count,
            na_type     = na_type,
            na_count    = na_count,
            value_number= list(range(len(vc))),
            value_label = [label_map[v] for v in vc.index],
            value_count = vc.values.tolist(),
            label_map   = label_map,
            distribution= fig,
        )

    else:
        s_num = pd.to_numeric(s_clean)
        fig, ax = plt.subplots(figsize=(4, 2.5))
        ax.hist(s_num, bins="auto", edgecolor="white")
        ax.set_title(df.columns[0])
        fig.tight_layout()
        plt.close(fig)

        return ContinuousStats(
            count       = count,
            na_type     = na_type,
            na_count    = na_count,
            mean        = float(s_num.mean()),
            sd          = float(s_num.std()),
            min         = float(s_num.min()),
            max         = float(s_num.max()),
            distribution= fig

        )
