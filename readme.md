Fee Recipient Monitoring
========================

Table of Contents
-----------------

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Endpoints](#endpoints)
- [How It Works](#how-it-works)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

Introduction
------------

Fee Recipient Monitoring is an application that provides monitoring capabilities for block reward payouts to validators. It serves as a companion to the Blockswap Stakehouse ecosystem, allowing for transparency of payouts to validators within LSD networks for liquidity-sensitive activities.

Prerequisites
-------------

Ensure that you have the necessary prerequisites before setting up Fee Recipient Monitoring:

- Python 3.6+
- SQL Database (PostgreSQL, MySQL, etc.)
- Beacon Node and Beacon Node API Key (if required)
- Subgraph URL for Stakehouse and LSD (defaults to https://api.thegraph.com/subgraphs/name/bsn-eng/liquid-staking-derivative)
- LSD ETL DB connection info (Requires access to Validators table in order to query historical existence of validators in LSD networks)

Installation
------------

Install the required packages for Fee Recipient Monitoring:

```shell
pip install -r requirements.txt
```

### To run

1. Create a virtual environment:

    ```shell
    python3 -m venv .venv
    ```

2. Activate the virtual environment:

    - On Windows:

        ```shell
        .venv\Scripts\activate
        ```

    - On macOS/Linux:

        ```shell
        source .venv/bin/activate
        ```

3. Set Archive Node API Key in your environment:

```shell
    export BEACON_NODE_API_KEY=your_api_key
```

4. Install requirements:

```shell
    pip install -r requirements.txt
```

5. Run FastAPI:

```shell
    python run_api.py
```

6. Access Available Endpoints:

    <http://localhost:7000/docs>

Endpoints
---------

Fee Recipient Monitoring by default the FastAPI server runs on `localhost:7000`, which can be changed in `run_api.py`. This server exposes several endpoints to interact with the application. These endpoints include:

- **api**: Main API for interacting with Fee Recipient Monitoring, and trigger manual backfilling jobs if necessary.
- **lsd_fee_recipient**: Monitoring for LSD networks with specificity. To retrieve historical compliance data, validator complicance data within a specific lsd network, or validator compliance data for a specific LSD, retrieve LSD syndicate addresses from Stakehouse's monitoring databases, and view general compliance health for a specific LSD.
- **validator_fee_recipient**: Monitoring for fee recipients specific to validators across their lifespan in any and all LSD networks. To retrieve historical compliance data, validator complicance data across all LSD networks it has historically participated in, or validator compliance data for a specific LSD, retrieve validator fee compliance helath and most recent blocks proposed by the validator.

These endpoints provide the necessary functionality to monitor and analyze fee recipients within the application.

How It Works
---------

The code monitors blockchain activity, checking for new blocks at each slot interval using either an advanced Python scheduler or by subscribing to the node's head event. Upon a new block event, it retrieves block information, focusing on the fee recipient and the proposing validator.

Validator compliance is verified against known validators in Liquid Staking Derivative (LSD) networks through queries to Stakehouse and LSD subgraphs. For a proposed block, the code obtains the LSD syndicate address of the proposer from Stakehouse's monitoring databases.

The obtained syndicate address is compared against the block's fee recipient for compliance. Mismatches trigger the unpacking of block contents and decoding of transactions. The code looks for a fee payment transaction to the syndicate, typically the last transaction. If no such transaction is found, and block rewards aren't set for the LSD syndicate address, it signifies proposer non-compliance.

Compliance data for each slot is stored in a configured SQL database. A scheduler runs periodic backfilling jobs to address any missed slots, ensuring comprehensive monitoring and storage of compliance data.

Usage
-----

Fee Recipient Monitoring allows seamless integration with multiple beacon nodes and validators. To configure and deploy Fee Recipient Monitoring within your local network, refer to `api.cfg` for configuration options.

Contributing
------------

We welcome contributions to Fee Recipient Monitoring. If you'd like to contribute, please follow these guidelines:

1. Fork the project.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them with clear and concise messages.
4. Push your changes to your fork.
5. Create a pull request to the main repository.

License
-------

This project is licensed under MIT - see the [LICENSE.md](LICENSE.md) file for details.
