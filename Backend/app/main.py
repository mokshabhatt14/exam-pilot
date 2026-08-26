"""
app/main.py

FastAPI entry point for ExamPilot's backend. Run with:
    uvicorn app.main:app --reload

Other team members add their own routers the same way the twin router
is added below (e.g. app/api/routes/planner.py, app/api/routes/auth.py).
"""

from fastapi import FastAPI
from app.api.routes import twin

app = FastAPI(title="ExamPilot API")

app.include_router(twin.router)


@app.get("/")
def root():
    return {"status": "ExamPilot backend running"}
