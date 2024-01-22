import requests
from apiconfig import APIConfig
from services.data.beacon_chain_service import BeaconChainService
from services.data.lsd_subgraph_service import LSDSubgraphService
from services.scheduler.scheduler_service import Scheduler
from models.backfill_jobs_model import BackfillJobs
from models.fee_recipient_model import FeeRecipientMonitoring
from models.validator_model import Validator
from models.lsd_model import LSD
from models.block_monitored_model import BlockMonitored
from models.block_transaction_model import BlockTransaction
from monitoring_etl_models.validator_indexes_model import ValidatorLSD
from datetime import datetime
from collections import defaultdict
import atexit
import numpy as np

from eth.vm.forks.gray_glacier.transactions import (
    GrayGlacierTransactionBuilder as TransactionBuilder,
)
from eth_utils import (
    encode_hex,
    to_bytes,
)

from sqlalchemy.dialects.mysql import insert
from configuration.database_configuration import SessionLocal, ETL_SessionLocal
from sqlalchemy import func, case
from common.constants import BACKFILL_SLOT_RANGE, EPOCH_SLOTS


class FeeRecipientService:
    """
    FeeRecipientService class that contains the logic to get the fee recipient and check compliance
    """

    def __init__(self):
        """
        Constructor that initializes the APIConfig class, the BeaconChainService
        class, and the LSDSubgraphService class.
        """
        self._config = APIConfig()
        self.beacon_chain_service = BeaconChainService()
        self.lsd_subgraph_service = LSDSubgraphService()

        atexit.register(self.stop_all_manual_backfills)

    def stop_all_manual_backfills(self):
        with SessionLocal() as session:
            session.query(BackfillJobs).filter(BackfillJobs.completed == False).update(
                {BackfillJobs.completed: True, BackfillJobs.stopped: True}
            )
            session.commit()
            session.flush()

    def get_fee_recipient_for_slot(self, slot, pre_check=True):
        if pre_check:
            try:
                with SessionLocal() as session:
                    block_checked = (
                        session.query(BlockMonitored)
                        .filter(BlockMonitored.slot == int(slot))
                        .first()
                    )
                    if block_checked is not None:

                        block_transactions = (
                            session.query(BlockTransaction)
                            .filter(BlockTransaction.slot == int(slot))
                            .all()
                        )

                        return {
                            "slot": slot,
                            "fee_recipient": block_checked.fee_recipient,
                            "validator_index": block_checked.validator_index,
                            "validator_pubkey": block_checked.validator_id,
                            "execution_chain_timestamp": block_checked.execution_chain_timestamp,
                            "execution_chain_block_hash": block_checked.execution_chain_block_hash,
                            "execution_chain_block_number": block_checked.execution_chain_block_number,
                            "execution_chain_gas_used": block_checked.execution_chain_gas_used,
                            "transactions": [
                                {
                                    "slot": int(block_transaction.slot),
                                    "block_hash": block_transaction.block_hash,
                                    "block_number": int(block_transaction.block_number),
                                    "tx_hash": block_transaction.tx_hash,
                                    "to": block_transaction.to,
                                    "sender": block_transaction.sender,
                                    "value": str(block_transaction.value),
                                    "gas": str(block_transaction.gas),
                                }
                                for block_transaction in block_transactions
                            ],
                        }
            except Exception as e:
                raise e

        block = self.beacon_chain_service.get_block(slot)
        if block is None:
            raise Exception("Block not found")
        fee_recipient = block["body"]["execution_payload"]["fee_recipient"]
        execution_chain_timestamp = int(block["body"]["execution_payload"]["timestamp"])
        execution_chain_block_hash = block["body"]["execution_payload"]["block_hash"]
        execution_chain_block_number = int(
            block["body"]["execution_payload"]["block_number"]
        )
        execution_chain_gas_used = int(block["body"]["execution_payload"]["gas_used"])
        proposer_index = int(block["proposer_index"])

        try:
            validator_pubkey = self.get_validator_pubkey(slot, proposer_index)
        except Exception as e:
            raise Exception("Validator not found")

        transactions = []
        for raw_transaction in block["body"]["execution_payload"]["transactions"]:
            signed_tx_as_bytes = to_bytes(hexstr=raw_transaction)
            decoded_tx = TransactionBuilder().decode(signed_tx_as_bytes)
            tx_object = {
                "slot": int(slot),
                "block_hash": execution_chain_block_hash,
                "block_number": int(execution_chain_block_number),
                "tx_hash": encode_hex(decoded_tx.hash),
                "to": encode_hex(decoded_tx.to),
                "sender": encode_hex(decoded_tx.sender),
                "value": str(decoded_tx.value),
                "gas": str(decoded_tx.gas),
            }

            # ensure that the txobject is valid
            if (len(tx_object["tx_hash"]) > 0 and 
            len(tx_object["to"]) > 0 and 
            np.uint64(tx_object["gas"]) > 0):
                transactions.append(tx_object)
        
        print("Slot", slot, "found")
        print("Decoding", len(block["body"]["execution_payload"]["transactions"]), "transactions")
        print("Decoded", len(transactions), "transactions successfully")

        result = {
            "slot": slot,
            "fee_recipient": fee_recipient,
            "validator_index": proposer_index,
            "validator_pubkey": validator_pubkey,
            "execution_chain_timestamp": execution_chain_timestamp,
            "execution_chain_block_hash": execution_chain_block_hash,
            "execution_chain_block_number": execution_chain_block_number,
            "execution_chain_gas_used": execution_chain_gas_used,
            "transactions": transactions,
        }

        try:
            self.add_or_update_block_monitored(result)
        except Exception as e:
            raise Exception("Error adding or updating block monitored")

        return result

    def get_validator_pubkey(self, slot, validator_index):
        """
        It returns the public key of the validator at the given slot and validator index

        :param slot: The slot number of the block you want to get the validator pubkey for
        :param validator_index: 0
        :return: The public key of the validator.
        """
        validator = self.beacon_chain_service.get_validator(slot, validator_index)
        if validator is None:
            raise Exception("Validator not found")
        pubkey = validator["pubkey"]
        return pubkey

    def fee_recipient_compliance(self, slot):
        print("Checking fee recipient compliance for current slot: ", slot)
        try:
            with SessionLocal() as session:
                fee_recipient_compliance = (
                    session.query(FeeRecipientMonitoring)
                    .filter(FeeRecipientMonitoring.slot == slot)
                    .join(LSD, LSD.id == FeeRecipientMonitoring.lsd_id)
                    .join(
                        Validator, Validator.id == FeeRecipientMonitoring.validator_id
                    )
                    .with_entities(
                        FeeRecipientMonitoring.slot,
                        FeeRecipientMonitoring.fee_recipient,
                        FeeRecipientMonitoring.contains_fee_transaction,
                        FeeRecipientMonitoring.fee_transaction_hash,
                        FeeRecipientMonitoring.compliant,
                        Validator.id,
                        Validator.index,
                        LSD.id,
                        LSD.ticker,
                        LSD.lsd_index,
                        LSD.fee_recipient_and_syndicate,
                    )
                    .first()
                )

                if fee_recipient_compliance is not None:
                    return {
                        "slot": fee_recipient_compliance[0],
                        "fee_recipient": fee_recipient_compliance[1],
                        "contains_fee_transaction": fee_recipient_compliance[2],
                        "fee_transaction_hash": fee_recipient_compliance[3],
                        "fee_recipient_compliant": fee_recipient_compliance[2],
                        "validator_pubkey": fee_recipient_compliance[3],
                        "validator_index": fee_recipient_compliance[4],
                        "validator_in_lsd": True,
                        "lsd_id": fee_recipient_compliance[5],
                        "lsd_ticker": fee_recipient_compliance[6],
                        "lsd_index": fee_recipient_compliance[7],
                        "lsd_fee_recipient_address": fee_recipient_compliance[8],
                    }
                else:
                    block_checked = (
                        session.query(BlockMonitored)
                        .filter(BlockMonitored.slot == int(slot))
                        .with_entities(
                            BlockMonitored.fee_recipient,
                            BlockMonitored.validator_id,
                            BlockMonitored.validator_index,
                        )
                        .first()
                    )
                    if block_checked is not None:
                        return {
                            "slot": slot,
                            "fee_recipient": block_checked[0],
                            "contains_fee_transaction": False,
                            "fee_transaction_hash": None,
                            "fee_recipient_compliant": False,
                            "validator_pubkey": block_checked[1],
                            "validator_index": block_checked[2],
                            "validator_in_lsd": False,
                            "lsd_id": None,
                            "lsd_ticker": None,
                            "lsd_index": None,
                            "lsd_fee_recipient_address": None,
                        }
        except Exception as e:
            raise e

        try:
            block_fee_recipient_data = self.get_fee_recipient_for_slot(slot, False)
        except Exception as e:
            raise e
        if block_fee_recipient_data is None:
            raise Exception("Block not found")
        validator_pubkey = block_fee_recipient_data["validator_pubkey"]

        validator_lsd = self.get_validator_lsd_at_epoch(
            validator_pubkey, int(slot) // EPOCH_SLOTS
        )

        fee_recipient_compliant = False
        contains_fee_transaction = False
        fee_transaction_hash = None
        if validator_lsd:
            for lsd in validator_lsd:
                lsd_id = lsd["id"]
                lsd_ticker = lsd["ticker"]
                lsd_index = lsd["lsdIndex"]
                lsd_fee_recipient_address = lsd["feeRecipientAndSyndicate"]
                if (
                    lsd_fee_recipient_address
                    == block_fee_recipient_data["fee_recipient"]
                ):
                    fee_recipient_compliant = True
                    break
                else:
                    for transaction in block_fee_recipient_data["transactions"]:
                        if (
                            lsd_fee_recipient_address.lower().strip()
                            == transaction["to"].lower().strip() and np.uint64(transaction["value"]) > 0
                        ):
                            fee_recipient_compliant = True
                            contains_fee_transaction = True
                            fee_transaction_hash = transaction["tx_hash"]
                            break

        data = {
            "slot": slot,
            "fee_recipient": block_fee_recipient_data["fee_recipient"],
            "contains_fee_transaction": contains_fee_transaction,
            "fee_transaction_hash": fee_transaction_hash,
            "validator_index": block_fee_recipient_data["validator_index"],
            "validator_pubkey": block_fee_recipient_data["validator_pubkey"],
            "validator_in_lsd": (True if validator_lsd else False),
            "lsd_id": (lsd_id if validator_lsd else None),
            "lsd_ticker": (lsd_ticker if validator_lsd else None),
            "lsd_index": (lsd_index if validator_lsd else None),
            "lsd_fee_recipient_address": (
                lsd_fee_recipient_address if validator_lsd else None
            ),
            "fee_recipient_compliant": fee_recipient_compliant,
        }

        print("Slot: ", slot)
        print("Number of Transactions: ", len(block_fee_recipient_data["transactions"]))
        print("Fee Recipient: ", block_fee_recipient_data["fee_recipient"])
        print("Validator Index: ", block_fee_recipient_data["validator_index"])
        print("Validator Pubkey: ", block_fee_recipient_data["validator_pubkey"])
        print("Validator in LSD: ", (True if validator_lsd else False))
        print("LSD ID: ", (lsd_id if validator_lsd else None))
        print("LSD Ticker: ", (lsd_ticker if validator_lsd else None))
        print("LSD Index: ", (lsd_index if validator_lsd else None))
        print(
            "LSD Fee Recipient Address: ",
            (lsd_fee_recipient_address if validator_lsd else None),
        )
        print("Contains Fee Transaction: ", contains_fee_transaction)
        print("Fee Transaction Hash: ", fee_transaction_hash)
        print("Fee Recipient Compliant: ", fee_recipient_compliant)

        print("------------------------")

        # Add to database
        self.add_or_update_block_monitored(block_fee_recipient_data)

        if validator_lsd:
            self.add_or_update_block_fee_recipient(data)

        return data

    def check_current_block_fee_recipient_compliance(self):
        """
        It checks the current slot and then calls the fee_recipient_compliance function with the current
        slot as an argument
        :return: The return value is a disctionary.
        """
        current_block = self.beacon_chain_service.get_block("head")
        if not current_block:
            return
        current_slot = current_block["slot"]
        return self.fee_recipient_compliance(current_slot)

    def backfill_missing_fee_recipient_compliance(
        self, start_slot=None, end_slot=None, manual=False
    ):
        # Check block monitored database for missing slots
        missing_slots = self.get_missing_slots(start_slot, end_slot)

        existing_run = False
        if manual:
            if missing_slots == []:
                return missing_slots, existing_run
            start_slot = (
                min(missing_slots)
                if start_slot is None
                else max([min(missing_slots), start_slot])
            )
            end_slot = (
                max(missing_slots)
                if end_slot is None
                else min([max(missing_slots), end_slot])
            )
            try:
                with SessionLocal() as session:
                    existing_jobs = (
                        session.query(BackfillJobs)
                        .filter(BackfillJobs.completed == False)
                        .all()
                    )
                    for job in existing_jobs:
                        # Check if the start and end slots are in the range of the existing job
                        exisiting_job_start_slot = int(job.start_slot)
                        exisiting_job_end_slot = int(job.end_slot)
                        print(
                            "Existing job: ",
                            exisiting_job_start_slot,
                            " - ",
                            exisiting_job_end_slot,
                        )
                        if (
                            start_slot >= exisiting_job_start_slot
                            and end_slot <= exisiting_job_end_slot
                        ):
                            existing_run = True
                            break
                        elif (
                            start_slot >= exisiting_job_start_slot
                            and start_slot <= exisiting_job_end_slot
                            and end_slot > exisiting_job_end_slot
                        ):
                            start_slot = exisiting_job_end_slot + 1
                        elif (
                            start_slot < exisiting_job_start_slot
                            and end_slot >= exisiting_job_start_slot
                            and end_slot <= exisiting_job_end_slot
                        ):
                            end_slot = exisiting_job_start_slot - 1
                    print(
                        "Scheduling backfill job for slots: ",
                        start_slot,
                        " - ",
                        end_slot,
                    )
                    Scheduler().add_job(
                        func=FeeRecipientService().backfill_missing_fee_recipient_compliance,
                        id="manual_backfill_" + str(start_slot) + "_" + str(end_slot),
                        args=[start_slot, end_slot],
                    )

                    if not existing_run:
                        add_backfill_job = BackfillJobs(
                            start_slot=start_slot,
                            end_slot=end_slot,
                            completed=False,
                        )
                        session.add(add_backfill_job)
                        session.commit()
                        session.flush()

                return missing_slots, existing_run
            except Exception as e:
                raise Exception("Error scheduling backfill job: ", e)

        if missing_slots:
            print("Checking fee recipient compliance for missed slots: ", missing_slots)

        for slot in missing_slots:
            try:
                self.fee_recipient_compliance(slot)
            except Exception as e:
                print("Backfill Error for slot: ", slot, " - ", e)

        if start_slot and end_slot:
            with SessionLocal() as session:
                backfill_jobs = (
                    session.query(BackfillJobs)
                    .filter(
                        BackfillJobs.start_slot == start_slot,
                        BackfillJobs.end_slot == end_slot,
                    )
                    .all()
                )
                for job in backfill_jobs:
                    job.completed = True
                session.commit()
                session.flush()

    def get_missing_slots(self, start_slot, end_slot):
        """
        It takes a start_slot and end_slot, and returns a list of slots that are missing from the
        database

        :param start_slot: the slot number to start monitoring from
        :param end_slot: the slot number of the last block to be monitored
        """
        with SessionLocal() as session:
            current_block = self.beacon_chain_service.get_block("head")
            if not current_block:
                return []
            if end_slot is None:
                end_slot = int(current_block["slot"])

            if start_slot is None:
                start_slot = end_slot - BACKFILL_SLOT_RANGE

            slots = (
                session.query(BlockMonitored.slot)
                .where(BlockMonitored.slot.between(start_slot, end_slot))
                .all()
            )
            slots = [slot[0] for slot in slots]
            missing_slots = list(set(range(start_slot, end_slot)) - set(slots))
            return missing_slots

    def add_or_update_block_monitored(self, block_monitored_data):
        """
        It inserts a new row into the table if the row doesn't exist, otherwise it does nothing

        :param block_monitored_data: {'slot': '12345'}
        """
        with SessionLocal() as session:
            try:
                block_monitored = (
                    session.query(BlockMonitored)
                    .filter(BlockMonitored.slot == int(block_monitored_data["slot"]))
                    .first()
                )

                if block_monitored:
                    return

                add_block_monitored = insert(BlockMonitored).values(
                    dict(
                        slot=int(block_monitored_data["slot"]),
                        fee_recipient=block_monitored_data["fee_recipient"],
                        validator_index=int(block_monitored_data["validator_index"]),
                        validator_id=block_monitored_data["validator_pubkey"],
                        execution_chain_timestamp=int(
                            block_monitored_data["execution_chain_timestamp"]
                        ),
                        execution_chain_block_hash=block_monitored_data[
                            "execution_chain_block_hash"
                        ],
                        execution_chain_block_number=int(
                            block_monitored_data["execution_chain_block_number"]
                        ),
                        execution_chain_gas_used=int(
                            block_monitored_data["execution_chain_gas_used"]
                        ),
                    )
                )

                add_block_monitored = add_block_monitored.on_duplicate_key_update(
                    fee_recipient=add_block_monitored.inserted.fee_recipient,
                    validator_index=add_block_monitored.inserted.validator_index,
                    validator_id=add_block_monitored.inserted.validator_id,
                    execution_chain_timestamp=add_block_monitored.inserted.execution_chain_timestamp,
                    execution_chain_block_hash=add_block_monitored.inserted.execution_chain_block_hash,
                    execution_chain_block_number=add_block_monitored.inserted.execution_chain_block_number,
                    execution_chain_gas_used=add_block_monitored.inserted.execution_chain_gas_used,
                )

                session.execute(add_block_monitored)
                session.commit()

            except Exception as e:
                print(e)
                session.rollback()
                raise e

            for transaction in block_monitored_data["transactions"]:
                try:
                
                    transaction = insert(BlockTransaction).values(
                        transaction)
                    transaction = transaction.on_duplicate_key_update(
                        slot=transaction.inserted.slot,
                        block_hash=transaction.inserted.block_hash,
                        block_number=transaction.inserted.block_number,
                        to=transaction.inserted.to,
                        sender=transaction.inserted.sender,
                        value=transaction.inserted.value,
                        gas=transaction.inserted.gas,
                    )
                    session.execute(transaction)
                
                except Exception as e:
                    # print(e)
                    # session.rollback()
                    # raise e
                    pass
            session.commit()



    def add_or_update_lsd(self, lsd_data):
        """
        It adds a new row to the LSD table if the id doesn't exist, or updates the row if the id does
        exist

        :param lsd_data:
            {'id': '0x8d8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8b8',
            'ticker': 'LSDB',
            'lsdIndex': 0,
            'feeRecipientAndSyndicate': '0x8d8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8b8f8b8f8b8f8b8b8'}
        """
        with SessionLocal() as session:
            try:
                add_lsd = insert(LSD).values(
                    dict(
                        id=lsd_data["id"],
                        ticker=lsd_data["ticker"],
                        lsd_index=lsd_data["lsdIndex"],
                        fee_recipient_and_syndicate=lsd_data[
                            "feeRecipientAndSyndicate"
                        ],
                    )
                )

                add_lsd = add_lsd.on_duplicate_key_update(
                    ticker=add_lsd.inserted.ticker,
                    lsd_index=add_lsd.inserted.lsd_index,
                    fee_recipient_and_syndicate=add_lsd.inserted.fee_recipient_and_syndicate,
                    updated_datetime=datetime.utcnow(),
                )
                session.execute(add_lsd)
            except Exception as e:
                session.rollback()
                print(e)
                raise
            session.commit()
            session.flush()

    def add_or_update_validator(self, validator_data):
        """
        It adds a new validator to the database if it doesn't exist, or updates the existing validator
        if it does exist

        :param validator_data: {'id': '0x8d8e8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f', 'index': 0,
        'lsd_id': '0x8d8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8f8b8b8b8'}
        """
        with SessionLocal() as session:
            try:
                add_validator = insert(Validator).values(
                    dict(
                        id=validator_data["id"],
                        index=validator_data["index"],
                        lsd_id=validator_data["lsd_id"],
                    )
                )

                add_validator = add_validator.on_duplicate_key_update(
                    lsd_id=add_validator.inserted.lsd_id,
                    updated_datetime=datetime.utcnow(),
                )
                session.execute(add_validator)
            except Exception as e:
                session.rollback()
                print(e)
                raise
            session.commit()
            session.flush()

    def add_or_update_block_fee_recipient(self, fee_recipient_data):
        with SessionLocal() as session:
            self.add_or_update_lsd(
                {
                    "id": fee_recipient_data["lsd_id"],
                    "lsdIndex": fee_recipient_data["lsd_index"],
                    "ticker": fee_recipient_data["lsd_ticker"],
                    "feeRecipientAndSyndicate": fee_recipient_data[
                        "lsd_fee_recipient_address"
                    ],
                }
            )
            self.add_or_update_validator(
                {
                    "id": fee_recipient_data["validator_pubkey"],
                    "index": fee_recipient_data["validator_index"],
                    "lsd_id": fee_recipient_data["lsd_id"],
                }
            )

            try:
                add_block_fee_recipient = insert(FeeRecipientMonitoring).values(
                    dict(
                        slot=fee_recipient_data["slot"],
                        validator_id=fee_recipient_data["validator_pubkey"],
                        lsd_id=fee_recipient_data["lsd_id"],
                        fee_recipient=fee_recipient_data["fee_recipient"],
                        contains_fee_transaction=fee_recipient_data["contains_fee_transaction"],
                        fee_transaction_hash=fee_recipient_data["fee_transaction_hash"],
                        compliant=fee_recipient_data["fee_recipient_compliant"],
                    )
                )

                add_block_fee_recipient = (
                    add_block_fee_recipient.on_duplicate_key_update(
                        validator_id=add_block_fee_recipient.inserted.validator_id,
                        lsd_id=add_block_fee_recipient.inserted.lsd_id,
                        fee_recipient=add_block_fee_recipient.inserted.fee_recipient,
                        contains_fee_transaction=add_block_fee_recipient.inserted.contains_fee_transaction,
                        fee_transaction_hash=add_block_fee_recipient.inserted.fee_transaction_hash,
                        compliant=add_block_fee_recipient.inserted.compliant,
                        updated_datetime=datetime.utcnow(),
                    )
                )
                session.execute(add_block_fee_recipient)
            except Exception as e:
                session.rollback()
                print(e)
                raise

            session.commit()
            session.flush()

    def get_validator_lsd_at_epoch(self, validator_pubkey, epoch):
        """
        It returns the LSD index of a validator for a given epoch

        :param validator_pubkey: The public key of the validator
        :param epoch: The epoch
        :return: The LSD index
        """
        with ETL_SessionLocal() as session:
            validator_lsd_index = (
                session.query(ValidatorLSD)
                .filter(
                    ValidatorLSD.bls_key == str(validator_pubkey),
                    ValidatorLSD.epoch <= int(epoch),
                )
                .order_by(ValidatorLSD.epoch.desc())
                .first()
            )

            if validator_lsd_index:
                print(
                    "Validator LSD Index found: ",
                    validator_lsd_index.indexes,
                    "Validator: ",
                    validator_pubkey,
                    "Slot: ",
                    epoch * 32,
                    "Epoch: ",
                    epoch,
                )
                result = self.lsd_subgraph_service.get_lsds_by_index(
                    [int(validator_lsd_index.indexes)]
                )
                return result
            else:
                return None

    def get_validator_fee_recipient_health(self, validator_pubkey):
        """
        It returns a dictionary with the following keys: compliant_count, non_compliant_count,
        total_blocks_proposed, compliance_score

        :param validator_pubkey: The public key of the validator
        :return: A dictionary
        """
        with SessionLocal() as session:
            validator_fee_recipient_health = (
                session.query(
                    func.count(
                        case(
                            [
                                (
                                    FeeRecipientMonitoring.compliant == False,
                                    FeeRecipientMonitoring.slot,
                                )
                            ]
                        )
                    ).label("non_compliant_count"),
                    func.count(
                        case(
                            [
                                (
                                    FeeRecipientMonitoring.compliant == True,
                                    FeeRecipientMonitoring.slot,
                                )
                            ]
                        )
                    ).label("compliant_count"),
                    func.count(FeeRecipientMonitoring.slot).label("total_count"),
                )
                .filter(FeeRecipientMonitoring.validator_id == validator_pubkey)
                .first()
            )

            result = {
                "compliant_count": validator_fee_recipient_health.compliant_count,
                "non_compliant_count": validator_fee_recipient_health.non_compliant_count,
                "total_blocks_proposed": validator_fee_recipient_health.total_count,
                "compliance_score": (
                    1
                    if validator_fee_recipient_health.total_count == 0
                    else round(
                        validator_fee_recipient_health.compliant_count
                        / validator_fee_recipient_health.total_count,
                        2,
                    )
                ),
            }

            return result

    def get_validator_fee_recipient_health_in_lsd(self, validator_pubkey, lsd_id):
        """
        It returns a dictionary with the following keys: compliant_count, non_compliant_count,
        total_blocks_proposed, compliance_score

        :param validator_pubkey: The public key of the validator
        :param lsd_id: The id of the lsd
        :return: A dictionary
        """
        with SessionLocal() as session:
            validator_fee_recipient_health = (
                session.query(
                    func.count(
                        case(
                            [
                                (
                                    FeeRecipientMonitoring.compliant == False,
                                    FeeRecipientMonitoring.slot,
                                )
                            ]
                        )
                    ).label("non_compliant_count"),
                    func.count(
                        case(
                            [
                                (
                                    FeeRecipientMonitoring.compliant == True,
                                    FeeRecipientMonitoring.slot,
                                )
                            ]
                        )
                    ).label("compliant_count"),
                    func.count(FeeRecipientMonitoring.slot).label("total_count"),
                )
                .filter(FeeRecipientMonitoring.validator_id == validator_pubkey)
                .filter(FeeRecipientMonitoring.lsd_id == lsd_id)
                .first()
            )

            result = {
                "compliant_count": validator_fee_recipient_health.compliant_count,
                "non_compliant_count": validator_fee_recipient_health.non_compliant_count,
                "total_blocks_proposed": validator_fee_recipient_health.total_count,
                "compliance_score": (
                    1
                    if validator_fee_recipient_health.total_count == 0
                    else round(
                        validator_fee_recipient_health.compliant_count
                        / validator_fee_recipient_health.total_count,
                        2,
                    )
                ),
            }

            return result

    def get_lsd_fee_recipient_health(self, lsd_id):
        """
        It returns a dictionary with the following keys: compliant_count, non_compliant_count,
        total_blocks_proposed, compliance_score

        :param lsd_id: The id of the lsd
        :return: A dictionary
        """
        with SessionLocal() as session:
            lsd_fee_recipient_health = (
                session.query(
                    func.count(
                        case(
                            [
                                (
                                    FeeRecipientMonitoring.compliant == False,
                                    FeeRecipientMonitoring.lsd_id,
                                )
                            ]
                        )
                    ).label("non_compliant_count"),
                    func.count(
                        case(
                            [
                                (
                                    FeeRecipientMonitoring.compliant == True,
                                    FeeRecipientMonitoring.lsd_id,
                                )
                            ]
                        )
                    ).label("compliant_count"),
                    func.count(FeeRecipientMonitoring.slot).label("total_count"),
                )
                .filter(FeeRecipientMonitoring.lsd_id == lsd_id)
                .first()
            )

            result = {
                "compliant_count": lsd_fee_recipient_health.compliant_count,
                "non_compliant_count": lsd_fee_recipient_health.non_compliant_count,
                "total_blocks_proposed": lsd_fee_recipient_health.total_count,
                "compliance_score": (
                    1
                    if lsd_fee_recipient_health.total_count == 0
                    else round(
                        lsd_fee_recipient_health.compliant_count
                        / lsd_fee_recipient_health.total_count,
                        2,
                    )
                ),
            }

            return result

    def get_all_validators_fee_recipient_health_in_lsd(self, lsd_id):
        """
        Returns a list of validator fee recipient health in a given lsd
        """

        validators_in_lsd = LSDSubgraphService().get_validators_in_lsd(lsd_id)

        validator_ids = [validator["id"] for validator in validators_in_lsd]

        known_validator_results = defaultdict(dict)

        validator_ids = []
        for validator in validators_in_lsd:
            validator_ids.append(validator["id"])
            known_validator_results[validator["id"]]["validator_id"] = validator["id"]
            known_validator_results[validator["id"]]["compliant_count"] = 0
            known_validator_results[validator["id"]]["non_compliant_count"] = 0
            known_validator_results[validator["id"]]["total_blocks_proposed"] = 0
            known_validator_results[validator["id"]]["compliance_score"] = 1

        with SessionLocal() as session:
            data = (
                session.query(
                    FeeRecipientMonitoring.validator_id,
                    func.count(
                        case(
                            [
                                (
                                    FeeRecipientMonitoring.compliant == False,
                                    FeeRecipientMonitoring.slot,
                                )
                            ]
                        )
                    ).label("non_compliant_count"),
                    func.count(
                        case(
                            [
                                (
                                    FeeRecipientMonitoring.compliant == True,
                                    FeeRecipientMonitoring.slot,
                                )
                            ]
                        )
                    ).label("compliant_count"),
                    func.count(FeeRecipientMonitoring.slot).label("total_count"),
                )
                .filter(FeeRecipientMonitoring.lsd_id == lsd_id)
                .filter(FeeRecipientMonitoring.validator_id.in_(validator_ids))
                .group_by(FeeRecipientMonitoring.validator_id)
                .all()
            )

            for data_item in data:
                if data_item.validator_id in known_validator_results:
                    known_validator_results[data_item.validator_id][
                        "non_compliant_count"
                    ] = data_item.non_compliant_count
                    known_validator_results[data_item.validator_id][
                        "compliant_count"
                    ] = data_item.compliant_count
                    known_validator_results[data_item.validator_id][
                        "total_blocks_proposed"
                    ] = data_item.total_count
                    known_validator_results[data_item.validator_id][
                        "compliance_score"
                    ] = (
                        1
                        if data_item.total_count == 0
                        else round(data_item.compliant_count / data_item.total_count, 2)
                    )

            return list(known_validator_results.values())

    def get_lsd_fee_recipient_compliance_history(self, lsd_id):
        """
        Returns a list of fee recipient compliance history for a given lsd
        """
        with SessionLocal() as session:
            data = (
                session.query(
                    FeeRecipientMonitoring.slot,
                    FeeRecipientMonitoring.compliant,
                    FeeRecipientMonitoring.validator_id,
                    FeeRecipientMonitoring.lsd_id,
                    FeeRecipientMonitoring.fee_recipient,
                    LSD.fee_recipient_and_syndicate,
                )
                .join(LSD, LSD.id == FeeRecipientMonitoring.lsd_id)
                .filter(FeeRecipientMonitoring.lsd_id == lsd_id)
                .order_by(FeeRecipientMonitoring.slot.desc())
                .all()
            )

            result = []
            for data_item in data:
                result.append(
                    {
                        "slot": data_item.slot,
                        "compliant": data_item.compliant,
                        "validator_pubkey": data_item.validator_id,
                        "lsd_id": data_item.lsd_id,
                        "fee_recipient": data_item.fee_recipient,
                        "lsd_fee_recipient": data_item.fee_recipient_and_syndicate,
                    }
                )

            return result

    def get_all_validators_fee_recipient_health(self, start_date, end_date):
        """
        Returns a disctionary of validator fee recipient health for all validators
        across all lsd, also includes the count of compliant and non compliant validators
        in the given time period
        """

        start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

        all_validators = LSDSubgraphService().get_all_validators()
        validator_ids = [validator["id"] for validator in all_validators]

        with SessionLocal() as session:
            data = (
                session.query(
                    FeeRecipientMonitoring.validator_id,
                    func.count(
                        case(
                            [
                                (
                                    FeeRecipientMonitoring.compliant == False,
                                    FeeRecipientMonitoring.slot,
                                )
                            ]
                        )
                    ).label("non_compliant_count"),
                    func.count(
                        case(
                            [
                                (
                                    FeeRecipientMonitoring.compliant == True,
                                    FeeRecipientMonitoring.slot,
                                )
                            ]
                        )
                    ).label("compliant_count"),
                    func.count(FeeRecipientMonitoring.slot).label("total_count"),
                )
                .join(
                    BlockMonitored, BlockMonitored.slot == FeeRecipientMonitoring.slot
                )
                .filter(
                    BlockMonitored.execution_chain_timestamp >= start_date.timestamp()
                )
                .filter(
                    BlockMonitored.execution_chain_timestamp <= end_date.timestamp()
                )
                .filter(FeeRecipientMonitoring.validator_id.in_(validator_ids))
                .group_by(FeeRecipientMonitoring.validator_id)
                .all()
            )

            print(data)

            result = []
            for data_item in data:
                result.append(
                    {
                        "validator_id": data_item.validator_id,
                        "non_compliant_count": data_item.non_compliant_count,
                        "compliant_count": data_item.compliant_count,
                        "total_blocks_proposed": data_item.total_count,
                        "compliance_score": (
                            1
                            if data_item.total_count == 0
                            else round(
                                data_item.compliant_count / data_item.total_count, 2
                            )
                        ),
                    }
                )

            network_overview = {
                "total_validators": len(validator_ids),
                "compliant_validators": len(validator_ids)
                - len([x for x in result if x["compliance_score"] < 1]),
                "non_compliant_validators": len(
                    [x for x in result if x["compliance_score"] < 1]
                ),
                "network_compliance_score": (
                    len(validator_ids)
                    - len([x for x in result if x["compliance_score"] < 1])
                )
                / len(validator_ids),
                "start_date": start_date,
                "end_date": end_date,
                "data": result,
            }

            return network_overview

    def get_all_validators_fee_recipient_health_details(
        self, start_date, end_date, time_divisions
    ):
        """
        Returns a dictionary of validator fee recipient health for all validators
        across all lsd. This data is divided into time divisions, with a compliance score
        for each time division
        """

        start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

        # Calculate the length of each time division
        time_delta = (end_date - start_date) / time_divisions

        # Get all validators, so only validators that are not banned from the network are included
        all_validators = LSDSubgraphService().get_all_validators()
        validator_ids = [validator["id"] for validator in all_validators]

        # Create a list of time divisions with an initial count of zero for each division
        time_divisions_list = [
            {
                "time_division_start_datetime": start_date + (i * time_delta),
                "non_compliant_count": 0,
                "compliant_count": 0,
                "total_count": 0,
            }
            for i in range(time_divisions)
        ]

        with SessionLocal() as session:
            data = (
                session.query(
                    func.floor(
                        (
                            BlockMonitored.execution_chain_timestamp
                            - func.unix_timestamp(start_date)
                        )
                        / time_delta.total_seconds()
                    ).label("time_division"),
                    func.count(
                        case(
                            [
                                (
                                    FeeRecipientMonitoring.compliant == False,
                                    FeeRecipientMonitoring.slot,
                                )
                            ]
                        )
                    ).label("non_compliant_count"),
                    func.count(
                        case(
                            [
                                (
                                    FeeRecipientMonitoring.compliant == True,
                                    FeeRecipientMonitoring.slot,
                                )
                            ]
                        )
                    ).label("compliant_count"),
                    func.count(FeeRecipientMonitoring.slot).label("total_count"),
                )
                .join(
                    BlockMonitored, BlockMonitored.slot == FeeRecipientMonitoring.slot
                )
                .filter(
                    BlockMonitored.execution_chain_timestamp >= start_date.timestamp()
                )
                .filter(
                    BlockMonitored.execution_chain_timestamp <= end_date.timestamp()
                )
                .filter(FeeRecipientMonitoring.validator_id.in_(validator_ids))
                .group_by("time_division")
                .all()
            )

            print(data)

            # Iterate through the data and add to the count of the appropriate time division
            for data_item in data:
                time_division_index = int(data_item[0])
                time_divisions_list[time_division_index][
                    "non_compliant_count"
                ] += data_item.non_compliant_count
                time_divisions_list[time_division_index][
                    "compliant_count"
                ] += data_item.compliant_count
                time_divisions_list[time_division_index][
                    "total_count"
                ] += data_item.total_count

            result = []
            for time_division in time_divisions_list:
                # Calculate the compliance score for each time division
                compliance_score = (
                    1
                    if time_division["total_count"] == 0
                    else round(
                        time_division["compliant_count"] / time_division["total_count"],
                        2,
                    )
                )
                result.append(
                    {
                        "time_division_start_datetime": time_division[
                            "time_division_start_datetime"
                        ],
                        "non_compliant_count": time_division["non_compliant_count"],
                        "compliant_count": time_division["compliant_count"],
                        "total_blocks_proposed": time_division["total_count"],
                        "compliance_score": compliance_score,
                    }
                )

            network_overview = {
                "time_division_length_seconds": time_delta,
                "time_division_as_string": str(time_delta),
                "start_date": start_date,
                "end_date": end_date,
                "total_blocks_proposed": sum(
                    [x["total_blocks_proposed"] for x in result]
                ),
                "total_compliant_blocks_proposed": sum(
                    [x["compliant_count"] for x in result]
                ),
                "total_non_compliant_blocks_proposed": sum(
                    [x["non_compliant_count"] for x in result]
                ),
                "data": result,
            }

            return network_overview
