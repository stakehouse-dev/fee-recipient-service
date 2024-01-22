import multiprocessing
from services.data.beacon_chain_service import BeaconChainService
from configuration.database_configuration import SessionLocal
from api import app
from services.scheduler.scheduler_service import Scheduler
from services.fee_recipient.fee_recipient_service import FeeRecipientService
from common.constants import SLOT_TIME


class BeaconChainEventService:
    def __init__(self):
        self.beacon_chain_service = BeaconChainService()
        self.session = SessionLocal()

    def head_subscription(self):
        client = self.beacon_chain_service.subscribe_to_beacon_chain_events("head")
        if not client.connected:
            print("Failed to connect to server")
            return None
        return client

    def monitor_beacon_chain_head_events(self):
        client = self.head_subscription()
        if client is not None:
            print("Subscribed to beacon chain events using SSE")
            multiprocessing.Process(
                target=BeaconChainEventService().monitoring_loop, args=(client,)
            ).start()
            return True
        else:
            print("Error subscribing to beacon chain events")
            return False

    def monitoring_loop(self, sse_client):
        for event in sse_client.events():
            print(event)
            FeeRecipientService().fee_recipient_compliance(event.data["data"]["slot"])


@app.on_event("startup")
def listen_to_beacon_chain_events():
    print("Starting to listen to beacon chain events")

    scheduler = Scheduler()

    # if not BeaconChainEventService().monitor_beacon_chain_head_events():
        # print(
        #     "Failed to start monitoring beacon chain events by SSE, using polling instead"
        # )
    try:
        scheduler.add_job(
            func=FeeRecipientService().check_current_block_fee_recipient_compliance,
            trigger="interval",
            id="fee_recipient_compliance",
            seconds=SLOT_TIME,
            replace_existing=True,
        )
    except Exception:
        print("Failed to start monitoring beacon chain events by polling")
        exit(1)

    # Backfill missing fee recipient compliance every day at 00:00
    scheduler.add_job(
        func=FeeRecipientService().backfill_missing_fee_recipient_compliance,
        id="backfill_missing_fee_recipient_compliance",
        trigger="cron",
        hour=0,
        minute=0,
        replace_existing=True,
    )
