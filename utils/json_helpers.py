import json
import re


def safe_parse_json(text):

    text = text.strip()

    text = re.sub(
        r"^```json",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```",
        "",
        text,
    )

    text = re.sub(
        r"```$",
        "",
        text,
    )

    text = text.strip()

    try:

        return json.loads(text)

    except Exception:

       return {

    "answer": text,

    "charts": [],

    "recommendation": "",

    "follow_up_questions": []

}