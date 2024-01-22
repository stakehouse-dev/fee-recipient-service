import requests
import sseclient
from apiconfig import APIConfig


class BeaconChainService:
    def __init__(self):
        self._config = APIConfig()
        self.eth2_url = self._config.get_beacon_node_url()
        self.headers = {"Content-Type": "application/json",
                        "x-api-key": self._config.get_beacon_node_api_key()}

    def get_block(self, slot):
        url = self.eth2_url + "/eth/v2/beacon/blocks/" + str(slot)
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()["data"]["message"]
        else:
            return None

    def get_validator(self, slot, validator_index):
        url = self.eth2_url + "/eth/v1/beacon/states/" + \
            str(slot) + "/validators/" + str(validator_index)
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()["data"]["validator"]
        else:
            return None
    
    def subscribe_to_beacon_chain_events(self, topic):
        print("Subscribing to beacon chain event:", topic)
        url = self.eth2_url + "/eth/v1/events?topics=" + topic
        headers = self.headers
        client = sseclient.SSEClient(url, headers=headers)
        print(client)
        return client

