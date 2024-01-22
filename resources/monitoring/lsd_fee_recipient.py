from fastapi import APIRouter, Depends, HTTPException
from services.data.lsd_subgraph_service import LSDSubgraphService
from services.fee_recipient.fee_recipient_service import FeeRecipientService


router = APIRouter(
    prefix="/monitoring/lsd_fee_recipient",
    tags=["lsd_fee_recipient"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/fee_address")
def lsd_fee_address(lsd_id: str):
    """
    Get fee recipient syndicate address for lsd network
    
    :param lsd_id: The ID of the LSD you want to get the fee recipient address for\n
    :type lsd_id: str\n
    :return: The address of the fee recipient for the lsd network.\n
    """
    # Get fee recipient syndicate address for lsd network
    result = LSDSubgraphService().get_lsds([lsd_id])
    if result:
        return result[0].get("feeRecipientAndSyndicate")
    return None


@router.get("/health")
def lsd_fee_recipient_health(lsd_id: str):
    """
    The count of compliant blocks against the total number of blocks for lsd
    network, giving an overall compliance score for the network.
    
    :param lsd_id: The ID of the LSD network you want to query\n
    :type lsd_id: str\n
    :return: The data is being returned as a dictionary.\n
    """
    # Count of compliant blocks against the total number of blocks for lsd network
    data = FeeRecipientService().get_lsd_fee_recipient_health(lsd_id)
    return data


@router.get("/health/validators")
def lsd_fee_recipient_health_for_validators(lsd_id: str):
    """
    The count of compliant blocks against the total number of blocks for each validator currently
    in an lsd network, giving an overall compliance score for each validator.
    
    :param lsd_id: The ID of the LSD network you want to query\n
    :type lsd_id: str\n
    :return: A list of dictionaries.\n
    """
    # Count of compliant blocks against the total number of blocks for all validators in lsd network
    data = FeeRecipientService().get_all_validators_fee_recipient_health_in_lsd(lsd_id)
    return data

@router.get("/history")
def lsd_fee_recipient_compliance_history(lsd_id: str):
    """
    A historical list of compliance data by slot proposed by any validator in the lsd network.

    :param lsd_id: The ID of the LSD network you want to query\n
    :type lsd_id: str\n
    :return: A list of dictionaries.\n
    """
    # A historical list of compliance data by slot proposed by any validator in the lsd network
    data = FeeRecipientService().get_lsd_fee_recipient_compliance_history(lsd_id)
    return data
