import json
import os

import google.generativeai as genai
import pandas as pd

from dotenv import load_dotenv

from utils.json_helpers import safe_parse_json
from utils.json_utils import make_json_safe

# ----------------------------------------------------
# Load Environment
# ----------------------------------------------------

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)

# ----------------------------------------------------
# SYSTEM PROMPT
# ----------------------------------------------------

SYSTEM_PROMPT = """
You are an expert Senior Data Scientist, Business Intelligence Analyst,
Data Analyst and AI Consultant.

Your job is to analyze datasets like a professional analyst.

You are given:

1. Dataset Profile
2. Dataset Statistics
3. Precomputed Analysis
4. Dataset Sample
5. User Question

You must answer ANY question related to the dataset.

Never say that you cannot answer unless the information truly does not exist.

Use logical reasoning.

Use statistical reasoning.

Infer patterns whenever possible.

Use the dataset sample whenever needed.

Use the precomputed analysis only as additional context.

Do NOT depend entirely on the precomputed analysis.

--------------------------------------------------

You can answer questions about:

• Summary

• Trends

• Highest values

• Lowest values

• Average

• Mean

• Median

• Mode

• Standard deviation

• Growth

• Correlation

• Outliers

• Missing values

• Duplicate rows

• Categories

• Distribution

• Forecasts

• Comparisons

• Business insights

• Machine Learning recommendations

• Data cleaning suggestions

• Statistical observations

• General observations

• Visualizations

--------------------------------------------------

If the user requests a graph OR if a graph would make the answer easier to understand,
generate chart data.

Supported chart types

bar

line

pie

Never invent fake numbers.

Use only numbers that exist in the dataset.

--------------------------------------------------

Return ONLY valid JSON.

Example:

{
    "answer":"...",

    "charts":[
        {
            "type":"bar",

            "title":"Sales by Category",

            "xKey":"Category",

            "yKey":"Sales",

            "data":[
                {
                    "Category":"A",
                    "Sales":100
                },
                {
                    "Category":"B",
                    "Sales":90
                }
            ]
        }
    ],

    "recommendation":"...",

    "follow_up_questions":[
        "...",
        "...",
        "..."
    ]
}

If no chart is required

"charts": []

Always return an array for charts.

Never return

"chart"

Always return

"charts"

Never return Markdown.

Never write ```json.

Never explain the JSON.

Only return the JSON object.
"""

# ----------------------------------------------------
# Helper Functions
# ----------------------------------------------------

def dataframe_statistics(df: pd.DataFrame):
    """
    Generate useful statistics for the AI.
    """

    try:

        stats = (
            df.describe(include="all")
            .fillna("")
            .to_dict()
        )

    except Exception:

        stats = {}

    return make_json_safe(stats)


def dataframe_sample(df: pd.DataFrame, rows=150):
    """
    Create a representative sample of the dataset.
    """

    if len(df) <= rows:
        sample = df.copy()

    else:
        sample = df.sample(
            rows,
            random_state=42
        )

    return make_json_safe(
        sample.to_dict(
            orient="records"
        )
    )
    # ----------------------------------------------------
# Prompt Builder
# ----------------------------------------------------

def build_prompt(
    question,
    profile,
    analysis,
    statistics,
    dataset_sample,
):
    """
    Builds a rich prompt that gives Gemini
    enough context to answer naturally.
    """

    prompt = f"""
==========================
USER QUESTION
==========================

{question}

==========================
DATASET PROFILE
==========================

{json.dumps(
    make_json_safe(profile),
    indent=2
)}

==========================
DATASET STATISTICS
==========================

{json.dumps(
    make_json_safe(statistics),
    indent=2
)}

==========================
PRECOMPUTED ANALYSIS
==========================

{json.dumps(
    make_json_safe(analysis),
    indent=2
)}

==========================
DATASET SAMPLE
==========================

{json.dumps(
    make_json_safe(dataset_sample),
    indent=2
)}

==========================
YOUR TASK
==========================

Answer the user's question using ALL available information.

Guidelines:

1. Use the dataset sample whenever possible.

2. Use the statistics to calculate values.

3. Use the precomputed analysis only as supporting context.

4. If the question requires reasoning,
reason like a professional data analyst.

5. If the user asks for:

- compare
- trend
- distribution
- highest
- lowest
- visualization
- graph
- chart
- analysis

generate an appropriate chart.

6. If a chart would make the answer easier,
generate one automatically.

7. Never invent values.

8. Never mention that you are an AI.

9. Return ONLY valid JSON.

10. Keep the answer concise but informative.

11. Recommendation should be practical.

12. Follow-up questions should help the user explore the data further.
"""

    return prompt


