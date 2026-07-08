from datetime import datetime
from pydantic import BaseModel

class TimeSlotSchema(BaseModel):
    start_time: datetime
    end_time: datetime