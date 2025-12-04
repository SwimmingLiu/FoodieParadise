from typing import List, Dict, Any
from app.database import SessionLocal
from app.models.history import HistoryModel

def get_user_history() -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        records = db.query(HistoryModel).order_by(HistoryModel.created_at.desc()).all()
        return [
            {
                "type": r.type,
                "image_path": r.image_path,
                "summary": r.summary,
                "details": r.details,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ]
    finally:
        db.close()

def save_history(record: Dict[str, Any]):
    db = SessionLocal()
    try:
        db_record = HistoryModel(
            type=record["type"],
            image_path=record["image_path"],
            summary=record["summary"],
            details=record["details"]
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
    finally:
        db.close()
