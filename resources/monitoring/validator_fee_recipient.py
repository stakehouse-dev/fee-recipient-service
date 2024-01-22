from fastapi import APIRouter, Depends, HTTPException
from services.fee_recipient.fee_recipient_service import FeeRecipientService


router = APIRouter(
    prefix="/monitoring/validator_fee_recipient",
    tags=["validator_fee_recipient"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/block")
def get_block_fee_recipient_data(slot: int):
    """
    It takes a slot number as an argument and returns the fee recipient data for that slot

    :param slot: The slot number of the block you want to get the fee recipient data for\n
    :type slot: int\n
    :return: The data is being returned as a dict.\n
    """
    try:
        data = FeeRecipientService().get_fee_recipient_for_slot(slot)
        return data
    except Exception as e:
        if "Block not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance")
def validator_fee_recipient_compliance(slot: int):
    """
    It takes a slot number as an argument, and returns the fee recipient
    compliance data for that slot, if the block was/was not proposed by
    a validator in an LSD network.

    :param slot: The slot number of the block to query\n
    :type slot: int\n
    :return: The data is being returned as a dictionary.\n
    """
    try:
        data = FeeRecipientService().fee_recipient_compliance(slot)
        return data
    except Exception as e:
        if "Block not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def validator_fee_recipient_health(validator: str, lsd_id: str = None):
    """
    The historical count of compliant blocks against the total number of blocks for a validator,
    giving an overall compliance score for each validator. Can be filtered by lsd_id the validator
    is/was part of.

    :param validator: The validator's bls key\n
    :type validator: str\n
    :param lsd_id: The ID of the LSD\n
    :type lsd_id: str\n
    :return: The return value is a dictionary\n
    """
    # Count of compliant blocks against the total number of blocks for validator
    if lsd_id:
        data = FeeRecipientService().get_validator_fee_recipient_health_in_lsd(
            validator, lsd_id
        )
    else:
        data = FeeRecipientService().get_validator_fee_recipient_health(validator)
    return data


@router.get("/health/all")
def validator_fee_recipient_health_all(start_date: str, end_date: str):
    """
    The historical count of compliant blocks against the total number of blocks for all validators
    across all lsd networks between a start and end date time. The start date is older than the end date.

    :param start_date: The start date time in the format of YYYY-MM-DD HH:MM:SS\n
    :type start_date: str\n
    :param end_date: The end date time in the format of YYYY-MM-DD HH:MM:SS\n
    :type end_date: str\n
    :return: The return value is a dictionary\n
    """
    # Count of compliant blocks against the total number of blocks for all validators in lsd network
    data = FeeRecipientService().get_all_validators_fee_recipient_health(
        start_date, end_date
    )
    return data

@router.get("/health/all/by_time_division")
def validator_fee_recipient_health_all_details(start_date: str, end_date: str, time_divisions: int):
    """
    The historical count of compliant blocks against the total number of blocks for all validators
    across all lsd networks between a start and end date time. The start date is older than the end date.

    :param start_date: The start date time in the format of YYYY-MM-DD HH:MM:SS\n
    :type start_date: str\n
    :param end_date: The end date time in the format of YYYY-MM-DD HH:MM:SS\n
    :type end_date: str\n
    :param time_divisions: The number of time divisions to split the start and end date time into\n
    :type time_divisions: int\n
    :return: The return value is a dictionary\n
    """
    # Count of compliant blocks against the total number of blocks for all validators in lsd network
    data = FeeRecipientService().get_all_validators_fee_recipient_health_details(
        start_date, end_date, time_divisions
    )
    return data
