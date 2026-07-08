import math
import re

import numpy as np
import pandas as pd

from pandas.api.types import (
    is_numeric_dtype,
    is_datetime64_any_dtype,
)

from utils.json_utils import make_json_safe


# ============================================================
# CONSTANTS
# ============================================================

NULL_VALUES = {
    "",
    " ",
    "na",
    "n/a",
    "nan",
    "null",
    "none",
    "-",
    "--",
    "---",
}


CURRENCY_PATTERN = r"[$₹€£,]"


# ============================================================
# SAFE NUMBER
# ============================================================

def safe_number(value):
    """
    Convert any numeric value into a JSON-safe float.
    """

    if value is None:
        return None

    try:

        if pd.isna(value):
            return None

    except Exception:
        pass

    try:

        value = float(value)

        if math.isnan(value):
            return None

        if math.isinf(value):
            return None

        return value

    except Exception:
        return None


# ============================================================
# CLEAN STRING SERIES
# ============================================================

def clean_string_series(series: pd.Series) -> pd.Series:
    """
    Removes extra spaces and converts common null strings to None.
    """

    series = series.astype(str)

    series = series.str.strip()

    series = series.replace(
        list(NULL_VALUES),
        None,
    )

    return series


# ============================================================
# TRY NUMERIC CONVERSION
# ============================================================

def try_numeric_conversion(series: pd.Series):
    """
    Automatically converts

    ₹1,200
    $300
    45%
    1,234

    into numeric values.
    """

    if is_numeric_dtype(series):
        return series

    cleaned = clean_string_series(series)

    cleaned = cleaned.str.replace(
        CURRENCY_PATTERN,
        "",
        regex=True,
    )

    cleaned = cleaned.str.replace(
        "%",
        "",
        regex=False,
    )

    converted = pd.to_numeric(
        cleaned,
        errors="coerce",
    )

    success = converted.notna().mean()

    if success >= 0.80:
        return converted

    return series


# ============================================================
# TRY DATE CONVERSION
# ============================================================

def convert_special_period(value):
    """
    Converts

    2025.03

    into

    2025-03-01
    """

    try:

        value = str(value)

        if not re.match(r"^\d{4}\.\d{2}$", value):
            return pd.NaT

        year, month = value.split(".")

        return pd.Timestamp(
            year=int(year),
            month=int(month),
            day=1,
        )

    except Exception:
        return pd.NaT


def detect_date_column(df):
    """
    Automatically detects the best date column.

    Supports

    yyyy-mm-dd

    dd/mm/yyyy

    Month names

    Quarter style

    2024.03
    """

    for column in df.columns:

        series = df[column]

        # Already datetime
        if is_datetime64_any_dtype(series):
            return column

        # Quarter style
        if is_numeric_dtype(series):

            values = series.dropna().astype(str)

            if len(values):

                if (
                    values.str.match(
                        r"^\d{4}\.\d{2}$"
                    ).mean()
                    >= 0.80
                ):

                    parsed = series.apply(
                        convert_special_period
                    )

                    if parsed.notna().mean() >= 0.80:

                        df[column] = parsed

                        return column

            continue

        parsed = pd.to_datetime(
            series,
            errors="coerce",
        )

        valid = series.notna().sum()

        if valid == 0:
            continue

        success = parsed.notna().sum() / valid

        if success >= 0.80:

            df[column] = parsed

            return column

    return None


# ============================================================
# DETECT COLUMN TYPES
# ============================================================

def detect_columns(df):
    """
    Returns

    numeric_columns

    categorical_columns

    column metadata
    """

    numeric_columns = []

    categorical_columns = []

    columns = []

    for column in df.columns:

        if is_numeric_dtype(df[column]):

            column_type = "numeric"

            numeric_columns.append(column)

        elif is_datetime64_any_dtype(df[column]):

            column_type = "datetime"

        else:

            column_type = "categorical"

            categorical_columns.append(column)

        columns.append(
            {
                "name": column,
                "type": column_type,
            }
        )

    return (
        numeric_columns,
        categorical_columns,
        columns,
    )
    # ============================================================
