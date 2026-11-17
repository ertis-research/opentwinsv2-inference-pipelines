from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas import automation as schemas
from src.config import settings
from src.models.automation import Automation
from src.services.bentloy_service import BentloyService
from src.services.k8s_service import k8s_service
from src.services.wot_service import WotService
from src.services.kafka_service import kafka_service
from src.config import settings
import json
from typing import List, Optional

router = APIRouter()
bentloy_service = BentloyService(settings.BENTLOY_SERVICE_URL)
wot_service = WotService(settings.THINGS_SERVICE_URL)

def _format_response(db_item):
    data = db_item.__dict__.copy()
    data["source_things"] = json.loads(db_item.source_things)
    data["target_events"] = json.loads(db_item.target_events)
    # Map back to schema names if needed (e.g. cron_expression)
    return data

@router.post("/", response_model=schemas.AutomationResponse)
async def create_automation(config: schemas.AutomationCreate, db: Session = Depends(get_db)):
    # 1. Prepare Env Vars for Worker
    # We must convert Pydantic models to dicts before json.dumps
    source_things_dict = {
        thing_id: [m.model_dump() for m in mappings]
        for thing_id, mappings in config.source_things.items()
    }

    # Check if things exist
    for thing_id in source_things_dict:
        if (await wot_service.get_thing(thing_id)) is None:
            raise HTTPException(status_code=404, detail=f"Thing {thing_id} not found")

    # Check if model exists
    if (await bentloy_service.get_model(model_name=config.ml_model)) is None:
        raise HTTPException(status_code=404, detail=f"Model {config.ml_model} not found")
    
    env_vars = {
        "SOURCE_THINGS": json.dumps(source_things_dict),
        "ML_MODEL": config.ml_model,
        "TARGET_EVENTS": json.dumps([te.model_dump() for te in config.target_events]),
        "KAFKA_BROKERS": settings.KAFKA_BROKERS,
        "THINGS_SERVICE_URL": settings.THINGS_SERVICE_URL,
        "BENTLOY_SERVICE_URL": settings.BENTLOY_SERVICE_URL
    }

    # 2. Create CronJob in K8s
    k8s_name = config.name.lower().replace(" ", "-")
    try:
        k8s_service.create_cronjob(
            name=k8s_name,
            schedule=config.cron_expression,
            image=settings.WORKER_IMAGE,
            env_vars=env_vars
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"K8s Error: {str(e)}")

    # 3. Save to DB
    db_automation = Automation(
        name=config.name,
        cron_expression=config.cron_expression,
        source_things=json.dumps(source_things_dict),
        ml_model=config.ml_model,
        target_events=json.dumps([te.model_dump() for te in config.target_events]),
        status="active"
    )
    db.add(db_automation)
    db.commit()
    db.refresh(db_automation)

    return _format_response(db_automation)

@router.get("/", response_model=List[schemas.AutomationResponse])
async def list_automations(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Automation)
    if search:
        query = query.filter(Automation.name.contains(search))
    
    items = query.offset((page - 1) * pageSize).limit(pageSize).all()
    return [_format_response(item) for item in items]

@router.get("/{id}", response_model=schemas.AutomationResponse)
async def get_automation(id: int, db: Session = Depends(get_db)):
    db_automation = db.query(Automation).filter(Automation.id == id).first()
    if not db_automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    return _format_response(db_automation)

@router.delete("/{id}")
async def delete_automation(id: int, db: Session = Depends(get_db)):
    db_automation = db.query(Automation).filter(Automation.id == id).first()
    if not db_automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    k8s_name = db_automation.name.lower().replace(" ", "-")
    k8s_service.delete_cronjob(k8s_name)
    
    db.delete(db_automation)
    db.commit()
    return {"message": "Automation deleted"}

@router.patch("/{id}/status")
async def update_status(id: int, status_update: schemas.AutomationUpdate, db: Session = Depends(get_db)):
    db_automation = db.query(Automation).filter(Automation.id == id).first()
    if not db_automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    if status_update.status not in ["active", "paused"]:
        raise HTTPException(status_code=400, detail="Status must be 'active' or 'paused'")

    k8s_name = db_automation.name.lower().replace(" ", "-")
    suspend = True if status_update.status == "paused" else False
    k8s_service.suspend_cronjob(k8s_name, suspend=suspend)
    
    db_automation.status = status_update.status
    db.commit()
    return {"status": db_automation.status}

@router.post("/{id}/trigger")
async def trigger_automation(id: int, db: Session = Depends(get_db)):
    db_automation = db.query(Automation).filter(Automation.id == id).first()
    if not db_automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    k8s_name = db_automation.name.lower().replace(" ", "-")
    try:
        job = k8s_service.trigger_job(k8s_name)
        return {"message": "Job triggered", "job_name": job.metadata.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{id}/executions")
async def get_executions(id: int, db: Session = Depends(get_db)):
    db_automation = db.query(Automation).filter(Automation.id == id).first()
    if not db_automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    k8s_name = db_automation.name.lower().replace(" ", "-")
    return k8s_service.get_job_executions(k8s_name)
