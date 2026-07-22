import json
import datetime
from uuid import UUID
from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.deps import (
    get_booking_service,
    get_availability_service,
    get_clinic_repository,
    get_doctor_repository,
)
from app.services.booking_service import BookingService
from app.services.availability_service import AvailabilityService
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.doctor_repository import DoctorRepository

router = APIRouter(prefix="/vapi")


def _parse_datetime(val: str) -> datetime.datetime:
    if isinstance(val, datetime.datetime):
        return val
    cleaned = str(val).replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(cleaned)


@router.post("/webhook")
def vapi_webhook(
    payload: Dict[str, Any],
    booking_service: BookingService = Depends(get_booking_service),
    availability_service: AvailabilityService = Depends(get_availability_service),
    clinic_repository: ClinicRepository = Depends(get_clinic_repository),
    doctor_repository: DoctorRepository = Depends(get_doctor_repository),
):
    """
    Webhook handler for Vapi AI tool calls and events.
    Exposes functions: list_doctors, check_availability, create_booking.
    """
    message = payload.get("message", {})
    message_type = message.get("type")

    # If it's not a tool-calls message, return status ok
    if message_type != "tool-calls":
        return {"status": "ok", "message_type": message_type}

    results = []
    tool_calls = message.get("toolCalls", [])

    for call in tool_calls:
        call_id = call.get("id", "")
        function = call.get("function", {})
        func_name = function.get("name")
        args = function.get("arguments", {})

        # If arguments are passed as a JSON string, parse it
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}

        try:
            if func_name == "list_doctors":
                clinic_id_str = args.get("clinic_id")
                if not clinic_id_str:
                    result_content = {"error": "clinic_id is required"}
                else:
                    clinic_id = UUID(clinic_id_str)
                    clinic = clinic_repository.get_by_id(clinic_id)
                    if clinic is None:
                        result_content = {"error": "Clinic not found"}
                    else:
                        doctors = doctor_repository.list_by_clinic(clinic_id)
                        result_content = [
                            {
                                "doctor_id": str(d.doctor_id),
                                "name": d.name,
                                "specialty": d.specialty,
                            }
                            for d in doctors
                        ]

            elif func_name == "check_availability":
                doctor_id_str = args.get("doctor_id")
                start_time_str = args.get("requested_start_time")
                clinic_id_str = args.get("clinic_id")

                if not doctor_id_str or not start_time_str:
                    result_content = {"error": "doctor_id and requested_start_time are required"}
                else:
                    doctor_id = UUID(doctor_id_str)
                    start_time = _parse_datetime(start_time_str)

                    if clinic_id_str:
                        clinic_id = UUID(clinic_id_str)
                        clinic = clinic_repository.get_by_id(clinic_id)
                        if clinic is None:
                            result_content = {"error": "Clinic not found"}

                    doctor = doctor_repository.get_by_id(doctor_id)
                    if doctor is None:
                        result_content = {"error": "Doctor not found"}
                    else:
                        res = availability_service.check_availability(
                            doctor_id=doctor_id,
                            requested_start=start_time,
                        )
                        result_content = {
                            "is_available": res.is_available,
                            "requested_start": res.requested_start.isoformat(),
                            "requested_end": res.requested_end.isoformat(),
                            "alternative_slots": [
                                {
                                    "start_time": s[0].isoformat(),
                                    "end_time": s[1].isoformat(),
                                }
                                for s in res.alternative_slots
                            ],
                        }

            elif func_name == "create_booking":
                clinic_id_str = args.get("clinic_id")
                doctor_id_str = args.get("doctor_id")
                patient_name = args.get("patient_name")
                patient_phone = args.get("patient_phone")
                patient_email = args.get("patient_email")
                start_time_str = args.get("requested_start_time")

                if not all([clinic_id_str, doctor_id_str, patient_name, patient_phone, start_time_str]):
                    result_content = {
                        "error": "clinic_id, doctor_id, patient_name, patient_phone, and requested_start_time are required"
                    }
                else:
                    clinic_id = UUID(clinic_id_str)
                    doctor_id = UUID(doctor_id_str)
                    start_time = _parse_datetime(start_time_str)

                    clinic = clinic_repository.get_by_id(clinic_id)
                    if clinic is None:
                        result_content = {"error": "Clinic not found"}
                    else:
                        doctor = doctor_repository.get_by_id(doctor_id)
                        if doctor is None or doctor.clinic_id != clinic_id:
                            result_content = {"error": "Doctor not found"}
                        else:
                            idempotency_key = args.get("idempotency_key") or f"vapi-{call_id}"
                            res = booking_service.process_booking(
                                idempotency_key=idempotency_key,
                                clinic_id=clinic_id,
                                doctor_id=doctor_id,
                                patient_name=patient_name,
                                patient_phone=patient_phone,
                                patient_email=patient_email,
                                requested_start_time=start_time,
                            )
                            result_content = {
                                "status": res.status,
                                "booking_request_id": str(res.booking_request.booking_request_id) if res.booking_request else None,
                                "appointment_id": str(res.appointment.appointment_id) if res.appointment else None,
                                "alternative_slots": [
                                    {
                                        "start_time": s[0].isoformat(),
                                        "end_time": s[1].isoformat(),
                                    }
                                    for s in res.alternative_slots
                                ],
                            }

            else:
                result_content = {"error": f"Unknown tool function: {func_name}"}

        except Exception as e:
            result_content = {"error": str(e)}

        results.append({
            "toolCallId": call_id,
            "result": result_content,
        })

    return {"results": results}
