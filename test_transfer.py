import os
import sys

# Set environment variables for the test
os.environ["WORLD_TYPE"] = "agricultural"
os.environ["IMPORT_AGENT_ID"] = "f44c2a61"
os.environ["KEEP_MEMORY"] = "1"

# We just want to see if the first era starts and imports correctly, then we can exit.
# To do this cleanly without modifying main_biosphere heavily, we can run it and kill it after 10 seconds.
# But it's easier to just run the import function directly and assert.

from src.graph_rag.async_logger import logger
from main_biosphere import init_primordial_soup

logger.start()
import time
time.sleep(2)
shared_db = logger.get_db()

try:
    print(f"Testing import for {os.environ['IMPORT_AGENT_ID']}...")
    genomes, ntm = init_primordial_soup(num_agents=5, import_agent_id=os.environ['IMPORT_AGENT_ID'], keep_memory=True, shared_db=shared_db)
    if genomes and len(genomes) == 5:
        print("OK: Transfert reussi ! Les genomes ont ete generes a partir du Connectome KuzuDB.")
        if ntm is not None:
            print("OK: Memoire NTM importee avec succes !")
    else:
        print("FAIL: Echec du transfert.")
finally:
    logger.stop()
