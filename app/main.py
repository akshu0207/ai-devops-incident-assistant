import json

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai_analyzer import analyze_log
from app.database import Base, engine, get_db
from app.db_models import IncidentRecord
from app.models import IncidentAnalysis


# Create database tables if they do not exist.
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="AI DevOps Incident Assistant",
    description="AI-powered log analysis and incident troubleshooting platform",
    version="0.2.0",
)


class LogRequest(BaseModel):
    log: str


def save_incident(log_text: str, analysis: IncidentAnalysis, db: Session):
    data = analysis.model_dump()

    incident = IncidentRecord(
        log=log_text,
        severity=data["severity"],
        summary=data["summary"],
        root_cause=data["root_cause"],
        possible_causes=json.dumps(data["possible_causes"]),
        recommended_actions=json.dumps(data["recommended_actions"]),
        confidence=data["confidence"],
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident


@app.get("/")
def root():
    return {
        "message": "AI DevOps Incident Assistant is running!",
        "status": "healthy",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/analyze-log", response_model=IncidentAnalysis)
def analyze_log_endpoint(
    request: LogRequest,
    db: Session = Depends(get_db),
):
    analysis = analyze_log(request.log)
    save_incident(request.log, analysis, db)
    return analysis


@app.post("/analyze-file", response_model=IncidentAnalysis)
async def analyze_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    log_text = content.decode("utf-8", errors="replace")

    if not log_text.strip():
        raise HTTPException(status_code=400, detail="Log file is empty.")

    analysis = analyze_log(log_text)
    save_incident(log_text, analysis, db)
    return analysis


@app.get("/incidents")
def get_incidents(db: Session = Depends(get_db)):
    incidents = (
        db.query(IncidentRecord)
        .order_by(IncidentRecord.id.desc())
        .all()
    )

    return [incident.to_dict() for incident in incidents]


@app.get("/incidents/{incident_id}")
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
):
    incident = (
        db.query(IncidentRecord)
        .filter(IncidentRecord.id == incident_id)
        .first()
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found.",
        )

    return incident.to_dict()