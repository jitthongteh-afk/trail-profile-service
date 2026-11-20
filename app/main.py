import logging
from contextlib import closing
from pathlib import Path

import pyodbc
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.auth import router as auth_router
from app.db import get_connection
from app.profile_api import router as profile_router


logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Trail App ProfileService",
    description="Profile management API for the Country Trust Trail App.",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(profile_router)


@app.get("/", tags=["Service"])
def service_information():
    return {
        "service": "ProfileService",
        "version": "0.1.0",
        "documentation": "/docs",
        "frontend": "/ui",
    }


@app.get("/health", tags=["Service"])
def health_check():
    return {
        "status": "ok",
        "service": "ProfileService",
    }


@app.get(
    "/health/database",
    tags=["Service"],
    responses={
        503: {"description": "Database connection or query failed."}
    },
)
def database_health_check():
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    "SELECT TOP (1) UserID FROM CW2.vw_UserProfile;"
                )
                cursor.fetchone()

    except pyodbc.Error:
        logger.exception("Database health check failed.")
        raise HTTPException(
            status_code=503,
            detail="Database connection or query failed.",
        ) from None

    return {
        "status": "ok",
        "database": "connected",
        "profile_view": "accessible",
    }


@app.get(
    "/activities",
    tags=["Activities"],
    responses={
        503: {"description": "Unable to retrieve activity categories."}
    },
)
def list_activities():
    try:
        with closing(get_connection()) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    """
                    SELECT ActivityID, ActivityName
                    FROM CW2.ACTIVITY
                    ORDER BY ActivityID;
                    """
                )

                activities = [
                    {
                        "activity_id": row.ActivityID,
                        "activity_name": row.ActivityName,
                    }
                    for row in cursor.fetchall()
                ]

    except pyodbc.Error:
        logger.exception("Failed to retrieve activity categories.")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve activity categories.",
        ) from None

    return {"activities": activities}


@app.get("/ui", include_in_schema=False)
def frontend_page():
    page_path = Path(__file__).resolve().parent / "static" / "index.html"

    if not page_path.is_file():
        logger.error("Frontend file not found: %s", page_path)
        raise HTTPException(
            status_code=500,
            detail="Frontend file is missing.",
        )

    return FileResponse(page_path, media_type="text/html")