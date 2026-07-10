from fastapi import FastAPI
from app.api.routers.bookings import router as bookings_router
from app.api.routers.availability import router as availability_router
from app.api.routers.doctors import router as doctors_router

app = FastAPI(title="AI Booking System", version="1.0.0")

app.include_router(bookings_router, prefix="/clinics/{clinic_id}", tags=["bookings"])
app.include_router(availability_router, prefix="/clinics/{clinic_id}", tags=["availability"])
app.include_router(doctors_router, prefix="/clinics/{clinic_id}", tags=["doctors"])

@app.get("/health")
def health():
    return {"status" : "ok"}