# ----------------------------------------------------
# AI Generation
# ----------------------------------------------------

def generate_ai_response(prompt):
    """
    Sends the prompt to Gemini and
    returns the raw text response.
    """

    response = model.generate_content(
        SYSTEM_PROMPT + "\n\n" + prompt
    )

    if not hasattr(response, "text"):
        raise Exception("Gemini returned an empty response.")

    return response.text.strip()


# ----------------------------------------------------
# JSON Parser
# ----------------------------------------------------

def parse_ai_response(text):
    """
    Parses Gemini output safely.
    Ensures all expected fields exist.
    """

    result = safe_parse_json(text)

    if not isinstance(result, dict):
        result = {
            "answer": str(result)
        }

    result.setdefault("answer", "")
    result.setdefault("charts", [])
    result.setdefault("recommendation", "")
    result.setdefault("follow_up_questions", [])

    if result["charts"] is None:
        result["charts"] = []

    return make_json_safe(result)
# ----------------------------------------------------
# Main AI Function
# ----------------------------------------------------

def ask_ai(
    question,
    profile,
    analysis,
    df,
):
    """
    Main function called from chat.py

    Parameters
    ----------
    question : str

    profile : dict

    analysis : dict

    df : pandas.DataFrame

    Returns
    -------
    dict
    """

    try:

        # ------------------------------
        # Clean DataFrame
        # ------------------------------

        df = df.copy()

        # ------------------------------
        # Generate Statistics
        # ------------------------------

        statistics = dataframe_statistics(df)

        # ------------------------------
        # Representative Sample
        # ------------------------------

        dataset_sample = dataframe_sample(
            df,
            rows=150
        )

        # ------------------------------
        # Build Prompt
        # ------------------------------

        prompt = build_prompt(
            question=question,
            profile=profile,
            analysis=analysis,
            statistics=statistics,
            dataset_sample=dataset_sample,
        )

        # ------------------------------
        # Gemini Response
        # ------------------------------

        raw_response = generate_ai_response(
            prompt
        )

        # ------------------------------
        # Parse JSON
        # ------------------------------

        result = parse_ai_response(
            raw_response
        )

        # ------------------------------
        # Extra Validation
        # ------------------------------

        if "answer" not in result:

            result["answer"] = (
                "No answer generated."
            )

        if "charts" not in result:

            result["charts"] = []

        if "recommendation" not in result:

            result["recommendation"] = ""

        if "follow_up_questions" not in result:

            result["follow_up_questions"] = []

        # ------------------------------
        # Validate Charts
        # ------------------------------

        valid_chart_types = [
            "bar",
            "line",
            "pie",
        ]

        cleaned_charts = []

        for chart in result["charts"]:

            if not isinstance(chart, dict):
                continue

            chart.setdefault("title", "")

            chart.setdefault("type", "bar")

            chart.setdefault("xKey", "")

            chart.setdefault("yKey", "")

            chart.setdefault("data", [])

            if chart["type"] not in valid_chart_types:

                chart["type"] = "bar"

            cleaned_charts.append(chart)

        result["charts"] = cleaned_charts

        # ------------------------------
        # Recommendation
        # ------------------------------

        if result["recommendation"] is None:

            result["recommendation"] = ""

        # ------------------------------
        # Follow-up Questions
        # ------------------------------

        if not isinstance(
            result["follow_up_questions"],
            list,
        ):

            result["follow_up_questions"] = []

        return make_json_safe(result)

    except Exception as e:

        return {

            "answer": f"AI processing failed: {str(e)}",

            "charts": [],

            "recommendation": "",

            "follow_up_questions": []
        }