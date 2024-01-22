import os


# api.cfG path
API_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TEMPLATES_DIR = os.path.join(API_DIR, 'templates')
API_CFG_FILE_NAME = 'api.cfg'
PATH_TO_API_CFG = os.path.join(API_DIR, API_CFG_FILE_NAME)

SLOT_TIME = 12  # Number of seconds in a slot
EPOCH_SLOTS = 32  # Number of slots in an epoch
EPOCH_TIME = EPOCH_SLOTS * SLOT_TIME  # Number of seconds in an epoch

GENESIS_SLOT = 4000000  # Slot number of the genesis block
BACKFILL_SLOT_RANGE = 7200 # Number of slots in 24hrs