# BUILD NUMERIC STATISTICS
# ============================================================

def build_statistics(df, numeric_columns):
    """
    Build descriptive statistics for every numeric column.
    """

    stats = {}

    for column in numeric_columns:

        series = df[column]

        stats[column] = {
            "count": int(series.count()),
            "null_count": int(series.isna().sum()),
            "mean": safe_number(series.mean()),
            "median": safe_number(series.median()),
            "sum": safe_number(series.sum()),
            "min": safe_number(series.min()),
            "max": safe_number(series.max()),
            "std": safe_number(series.std()),
            "variance": safe_number(series.var()),
        }

    return stats


# ============================================================
# BUILD SAMPLE ROWS
# ============================================================

def build_sample_rows(df):
    """
    Return first five rows in JSON-safe format.
    """

    sample = df.head(5).copy()

    for column in sample.columns:

        if is_datetime64_any_dtype(sample[column]):

            sample[column] = sample[column].dt.strftime(
                "%Y-%m-%d"
            )

    sample = make_json_safe(sample)

    return sample


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicates(df):

    before = len(df)

    df = df.drop_duplicates()

    after = len(df)

    return df, before - after


# ============================================================
# CLEAN DATAFRAME
# ============================================================

def clean_dataframe(df):
    """
    Perform generic cleaning on almost any dataset.
    """

    df = df.copy()

    # Remove empty rows
    df.dropna(
        axis=0,
        how="all",
        inplace=True,
    )

    # Remove empty columns
    df.dropna(
        axis=1,
        how="all",
        inplace=True,
    )

    # Clean column names
    df.columns = [
        str(col).strip()
        for col in df.columns
    ]

    # Clean every object column
    for column in df.columns:

        if df[column].dtype == object:

            df[column] = clean_string_series(
                df[column]
            )

    # Try converting numerics
    for column in df.columns:

        df[column] = try_numeric_conversion(
            df[column]
        )

    # Remove duplicates
    df, duplicate_count = remove_duplicates(df)

    return df, duplicate_count
# ============================================================
# MAIN FUNCTION
# ============================================================

def clean_and_profile(df: pd.DataFrame):
    """
    Clean the dataframe and generate a profile.

    Returns
    -------
    profile : dict
    cleaned_dataframe : pd.DataFrame
    """

    # -----------------------------
    # Clean dataframe
    # -----------------------------

    df, duplicate_count = clean_dataframe(df)

    # -----------------------------
    # Detect date column
    # -----------------------------

    date_column = detect_date_column(df)

    # -----------------------------
    # Detect column types
    # -----------------------------

    (
        numeric_columns,
        categorical_columns,
        columns,
    ) = detect_columns(df)

    # -----------------------------
    # Build statistics
    # -----------------------------

    stats = build_statistics(
        df,
        numeric_columns,
    )

    # -----------------------------
    # Sample rows
    # -----------------------------

    sample_rows = build_sample_rows(df)

    # -----------------------------
    # Missing values
    # -----------------------------

    missing_values = {}

    for column in df.columns:

        missing_values[column] = int(
            df[column].isna().sum()
        )

    # -----------------------------
    # Data types
    # -----------------------------

    dtypes = {}

    for column in df.columns:

        dtypes[column] = str(
            df[column].dtype
        )

    # -----------------------------
    # Dataset overview
    # -----------------------------

    profile = {

        "row_count": int(len(df)),

        "column_count": int(len(df.columns)),

        "duplicate_rows_removed": duplicate_count,

        "columns": columns,

        "dtypes": dtypes,

        "date_column": date_column,

        "numeric_columns": numeric_columns,

        "categorical_columns": categorical_columns,

        "missing_values": missing_values,

        "sample_rows": sample_rows,

        "stats": stats,

    }

    # -----------------------------
    # Make profile JSON-safe
    # -----------------------------

    profile = make_json_safe(profile)

    # -----------------------------
    # Return
    # -----------------------------

    return profile, df