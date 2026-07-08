import math
import numpy as np
import pandas as pd


def make_json_safe(obj):
    """
    Recursively convert pandas/numpy objects into
    JSON serializable Python objects.

    Handles:

    ✔ NaN
    ✔ NaT
    ✔ Infinity
    ✔ numpy ints
    ✔ numpy floats
    ✔ Timestamp
    ✔ DataFrame
    ✔ Series
    ✔ dict
    ✔ list
    """

    # ------------------------------
    # None
    # ------------------------------

    if obj is None:
        return None

    # ------------------------------
    # Pandas NA
    # ------------------------------

    if obj is pd.NA:
        return None

    # ------------------------------
    # NaN
    # ------------------------------

    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass

    # ------------------------------
    # Timestamp
    # ------------------------------

    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()

    # ------------------------------
    # numpy integer
    # ------------------------------

    if isinstance(obj, np.integer):
        return int(obj)

    # ------------------------------
    # numpy float
    # ------------------------------

    if isinstance(obj, np.floating):

        value = float(obj)

        if math.isnan(value):
            return None

        if math.isinf(value):
            return None

        return value

    # ------------------------------
    # Python float
    # ------------------------------

    if isinstance(obj, float):

        if math.isnan(obj):
            return None

        if math.isinf(obj):
            return None

        return obj

    # ------------------------------
    # numpy bool
    # ------------------------------

    if isinstance(obj, np.bool_):
        return bool(obj)

    # ------------------------------
    # DataFrame
    # ------------------------------

    if isinstance(obj, pd.DataFrame):

        return make_json_safe(
            obj.to_dict(orient="records")
        )

    # ------------------------------
    # Series
    # ------------------------------

    if isinstance(obj, pd.Series):

        return make_json_safe(
            obj.tolist()
        )

    # ------------------------------
    # Dict
    # ------------------------------

    if isinstance(obj, dict):

        return {
            str(k): make_json_safe(v)
            for k, v in obj.items()
        }

    # ------------------------------
    # List
    # ------------------------------

    if isinstance(obj, list):

        return [
            make_json_safe(x)
            for x in obj
        ]

    # ------------------------------
    # Tuple
    # ------------------------------

    if isinstance(obj, tuple):

        return tuple(
            make_json_safe(x)
            for x in obj
        )

    return obj