from fastapi import APIRouter, Depends, HTTPException, Body
from services.scheduler.scheduler_service import Scheduler
from services.fee_recipient.fee_recipient_service import FeeRecipientService
from datetime import datetime
from common.constants import BACKFILL_SLOT_RANGE


router = APIRouter(
    prefix="/api",
    tags=["api"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/status")
def api_status():
    """
    It returns a dictionary with two keys: server_status and scheduler_status. 
    
    The value of server_status is always "ok" if the response is successful.
    
    The value of scheduler_status is "Alive" if the scheduler is running, and "Not alive" if it's not
    
    :return: A dictionary with two keys and two values.\n
    """
    return {
        "server_status": "ok",
        "scheduler_status": ("Alive" if Scheduler().state == 1 else "Not alive"),
    }


@router.post("/start_backfill")
def start_backfill(
    start_slot: int = Body(None, description="The slot number to start the backfill process from, if not provided, the backfill will start from "+str(BACKFILL_SLOT_RANGE)+" behind the latest slot"),
    end_slot: int = Body(None, description="The slot number to end the backfill process at, if not provided, the backfill will end at the latest slot"),
):
    """
    It takes two arguments, start_slot and end_slot, and starts a backfill process for the given slots.
    
    :param start_slot: The slot number to start the backfill process from, if not provided, the backfill will start from a range behind the latest slot\n
    :type start_slot: int\n
    :param end_slot: The slot number to end the backfill process at, if not provided, the backfill will end at the latest slot\n
    :type end_slot: int\n
    :return: A dictionary with two keys and two values.\n
    """
    try:
        if start_slot and end_slot:
            assert start_slot < end_slot, "start_slot must be less than end_slot"

        missing_slots, existing_run = FeeRecipientService().backfill_missing_fee_recipient_compliance(start_slot, end_slot, manual=True)
        if existing_run:
            return {"status": "ok", "message": "Backfill already running for the given slots"}
        if len(missing_slots) == 0:
            return {"status": "ok", "message": "No missing slots found for the given range", "missing_slots": missing_slots, "len_missing_slots": len(missing_slots)}
        else:
            return {"status": "ok", "message": "Backfill started for the given slots", "missing_slots": missing_slots, "len_missing_slots": len(missing_slots)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
