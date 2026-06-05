import kuzu
import logging
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

logger = logging.getLogger("AGIseed.KuzuDB")
logging.basicConfig(level=logging.INFO)

class DatabaseConfig(BaseModel):
    db_path: str = "./data/kuzudb/kuzu.db"
    buffer_pool_size: int = 1024 * 1024 * 1024 # 1GB
    
class KuzuDatabase:
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        
        # Ensure parent directory exists
        Path(self.config.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initializing KuzuDB at {self.config.db_path}")
        self.db = kuzu.Database(self.config.db_path, buffer_pool_size=self.config.buffer_pool_size)
        self.conn = kuzu.Connection(self.db)
        
    def bootstrap_schema(self):
        """Initializes the base schema for AGIseed if it doesn't exist."""
        logger.info("Bootstrapping KuzuDB Schema...")
        
        # Define schemas
        tables = [
            "CREATE NODE TABLE Concept (id STRING, name STRING, embedding DOUBLE[], PRIMARY KEY (id))",
            "CREATE NODE TABLE Atome (id STRING, operation STRING, fitness DOUBLE, PRIMARY KEY (id))",
            "CREATE REL TABLE CONNECTE_A (FROM Atome TO Atome, weight DOUBLE)",
            "CREATE REL TABLE INFLUENCES (FROM Concept TO Concept, strength DOUBLE)",
            "CREATE REL TABLE IS_A (FROM Concept TO Concept)",
        ]
        
        for query in tables:
            try:
                self.conn.execute(query)
                logger.info(f"Executed schema query successfully: {query.split('(')[0]}")
            except RuntimeError as e:
                # Catch "already exists" errors to make bootstrap idempotent
                if "already exists" not in str(e).lower():
                    logger.error(f"Error executing schema query: {e}")
                    raise
                    
    def execute_cypher(self, query: str, parameters: dict = None) -> list:
        """Executes a Cypher query and returns the results as a list."""
        logger.debug(f"Executing Cypher: {query}")
        try:
            results = self.conn.execute(query, parameters or {})
            
            output = []
            while results.has_next():
                output.append(results.get_next())
            return output
        except Exception as e:
            logger.error(f"Cypher Query Failed: {e}")
            raise
