import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.database import Base


class IncidentRecord(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    log = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)
    summary = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=False)

    possible_causes = Column(Text, nullable=False)
    recommended_actions = Column(Text, nullable=False)

    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "log": self.log,
            "severity": self.severity,
            "summary": self.summary,
            "root_cause": self.root_cause,
            "possible_causes": json.loads(self.possible_causes),
            "recommended_actions": json.loads(
                self.recommended_actions
            ),
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }
