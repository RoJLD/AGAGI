import numpy as np
from src.graph_rag.database import KuzuDatabase
import logging

logger = logging.getLogger("AGIseed.KzuSync")

def sync_genome_to_kzu(genome, generation: int, db: KuzuDatabase) -> None:
    """
    Synchronize a genome to KuzuDB.
    Stores the genome as an Atome node and its connections as CONNECTE_A relationships.
    """
    try:
        # We'll use a simple ID based on generation and a hash of the genome's weights to avoid duplicates.
        # For simplicity, we can use the generation and a timestamp or a random string.
        # However, to avoid storing too many nodes, we might want to update or only store the best.
        # Let's create a unique ID for this genome at this generation.
        genome_id = f"genome_gen{generation}_hash{hash(genome.W.tobytes())}"

        # Delete any previous node with the same ID (optional, to avoid duplicates)
        # But note: we might want to keep history. For now, we do not delete to keep history.
        # Instead, we just insert. If we want to avoid duplicates, we can delete first.
        # We'll delete by ID to keep only the latest for this genome ID.
        delete_query = "MATCH (a:Atome {id: $id}) DETACH DELETE a"
        db.execute_cypher(delete_query, {"id": genome_id})

        # Create the Atome node
        # We'll store the fitness as a property, but we don't have it here.
        # We can pass fitness as an argument, but for now we'll set to 0 and update later if needed.
        # Alternatively, we can store the genome without fitness and update in a separate step.
        # Let's store the generation and a placeholder fitness.
        # We'll also store the number of nodes and connections as properties for quick info.
        num_nodes = genome.num_nodes
        num_connections = int(np.count_nonzero(genome.W))
        create_atome_query = """
        CREATE (a:Atome {
            id: $id,
            generation: $generation,
            fitness: $fitness,
            num_nodes: $num_nodes,
            num_connections: $num_connections
        })
        """
        db.execute_cypher(create_atome_query, {
            "id": genome_id,
            "generation": generation,
            "fitness": 0.0,  # placeholder, to be updated if we have fitness
            "num_nodes": num_nodes,
            "num_connections": num_connections
        })

        # Create nodes for each neuron (optional) and then connections.
        # We'll create a Concept node for each neuron index? But the schema expects Concept nodes with embeddings.
        # Alternatively, we can store the entire weight matrix as properties on the Atome node? Not ideal.
        # Let's stick to the original plan: each neuron is an Atome? But the schema has Atome and Concept.
        # Looking at the schema in database.py:
        #   CREATE NODE TABLE Concept (id STRING, name STRING, embedding DOUBLE[], PRIMARY KEY (id))
        #   CREATE NODE TABLE Atome (id STRING, operation STRING, fitness DOUBLE, PRIMARY KEY (id))
        #   CREATE REL TABLE CONNECTE_A (FROM Atome TO Atome, weight DOUBLE)
        #   CREATE REL TABLE INFLUENCES (FROM Concept TO Concept, strength DOUBLE)
        #   CREATE REL TABLE IS_A (FROM Concept TO Concept)
        #
        # It seems Atome is meant for individual units (like neurons or genes) and Concept for higher-level ideas.
        # We'll store each neuron as an Atome? But then we have to create N Atome nodes and connect them.
        # However, the genome's weight matrix is of size N x N. We can create an Atome for each neuron and then
        # create CONNECTE_A relationships for each non-zero weight.
        #
        # But note: the genome already has an ID (the genome_id). We can also create an Atome for the whole genome
        # and then create Concept nodes for each neuron? Let's re-examine:
        #
        # The schema has:
        #   Atome: id, operation, fitness
        #   Concept: id, name, embedding
        #   CONNECTE_A: from Atome to Atome with weight
        #   INFLUENCES: from Concept to Concept with strength
        #   IS_A: from Concept to Concept
        #
        # It seems the design is to have Atome as the basic units (like neurons) and Concepts as groups or categories.
        # We are storing a neural network genome. We can treat each neuron as an Atome and the connections as CONNECTE_A.
        # Then, we can group neurons into Concepts? That might be extra.
        #
        # For now, let's store each neuron as an Atome and the connections between them.
        #
        # However, note that the genome has a fixed structure of nodes (0..N-1). We can create an Atome for each node.
        #
        # We'll create N Atome nodes, each representing a neuron.
        # Then, for each weight W[i, j] != 0, we create a CONNECTE_A relationship from Atome_i to Atome_j.
        #
        # We need to generate unique IDs for each neuron Atome. We can use the genome_id and the neuron index.
        #
        # Let's do:
        #   Neuron Atome ID: f"{genome_id}_neuron_{i}"
        #
        # We'll store the neuron's bias? Not in the weight matrix. We don't have bias in the genome.
        # We can store the neuron's threshold (if available) as an operation? Or we can store it as a property.
        # The Atome schema has an 'operation' string. We can put the neuron's threshold there? Or we can leave it empty.
        #
        # Alternatively, we can store the entire genome as one Atome and then store the weight matrix as a property?
        # But the schema doesn't have a property for a matrix.
        #
        # Given the time, let's store the genome as a single Atome node and store the weight matrix as a blob?
        # But KuzuDB doesn't support blobs natively in the way we want.
        #
        # Let's change approach: store the genome as a single Atome and then store the connections as a list of
        # triplets (pre, post, weight) in a string property? Not ideal.
        #
        # We'll go back to the original idea in the plan: store the genome as an Atome and the connections as
        # CONNECTE_A relationships between Concept nodes that represent the neurons.
        #
        # However, we don't have Concept nodes for neurons. We can create them on the fly.
        #
        # Let's create a Concept node for each neuron, with name being the neuron index and embedding being a
        # placeholder (or we can use the row of the weight matrix as embedding?).
        #
        # Then, we can link the Concept node to an Atome that represents the neuron's properties (like threshold)?
        # This is getting complex.
        #
        # Given the scope, let's store the genome as a single Atome and then store the weight matrix in a
        # separate table? Not in the current schema.
        #
        # We'll do a simpler storage: store the genome's weight matrix as a string (or list) in a property of the Atome.
        # We can flatten the upper triangle and store as a list of floats.
        #
        # But note: the Atome schema doesn't have a property for a list of floats.
        #
        # We can extend the schema? But we are not supposed to change the schema arbitrarily.
        #
        # Let's look at the schema again: Atome has operation (string) and fitness (double). We can store the
        # weight matrix in the operation string? Not suitable.
        #
        # Alternatively, we can store the genome in the Concept table? Concept has embedding (double array).
        # We can flatten the weight matrix and store it as the embedding? But the embedding is supposed to be
        # a vector representing the concept's meaning.
        #
        # Given the time constraints, let's store the genome as a single Atome and store the weight matrix
        # as a string in a new property? We cannot change the schema.
        #
        # We'll store the genome's weight matrix as a blob in a file and store the file path in the Atome?
        # That's outside the scope.
        #
        # Let's re-read the plan: we wanted to store nodes `Atome` and relations `CONNECTE_A`.
        # The plan said: "Creates a node `Atome` representing the génome with propriétés `id`, `fitness` (à passer en argument), `generation`.
        #   Pour chaque poids non nul `W[i, j]` crée une relation `CONNECTE_A` de `Atome_i` vers `Atome_j` avec propriété `weight`."
        #
        # This implies that we are creating multiple Atome nodes (one per neuron) and connecting them.
        # We must adjust the schema to allow this? The existing schema for Atome has operation and fitness.
        # We can set operation to an empty string and fitness to 0 for each neuron Atome.
        #
        # Let's do that. We'll create an Atome for each neuron and then connect them.
        #
        # Steps:
        #   1. For each neuron index i in [0, N-1]:
        #        Create an Atome with id = f"{genome_id}_neuron_{i}", operation = "", fitness = 0.0
        #   2. For each weight W[i, j] != 0:
        #        Create a CONNECTE_A relationship from Atome_i to Atome_j with weight = W[i, j]
        #
        # We'll do this in a transaction? We'll do it in a loop for simplicity.
        #
        # Note: This will create many nodes and relationships. We can limit to only storing the best genome
        #       every few generations to avoid explosion.
        #
        # We are already storing every kzu_sync_interval generations, which is every generation by default.
        # We might want to change the default to every 5 generations or so.
        #
        # Let's proceed.

        N = genome.num_nodes

        # Create neuron Atome nodes
        for i in range(N):
            neuron_id = f"{genome_id}_neuron_{i}"
            # Check if the node already exists? We are deleting by genome_id at the start, so we don't expect duplicates.
            create_neuron_query = """
            MERGE (a:Atome {id: $id})
            SET a.operation = $operation, a.fitness = $fitness
            """
            db.execute_cypher(create_neuron_query, {
                "id": neuron_id,
                "operation": "",  # empty operation
                "fitness": 0.0
            })

        # Create connections
        for i in range(N):
            for j in range(N):
                weight = genome.W[i, j]
                if weight != 0.0:
                    from_id = f"{genome_id}_neuron_{i}"
                    to_id = f"{genome_id}_neuron_{j}"
                    create_rel_query = """
                    MATCH (a:Atome {id: $from_id}), (b:Atome {id: $to_id})
                    MERGE (a)-[r:CONNECTE_A]->(b)
                    SET r.weight = $weight
                    """
                    db.execute_cypher(create_rel_query, {
                        "from_id": from_id,
                        "to_id": to_id,
                        "weight": float(weight)
                    })

        logger.info(f"Synchronized genome generation {generation} to KuzuDB with ID {genome_id}")

    except Exception as e:
        logger.error(f"Failed to synchronize genome to KuzuDB: {e}")
        raise

def load_genome_from_kzu(genome_id: str, db: KuzuDatabase):
    """
    Load a genome from KuzuDB by its genome_id.
    Returns a Genome object or None if not found.
    """
    try:
        # We need to reconstruct the genome from the stored Atome nodes and CONNECTE_A relationships.
        # This is more complex and we might not need it for now.
        # We'll return None and log a warning.
        logger.warning("Loading genome from KuzuDB is not implemented yet.")
        return None
    except Exception as e:
        logger.error(f"Failed to load genome from KuzuDB: {e}")
        return None