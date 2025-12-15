from neo4j import GraphDatabase
import uuid
import logging
from app.utils import neo4j_to_python

logger = logging.getLogger(__name__)

class Neo4jService:
    """Service for Neo4j database operations"""
    
    def __init__(self, uri, user, password):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self._init_driver()
    
    def _init_driver(self):
        """Initialize Neo4j driver"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            logger.info("Neo4j driver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {e}")
            raise
    
    def close(self):
        """Close Neo4j driver"""
        if self.driver:
            self.driver.close()
    
    def init_database_constraints(self, max_retries=30, retry_delay=2):
        """Initialize database constraints and indexes with retry logic"""
        import time
        
        for attempt in range(max_retries):
            try:
                with self.driver.session() as session:
                    # Test connection
                    session.run("RETURN 1")
                    
                    # Create unique constraints
                    constraints = [
                        "CREATE CONSTRAINT building_id IF NOT EXISTS FOR (n:Building) REQUIRE n.id IS UNIQUE",
                        "CREATE CONSTRAINT floor_id IF NOT EXISTS FOR (n:Floor) REQUIRE n.id IS UNIQUE",
                        "CREATE CONSTRAINT apartment_id IF NOT EXISTS FOR (n:Apartment) REQUIRE n.id IS UNIQUE",
                        "CREATE CONSTRAINT meter_id IF NOT EXISTS FOR (n:Meter) REQUIRE n.id IS UNIQUE",
                        "CREATE CONSTRAINT distribution_id IF NOT EXISTS FOR (n:Distribution) REQUIRE n.id IS UNIQUE",
                        "CREATE CONSTRAINT consumer_id IF NOT EXISTS FOR (n:Consumer) REQUIRE n.id IS UNIQUE",
                        "CREATE CONSTRAINT tree_id IF NOT EXISTS FOR (n:MeteringTree) REQUIRE n.id IS UNIQUE"
                    ]
                    
                    for constraint in constraints:
                        session.run(constraint)
                    
                    # Create indexes for name searches and project filtering
                    indexes = [
                        "CREATE INDEX meter_name IF NOT EXISTS FOR (n:Meter) ON (n.name)",
                        "CREATE INDEX distribution_name IF NOT EXISTS FOR (n:Distribution) ON (n.name)",
                        "CREATE INDEX consumer_name IF NOT EXISTS FOR (n:Consumer) ON (n.name)",
                        "CREATE INDEX tree_project_id IF NOT EXISTS FOR (n:MeteringTree) ON (n.project_id)",
                        "CREATE INDEX building_project_id IF NOT EXISTS FOR (n:Building) ON (n.project_id)",
                        "CREATE INDEX floor_project_id IF NOT EXISTS FOR (n:Floor) ON (n.project_id)",
                        "CREATE INDEX apartment_project_id IF NOT EXISTS FOR (n:Apartment) ON (n.project_id)",
                        "CREATE INDEX meter_project_id IF NOT EXISTS FOR (n:Meter) ON (n.project_id)",
                        "CREATE INDEX distribution_project_id IF NOT EXISTS FOR (n:Distribution) ON (n.project_id)",
                        "CREATE INDEX consumer_project_id IF NOT EXISTS FOR (n:Consumer) ON (n.project_id)",
                        # Utility type indexes
                        "CREATE INDEX meter_utility IF NOT EXISTS FOR (n:Meter) ON (n.utility_type)",
                        "CREATE INDEX distribution_utility IF NOT EXISTS FOR (n:Distribution) ON (n.utility_type)",
                        "CREATE INDEX building_utility IF NOT EXISTS FOR (n:Building) ON (n.utility_type)",
                        "CREATE INDEX tree_utility IF NOT EXISTS FOR (n:MeteringTree) ON (n.utility_type)"
                    ]
                    
                    for index in indexes:
                        session.run(index)
                    
                    logger.info("Initialized constraints and indexes")
                    return True
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to connect to Neo4j: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to initialize constraints after {max_retries} attempts: {e}")
                    raise
    
    def create_root_node(self, project_id, utility_type):
        """Create root MeteringTree node for a project"""
        with self.driver.session() as session:
            query = """
            CREATE (t:MeteringTree {
                id: $id,
                project_id: $project_id,
                name: $name,
                utility_type: $utility_type,
                is_utility_root: true,
                description: $description,
                created_at: datetime()
            })
            RETURN t
            """
            result = session.run(query, 
                id=str(uuid.uuid4()),
                project_id=project_id,
                name=f"{utility_type.capitalize()} Infrastructure",
                utility_type=utility_type,
                description=f"Root node for {utility_type} metering system"
            )
            node = result.single()[0]
            return neo4j_to_python(dict(node))
    
    def get_all_nodes(self, project_id):
        """Get all nodes for a project"""
        with self.driver.session() as session:
            query = "MATCH (n {project_id: $project_id}) RETURN n, labels(n) as labels"
            result = session.run(query, project_id=project_id)
            nodes = []
            for record in result:
                node = dict(record['n'])
                node['labels'] = record['labels']
                nodes.append(neo4j_to_python(node))
            return nodes
    
    def get_relationships(self, project_id):
        """Get all relationships for a project"""
        with self.driver.session() as session:
            query = """
            MATCH (a {project_id: $project_id})-[r]->(b {project_id: $project_id})
            RETURN 
                a.id as start_node,
                b.id as end_node,
                type(r) as rel_type,
                properties(r) as properties
            """
            result = session.run(query, project_id=project_id)
            relationships = []
            for record in result:
                relationships.append({
                    'start_node': record['start_node'],
                    'end_node': record['end_node'],
                    'type': record['rel_type'],
                    'properties': neo4j_to_python(dict(record['properties']) if record['properties'] else {})
                })
            return relationships
    
    def create_node(self, project_id, node_type, properties):
        """Create a new node"""
        with self.driver.session() as session:
            # Add unique ID and project_id if not present
            if 'id' not in properties:
                properties['id'] = str(uuid.uuid4())
            properties['project_id'] = project_id
            properties['created_at'] = 'datetime()'
            
            # Build property string
            prop_string = ', '.join([f"{k}: ${k}" for k in properties.keys() if k != 'created_at'])
            prop_string += ', created_at: datetime()'
            
            query = f"""
            CREATE (n:{node_type} {{{prop_string}}})
            RETURN n, labels(n) as labels
            """
            
            result = session.run(query, **properties)
            record = result.single()
            if record:
                node = dict(record['n'])
                node['labels'] = record['labels']
                return neo4j_to_python(node)
            return None
    
    def get_node(self, project_id, node_id):
        """Get a single node by ID within a specific project"""
        with self.driver.session() as session:
            query = """
            MATCH (n {id: $node_id, project_id: $project_id})
            RETURN n, labels(n) as labels
            """
            result = session.run(query, node_id=node_id, project_id=project_id)
            return self._process_single_node_result(result)
    
    def get_node_by_id(self, node_id):
        """Get a single node by ID (without project_id constraint, for cross-project operations)"""
        with self.driver.session() as session:
            query = """
            MATCH (n {id: $node_id})
            RETURN n, labels(n) as labels
            """
            result = session.run(query, node_id=node_id)
            return self._process_single_node_result(result)
    
    def _process_single_node_result(self, result):
        """Process a single node query result"""
        record = result.single()
        if record:
            node = dict(record['n'])
            node['labels'] = record['labels']
            return neo4j_to_python(node)
        return None
    
    def update_node(self, project_id, node_id, properties):
        """Update node properties"""
        with self.driver.session() as session:
            # Build SET clause
            set_clauses = [f"n.{k} = ${k}" for k in properties.keys()]
            set_string = ', '.join(set_clauses)
            
            query = f"""
            MATCH (n {{id: $node_id, project_id: $project_id}})
            SET {set_string}, n.updated_at = datetime()
            RETURN n, labels(n) as labels
            """
            
            result = session.run(query, node_id=node_id, project_id=project_id, **properties)
            record = result.single()
            if record:
                node = dict(record['n'])
                node['labels'] = record['labels']
                return neo4j_to_python(node)
            return None
    
    def delete_node(self, project_id, node_id):
        """Delete a node and its relationships"""
        with self.driver.session() as session:
            query = """
            MATCH (n {id: $node_id, project_id: $project_id})
            DETACH DELETE n
            RETURN count(n) as deleted
            """
            result = session.run(query, node_id=node_id, project_id=project_id)
            return result.single()['deleted'] > 0
    
    def create_relationship(self, project_id, start_node_id, end_node_id, rel_type, properties=None):
        """Create a relationship between two nodes"""
        with self.driver.session() as session:
            if properties:
                prop_string = ', '.join([f"{k}: ${k}" for k in properties.keys()])
                query = f"""
                MATCH (a {{id: $start_id, project_id: $project_id}}), (b {{id: $end_id, project_id: $project_id}})
                CREATE (a)-[r:{rel_type} {{{prop_string}}}]->(b)
                RETURN r, type(r) as rel_type
                """
                result = session.run(query, start_id=start_node_id, end_id=end_node_id, project_id=project_id, **properties)
            else:
                query = f"""
                MATCH (a {{id: $start_id, project_id: $project_id}}), (b {{id: $end_id, project_id: $project_id}})
                CREATE (a)-[r:{rel_type}]->(b)
                RETURN r, type(r) as rel_type
                """
                result = session.run(query, start_id=start_node_id, end_id=end_node_id, project_id=project_id)
            
            record = result.single()
            if record:
                rel = dict(record['r'])
                rel['type'] = record['rel_type']
                return rel
            return None
    
    def get_node_context(self, project_id, node_id, depth=1):
        """Get node with its ancestors and children"""
        with self.driver.session() as session:
            # Get ancestors (path to root)
            ancestors_query = """
            MATCH path = (n {id: $node_id, project_id: $project_id})<-[*]-(ancestor)
            WHERE ancestor.project_id = $project_id AND NOT (ancestor)<-[:CONNECTED_TO]-()
            WITH nodes(path) as node_list
            UNWIND node_list as node
            RETURN DISTINCT node, labels(node) as labels
            """
            
            # Get current node
            current_query = """
            MATCH (n {id: $node_id, project_id: $project_id})
            RETURN n as node, labels(n) as labels
            """
            
            # Get children
            children_query = f"""
            MATCH (n {{id: $node_id, project_id: $project_id}})-[:CONNECTED_TO*1..{depth}]->(child)
            WHERE child.project_id = $project_id
            RETURN DISTINCT child as node, labels(child) as labels
            """
            
            nodes = []
            relationships = []
            node_ids = set()
            
            # Collect all nodes
            for query in [ancestors_query, current_query, children_query]:
                result = session.run(query, node_id=node_id, project_id=project_id)
                for record in result:
                    node = dict(record['node'])
                    node['labels'] = record['labels']
                    node_ids.add(node['id'])
                    # Mark if it's the current node
                    if node['id'] == node_id:
                        node['is_current'] = True
                    nodes.append(neo4j_to_python(node))
            
            # Get relationships between loaded nodes
            if node_ids:
                rels_query = """
                MATCH (a)-[r:CONNECTED_TO]->(b)
                WHERE a.id IN $node_ids AND b.id IN $node_ids
                AND a.project_id = $project_id AND b.project_id = $project_id
                RETURN 
                    a.id as start_node,
                    b.id as end_node,
                    type(r) as rel_type,
                    properties(r) as properties
                """
                result = session.run(rels_query, node_ids=list(node_ids), project_id=project_id)
                for record in result:
                    relationships.append({
                        'start_node': record['start_node'],
                        'end_node': record['end_node'],
                        'type': record['rel_type'],
                        'properties': neo4j_to_python(dict(record['properties']) if record['properties'] else {})
                    })
            
            return {'nodes': nodes, 'relationships': relationships}
    
    def _process_node_results(self, result):
        """Process Neo4j result and return list of node dicts"""
        nodes = []
        for record in result:
            node = dict(record['n'])
            node['labels'] = record['labels']
            nodes.append(neo4j_to_python(node))
        return nodes
    
    def search_nodes(self, project_id, query_string):
        """Search nodes by name or description"""
        with self.driver.session() as session:
            cypher = """
            MATCH (n {project_id: $project_id})
            WHERE toLower(n.name) CONTAINS toLower($search_term) 
               OR toLower(coalesce(n.description, '')) CONTAINS toLower($search_term)
            RETURN n, labels(n) as labels
            LIMIT 50
            """
            result = session.run(cypher, search_term=query_string, project_id=project_id)
            return self._process_node_results(result)
    
    def search_nodes_global(self, query_string):
        """Search nodes globally by name, description, or serial_number (across all projects)"""
        with self.driver.session() as session:
            cypher = """
            MATCH (n)
            WHERE (toLower(n.name) CONTAINS toLower($search_term) 
               OR toLower(coalesce(n.description, '')) CONTAINS toLower($search_term)
               OR toLower(coalesce(n.serial_number, '')) CONTAINS toLower($search_term))
               AND NOT n:MeteringTree
            RETURN n, labels(n) as labels
            LIMIT 50
            """
            result = session.run(cypher, search_term=query_string)
            return self._process_node_results(result)
    
    def search_nodes_by_category(self, project_id, category):
        """Search Consumer nodes by category"""
        with self.driver.session() as session:
            cypher = """
            MATCH (n:Consumer {project_id: $project_id, category: $category})
            RETURN n, labels(n) as labels
            """
            result = session.run(cypher, project_id=project_id, category=category)
            return self._process_node_results(result)
    
    def get_paths_to_nodes(self, project_id, node_ids):
        """Get paths from root to multiple nodes (for tree expansion)"""
        with self.driver.session() as session:
            paths = []
            
            for node_id in node_ids:
                # Find all ancestors of the node by traversing backwards
                cypher = """
                MATCH (target {id: $node_id, project_id: $project_id})
                OPTIONAL MATCH path = (root:MeteringTree {project_id: $project_id})-[:CONNECTED_TO*]->(target)
                WITH nodes(path) as pathNodes
                WHERE pathNodes IS NOT NULL
                UNWIND pathNodes as n
                WITH DISTINCT n
                RETURN n.id as id
                """
                result = session.run(cypher, project_id=project_id, node_id=node_id)
                
                ancestors = []
                for record in result:
                    node_id_result = record['id']
                    if node_id_result and node_id_result != node_id:
                        ancestors.append({'id': node_id_result})
                
                paths.append({
                    'node_id': node_id,
                    'ancestors': ancestors
                })
            
            return paths
    
    def get_category_tree(self, project_id, node_ids):
        """Get complete tree structure from root to specified nodes (nodes + relationships)"""
        with self.driver.session() as session:
            nodes = []
            relationships = []
            seen_nodes = set()
            seen_rels = set()
            
            # For each target node, get the path from root
            for target_id in node_ids:
                cypher = """
                MATCH path = (root:MeteringTree {project_id: $project_id})-[:CONNECTED_TO*0..]->(target {id: $target_id, project_id: $project_id})
                UNWIND nodes(path) as n
                UNWIND relationships(path) as r
                RETURN DISTINCT n as node, labels(n) as labels, 
                       startNode(r).id as rel_start, endNode(r).id as rel_end, type(r) as rel_type
                """
                result = session.run(cypher, project_id=project_id, target_id=target_id)
                
                for record in result:
                    # Add node if not seen
                    node_data = dict(record['node'])
                    node_id = node_data.get('id')
                    if node_id and node_id not in seen_nodes:
                        seen_nodes.add(node_id)
                        node_data['labels'] = record['labels']
                        nodes.append(neo4j_to_python(node_data))
                    
                    # Add relationship if not seen
                    rel_start = record['rel_start']
                    rel_end = record['rel_end']
                    if rel_start and rel_end:
                        rel_key = f"{rel_start}-{rel_end}"
                        if rel_key not in seen_rels:
                            seen_rels.add(rel_key)
                            relationships.append({
                                'start': rel_start,
                                'end': rel_end,
                                'type': record['rel_type']
                            })
            
            return {'nodes': nodes, 'relationships': relationships}
    
    def get_tree_children(self, project_id, parent_id=None):
        """Get immediate children of a node for tree view"""
        with self.driver.session() as session:
            if parent_id:
                query = """
                MATCH (p {id: $parent_id, project_id: $project_id})-[:CONNECTED_TO]->(child)
                WHERE child.project_id = $project_id
                RETURN child as node, labels(child) as labels
                ORDER BY child.name
                """
                result = session.run(query, parent_id=parent_id, project_id=project_id)
            else:
                # Get root node
                query = """
                MATCH (n:MeteringTree {project_id: $project_id})
                RETURN n as node, labels(n) as labels
                """
                result = session.run(query, project_id=project_id)
            
            nodes = []
            for record in result:
                node = dict(record['node'])
                node['labels'] = record['labels']
                # Check if node has children
                has_children_query = """
                MATCH (n {id: $node_id, project_id: $project_id})-[:CONNECTED_TO]->()
                RETURN count(*) > 0 as has_children
                """
                has_children = session.run(has_children_query, node_id=node['id'], project_id=project_id).single()['has_children']
                node['has_children'] = has_children
                nodes.append(neo4j_to_python(node))
            
            return nodes
    
    def get_node_count(self, project_id):
        """Get total number of nodes for a project"""
        with self.driver.session() as session:
            result = session.run("MATCH (n {project_id: $project_id}) RETURN count(n) as count", project_id=project_id)
            return result.single()['count']
    
    def delete_project_nodes(self, project_id):
        """Delete all nodes for a project"""
        with self.driver.session() as session:
            query = """
            MATCH (n {project_id: $project_id})
            DETACH DELETE n
            RETURN count(n) as deleted
            """
            result = session.run(query, project_id=project_id)
            return result.single()['deleted']
    
    def ensure_utility_roots(self, project_id):
        """Ensure 3 utility root nodes exist for project"""
        utilities = ['electricity', 'water', 'heating']
        roots = {}
        
        with self.driver.session() as session:
            for utility in utilities:
                # Check if root exists
                query = """
                MATCH (n:MeteringTree {project_id: $project_id, utility_type: $utility, is_utility_root: true})
                RETURN n
                """
                result = session.run(query, project_id=project_id, utility=utility)
                node = result.single()
                
                if node:
                    roots[utility] = neo4j_to_python(dict(node['n']))
                else:
                    # Create root
                    roots[utility] = self.create_root_node(project_id, utility)
        
        return roots
    
    def insert_node_between(self, project_id, source_id, target_id, node_type, properties):
        """Insert new node between two existing nodes"""
        with self.driver.session() as session:
            # Add unique ID
            if 'id' not in properties:
                properties['id'] = str(uuid.uuid4())
            properties['project_id'] = project_id
            
            # Build property string
            prop_string = ', '.join([f"{k}: ${k}" for k in properties.keys()])
            
            query = f"""
            MATCH (source {{id: $source_id, project_id: $project_id}})
            MATCH (target {{id: $target_id, project_id: $project_id}})
            MATCH (source)-[old_rel:CONNECTED_TO]->(target)
            
            CREATE (new:{node_type} {{{prop_string}, created_at: datetime()}})
            CREATE (source)-[:CONNECTED_TO]->(new)
            CREATE (new)-[:CONNECTED_TO]->(target)
            DELETE old_rel
            
            RETURN new, labels(new) as labels
            """
            
            result = session.run(query, source_id=source_id, target_id=target_id, **properties)
            record = result.single()
            if record:
                node = dict(record['new'])
                node['labels'] = record['labels']
                return neo4j_to_python(node)
            return None
    
    def validate_connection(self, source_id, target_id):
        """
        Validate connection rules:
        1. Consumer can only be a child (target), not a parent (source)
        2. Meter/Distribution can only connect to same utility_type
        3. Only Consumer can be multi-project (connected from different infrastructures)
        
        Returns: (is_valid: bool, error_message: str or None)
        """
        source = self.get_node_by_id(source_id)
        target = self.get_node_by_id(target_id)
        
        if not source:
            return False, f"Source node '{source_id}' not found"
        if not target:
            return False, f"Target node '{target_id}' not found"
        
        source_labels = source.get('labels', [])
        target_labels = target.get('labels', [])
        source_utility = source.get('utility_type')
        target_utility = target.get('utility_type')
        source_project = source.get('project_id')
        target_project = target.get('project_id')
        
        # Rule 1: Consumer cannot be a parent (source)
        if 'Consumer' in source_labels:
            return False, "Consumer cannot be a parent node. Consumer can only receive connections, not create them."
        
        # Rule 2 & 3: Check utility type mixing and multi-project rules
        is_cross_project = source_project != target_project
        
        if is_cross_project:
            # Rule 3: Only Consumer can be multi-project target
            if 'Consumer' not in target_labels:
                return False, f"Cross-infrastructure connections are only allowed to Consumer nodes. " \
                             f"Target '{target.get('name')}' is {', '.join([l for l in target_labels if l != 'MeteringTree'])}."
        
        # Rule 2: Same utility type for Meter/Distribution connections (unless target is Consumer)
        if 'Consumer' not in target_labels:
            # Both are infrastructure nodes (Meter/Distribution)
            if source_utility and target_utility and source_utility != target_utility:
                return False, f"Cannot connect different utility types. " \
                             f"Source is '{source_utility}', target is '{target_utility}'. " \
                             f"Meter/Distribution nodes must be connected within the same utility infrastructure."
        
        return True, None
    
    def create_connection_between_nodes(self, source_id, target_id):
        """
        Create CONNECTED_TO relationship between two nodes.
        Validates connection rules before creating.
        
        Returns: (success: bool, error_message: str or None)
        """
        # Validate connection rules
        is_valid, error_message = self.validate_connection(source_id, target_id)
        if not is_valid:
            return False, error_message
        
        # Create connection
        with self.driver.session() as session:
            query = """
            MATCH (source {id: $source_id})
            MATCH (target {id: $target_id})
            MERGE (source)-[r:CONNECTED_TO]->(target)
            RETURN source, target, r
            """
            result = session.run(query, source_id=source_id, target_id=target_id)
            record = result.single()
            if record:
                return True, None
            return False, "Failed to create connection in database"
    
    def get_utility_root(self, project_id, utility_type):
        """Get a specific utility root node for project"""
        with self.driver.session() as session:
            query = """
            MATCH (n:MeteringTree {project_id: $project_id, utility_type: $utility_type, is_utility_root: true})
            RETURN n, labels(n) as labels
            """
            result = session.run(query, project_id=project_id, utility_type=utility_type)
            record = result.single()
            if record:
                node = dict(record['n'])
                node['labels'] = record['labels']
                return neo4j_to_python(node)
            return None
    
    def get_utility_roots(self, project_id):
        """Get all utility root nodes for project"""
        with self.driver.session() as session:
            query = """
            MATCH (n:MeteringTree {project_id: $project_id, is_utility_root: true})
            RETURN n, labels(n) as labels
            ORDER BY n.utility_type
            """
            result = session.run(query, project_id=project_id)
            roots = []
            for record in result:
                node = dict(record['n'])
                node['labels'] = record['labels']
                roots.append(neo4j_to_python(node))
            return roots

# Global service instance
_neo4j_service = None

def init_neo4j_service(uri, user, password):
    """Initialize Neo4j service with config"""
    global _neo4j_service
    _neo4j_service = Neo4jService(uri, user, password)
    return _neo4j_service

def get_neo4j_service():
    """Get Neo4j service instance"""
    if _neo4j_service is None:
        raise RuntimeError("Neo4j service not initialized. Call init_neo4j_service first.")
    return _neo4j_service
