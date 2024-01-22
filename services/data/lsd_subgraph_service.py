import requests
import json
from apiconfig import APIConfig


class LSDSubgraphService:
    def __init__(self):
        self._config = APIConfig()
        self.lsd_subgraph_url = self._config.get_lsd_subgraph_url()

    def get_validator_lsds(self, validator_pubkey):
        query = """
      {{
        lsdvalidators (where: {{ id: "{}" }}) {{
          id
          status
          liquidStakingManager
          currentIndex
          registerInitialsBlockNumber
          ethSentToDepositContractBlockNumber
        }}
      }}
      """.format(
            validator_pubkey
        )
        response = requests.post(self.lsd_subgraph_url, json={"query": query})
        result = response.json()
        return result.get("data", {}).get("lsdvalidators", [])
    
    def get_validators_in_lsd(self, lsd_id):
        query = """
      {{
        lsdvalidators (where: {{ 
          liquidStakingManager: "{}"
          status_not: "BANNED"
          }}) {{
          id
          status
          liquidStakingManager
          currentIndex
          registerInitialsBlockNumber
          ethSentToDepositContractBlockNumber
        }}
      }}
      """.format(
            lsd_id
        )
        response = requests.post(self.lsd_subgraph_url, json={"query": query})
        result = response.json()
        return result.get("data", {}).get("lsdvalidators", [])
      
    def get_all_validators(self):
        query = """
      {
        lsdvalidators (where: { status_not: "BANNED"}) {
          id
          status
          liquidStakingManager
          currentIndex
          registerInitialsBlockNumber
          ethSentToDepositContractBlockNumber
        }
      }
      """
        response = requests.post(self.lsd_subgraph_url, json={"query": query})
        result = response.json()
        return result.get("data", {}).get("lsdvalidators", [])

    def get_lsds(self, lsd_ids: list):
        query = """
      {{
        liquidStakingNetworks (where: {{ id_in: {} }}) {{
          id
          ticker
          lsdIndex
          numberOfStakedValidators
          numberOfValidatorsBeingPrepared
          feeRecipientAndSyndicate
        }}
      }}
      """.format(
            json.dumps(lsd_ids)
        )
        response = requests.post(self.lsd_subgraph_url, json={"query": query})
        result = response.json()
        return result.get("data", {}).get("liquidStakingNetworks", [])
    
    def get_lsds_by_index(self, lsd_indexes: list):
        query = """
      {{
        liquidStakingNetworks (where: {{ lsdIndex_in: {} }}) {{
          id
          ticker
          lsdIndex
          numberOfStakedValidators
          numberOfValidatorsBeingPrepared
          feeRecipientAndSyndicate
        }}
      }}
      """.format(
            json.dumps(lsd_indexes)
        )
        response = requests.post(self.lsd_subgraph_url, json={"query": query})
        result = response.json()
        return result.get("data", {}).get("liquidStakingNetworks", [])
