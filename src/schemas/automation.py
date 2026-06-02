from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PropertyMapping(BaseModel):
    property: str
    mapping_key: str

class TargetEvent(BaseModel):
    topic: str
    event_type: str

class AutomationBase(BaseModel):
    name: str
    cron_expression: str = Field(..., alias="cron") # Alias for backward compatibility if needed, but we'll use cron_expression
    source_things: Dict[str, List[PropertyMapping]]
    ml_model: str
    target_events: List[TargetEvent]

    class Config:
        populate_by_name = True

class AutomationCreate(AutomationBase):
    pass

class AutomationUpdate(BaseModel):
    status: Optional[str] = None

class AutomationResponse(AutomationBase):
    id: int
    status: str

    class Config:
        from_attributes = True
