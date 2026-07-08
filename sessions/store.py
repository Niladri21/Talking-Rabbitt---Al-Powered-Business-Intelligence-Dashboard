import uuid

from fastapi import HTTPException

# In-memory session storage
sessions = {}


def create_session(df, profile):
    """
    Create a new session and store:
    - cleaned dataframe
    - dataset profile
    - cached analysis
    """

    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "df": df,
        "profile": profile,
        "analysis": None,
    }

    return session_id


def get_session(session_id: str):
    """
    Retrieve a session by ID.
    """

    session = sessions.get(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        )

    return session


def save_analysis(session_id: str, analysis: dict):
    """
    Cache analysis for a session.
    """

    session = get_session(session_id)

    session["analysis"] = analysis


def clear_session(session_id: str):
    """
    Delete a session.
    """

    if session_id in sessions:
        del sessions[session_id]