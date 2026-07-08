import math
import pandas as pd

from utils.json_utils import make_json_safe


# ==========================================================
# SAFE NUMBER
# ==========================================================

def safe_number(value):

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


# ==========================================================
# CHOOSE BEST NUMERIC COLUMN
# ==========================================================

def choose_numeric_column(df, numeric_columns):
    """
    Choose the most useful numeric column.

    Priority

    • most non-null values

    • highest variance

    """

    if not numeric_columns:
        return None

    best_column = None
    best_score = -1

    for column in numeric_columns:

        series = df[column]

        non_null = series.notna().sum()

        variance = series.var(skipna=True)

        if pd.isna(variance):
            variance = 0

        score = non_null * (variance + 1)

        if score > best_score:

            best_score = score
            best_column = column

    return best_column


# ==========================================================
# CHOOSE BEST CATEGORY
# ==========================================================

def choose_category_column(df, categorical_columns):
    """
    Ignore ID columns.

    Pick a column with
    2-50 unique values.
    """

    if not categorical_columns:
        return None

    candidates = []

    for column in categorical_columns:

        unique = df[column].nunique(dropna=True)

        if unique <= 1:
            continue

        if unique > 50:
            continue

        name = column.lower()

        if "id" in name:
            continue

        candidates.append(
            (
                unique,
                column,
            )
        )

    if not candidates:
        return None

    candidates.sort()

    return candidates[0][1]


# ==========================================================
# BUILD TREND
# ==========================================================

def build_trend(df, date_column, value_column):

    if date_column is None:
        return []

    if value_column is None:
        return []

    temp = df.copy()

    temp[date_column] = pd.to_datetime(
        temp[date_column],
        errors="coerce",
    )

    temp = temp.dropna(
        subset=[
            date_column,
            value_column,
        ]
    )

    if temp.empty:
        return []

    monthly = (

        temp

        .set_index(date_column)[value_column]

        .resample("MS")

        .sum()

    )

    trend = []

    for date, value in monthly.items():

        trend.append(

            {

                "period": date.strftime("%Y-%m"),

                "value": safe_number(value),

            }

        )

    return trend
# ==========================================================
# BUILD GROWTH
# ==========================================================

def build_growth(trend):

    if len(trend) < 2:
        return []

    growth = []

    previous = None

    for item in trend:

        current = item["value"]

        if previous is None or previous == 0 or current is None:

            growth.append(
                {
                    "period": item["period"],
                    "growth_pct": None,
                }
            )

        else:

            pct = ((current - previous) / previous) * 100

            growth.append(
                {
                    "period": item["period"],
                    "growth_pct": safe_number(pct),
                }
            )

        previous = current

    return growth


# ==========================================================
# BUILD ANOMALIES
# ==========================================================

def build_anomalies(trend):

    if len(trend) < 4:
        return []

    values = pd.Series(
        [
            t["value"]
            for t in trend
            if t["value"] is not None
        ]
    )

    if len(values) < 4:
        return []

    q1 = values.quantile(.25)

    q3 = values.quantile(.75)

    iqr = q3 - q1

    lower = q1 - 1.5 * iqr

    upper = q3 + 1.5 * iqr

    anomalies = []

    for item in trend:

        value = item["value"]

        if value is None:

            anomalies.append(
                {
                    "period": item["period"],
                    "value": None,
                    "is_anomaly": False,
                }
            )

            continue

        anomalies.append(
            {
                "period": item["period"],
                "value": value,
                "is_anomaly": bool(
                    value < lower or value > upper
                ),
            }
        )

    return anomalies


# ==========================================================
# BUILD TOP/BOTTOM
# ==========================================================

def build_top_bottom(df, category_column, value_column):

    if category_column is None:
        return {
            "top": [],
            "bottom": [],
        }

    if value_column is None:
        return {
            "top": [],
            "bottom": [],
        }

    grouped = (

        df

        .groupby(category_column)[value_column]

        .sum()

        .sort_values(ascending=False)

    )

    top = grouped.head(5)

    bottom = grouped.tail(5).sort_values()

    return {

        "top": [

            {

                "category": str(k),

                "value": safe_number(v),

            }

            for k, v in top.items()

        ],

        "bottom": [

            {

                "category": str(k),

                "value": safe_number(v),

            }

            for k, v in bottom.items()

        ],

    }


# ==========================================================
# KPI SUMMARY
# ==========================================================

def build_summary(df):

    return {

        "rows": int(len(df)),

        "columns": int(len(df.columns)),

        "missing_values": int(df.isna().sum().sum()),

        "duplicate_rows": int(df.duplicated().sum()),

    }
    # ==========================================================
# GENERATE INSIGHTS
# ==========================================================

def generate_insights(
    trend,
    growth,
    top_bottom,
    value_column,
    category_column,
):

    insights = []

    if trend:

        latest = trend[-1]

        insights.append(
            f"The latest recorded value for '{value_column}' is {latest['value']}."
        )

    if growth:

        latest_growth = growth[-1]["growth_pct"]

        if latest_growth is not None:

            if latest_growth > 0:

                insights.append(
                    f"{value_column} increased by {latest_growth:.2f}% during the latest period."
                )

            elif latest_growth < 0:

                insights.append(
                    f"{value_column} decreased by {abs(latest_growth):.2f}% during the latest period."
                )

    if top_bottom["top"]:

        top = top_bottom["top"][0]

        insights.append(
            f"The best-performing {category_column} is '{top['category']}' with a value of {top['value']}."
        )

    if top_bottom["bottom"]:

        bottom = top_bottom["bottom"][0]

        insights.append(
            f"The lowest-performing {category_column} is '{bottom['category']}' with a value of {bottom['value']}."
        )

    return insights


# ==========================================================
# MAIN ANALYSIS FUNCTION
# ==========================================================

def run_analysis(df, profile):

    date_column = profile.get("date_column")

    numeric_columns = profile.get(
        "numeric_columns",
        [],
    )

    categorical_columns = profile.get(
        "categorical_columns",
        [],
    )

    value_column = choose_numeric_column(
        df,
        numeric_columns,
    )

    category_column = choose_category_column(
        df,
        categorical_columns,
    )

    trend = build_trend(
        df,
        date_column,
        value_column,
    )

    growth = build_growth(
        trend,
    )

    anomalies = build_anomalies(
        trend,
    )

    top_bottom = build_top_bottom(
        df,
        category_column,
        value_column,
    )

    summary = build_summary(
        df,
    )

    insights = generate_insights(
        trend,
        growth,
        top_bottom,
        value_column,
        category_column,
    )

    analysis = {

        "summary": summary,

        "analysis_info": {

            "date_column": date_column,

            "value_column": value_column,

            "category_column": category_column,

        },

        "trends": trend,

        "growth": growth,

        "anomalies": anomalies,

        "top_bottom": top_bottom,

        "insights": insights,

    }

    return make_json_safe(
        analysis
    )