from sqlalchemy import Column, Integer, String, Text
from src.database import Base

class Automation(Base):
    __tablename__ = "automations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    cron_expression = Column(String)
    status = Column(String, default="active")
    source_things = Column(Text) # JSON string
    ml_model = Column(String)
    target_events = Column(Text) # JSON string
