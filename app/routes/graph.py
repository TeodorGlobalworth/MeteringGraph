from flask import Blueprint, request, jsonify
from app.services.neo4j_service import get_neo4j_service
from app.services.timescale_service import get_timescale_service
from functools import wraps
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('graph', __name__, url_prefix='/api/graph')


def validate_project(f):
    """Decorator to validate project_id parameter"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        project_id = request.args.get('project_id', type=int)
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        ts_service = get_timescale_service()
        project = ts_service.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Add project_id to kwargs for the route
        kwargs['project_id'] = project_id
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/context/<node_id>', methods=['GET'])
@validate_project
def get_context(node_id, project_id):
    """Get node context (ancestors + current + children)"""
    try:
        depth = request.args.get('depth', default=1, type=int)
        neo4j_service = get_neo4j_service()
        context = neo4j_service.get_node_context(project_id, node_id, depth)
        return jsonify(context), 200
    except Exception as e:
        logger.error(f"Error getting context: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/expand/<node_id>', methods=['GET'])
@validate_project
def expand_node(node_id, project_id):
    """Expand node to show its neighbors"""
    try:
        neo4j_service = get_neo4j_service()
        context = neo4j_service.get_node_context(project_id, node_id, depth=1)
        
        return jsonify(context), 200
    except Exception as e:
        logger.error(f"Error expanding node: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/connection', methods=['POST'])
def create_connection():
    """Create a connection between two nodes"""
    try:
        data = request.json
        project_id = data.get('project_id')
        start_node_id = data.get('start_node_id')
        end_node_id = data.get('end_node_id')
        connection_type = data.get('connection_type', '')
        
        if not all([project_id, start_node_id, end_node_id]):
            return jsonify({'error': 'project_id, start_node_id, and end_node_id are required'}), 400
        
        # Get project
        ts_service = get_timescale_service()
        project = ts_service.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Create relationship
        neo4j_service = get_neo4j_service()
        properties = {'connection_type': connection_type} if connection_type else None
        relationship = neo4j_service.create_relationship(
            project_id,
            start_node_id,
            end_node_id,
            'CONNECTED_TO',
            properties
        )
        
        return jsonify(relationship), 201
    except Exception as e:
        logger.error(f"Error creating connection: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/tree', methods=['GET'])
@validate_project
def get_tree(project_id):
    """Get tree structure for tree view"""
    try:
        parent_id = request.args.get('parent_id')
        neo4j_service = get_neo4j_service()
        nodes = neo4j_service.get_tree_children(project_id, parent_id)
        return jsonify(nodes), 200
    except Exception as e:
        logger.error(f"Error getting tree: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/search', methods=['GET'])
@validate_project
def search(project_id):
    """Search nodes"""
    try:
        query = request.args.get('q', '')
        category = request.args.get('category', '')
        
        neo4j_service = get_neo4j_service()
        
        if category:
            nodes = neo4j_service.search_nodes_by_category(project_id, category)
        elif not query:
            nodes = neo4j_service.get_all_nodes(project_id)
        else:
            nodes = neo4j_service.search_nodes(project_id, query)
        
        return jsonify(nodes), 200
    except Exception as e:
        logger.error(f"Error searching: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/paths', methods=['GET'])
@validate_project
def get_paths_to_nodes(project_id):
    """Get paths (ancestors) to multiple nodes"""
    try:
        node_ids_str = request.args.get('node_ids', '')
        if not node_ids_str:
            return jsonify([]), 200
        
        node_ids = [nid.strip() for nid in node_ids_str.split(',') if nid.strip()]
        neo4j_service = get_neo4j_service()
        paths = neo4j_service.get_paths_to_nodes(project_id, node_ids)
        return jsonify(paths), 200
    except Exception as e:
        logger.error(f"Error getting paths: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/category-tree', methods=['GET'])
@validate_project
def get_category_tree(project_id):
    """Get tree structure containing paths to specific nodes (for category view)"""
    try:
        node_ids_str = request.args.get('node_ids', '')
        if not node_ids_str:
            return jsonify({'nodes': [], 'relationships': []}), 200
        
        node_ids = [nid.strip() for nid in node_ids_str.split(',') if nid.strip()]
        neo4j_service = get_neo4j_service()
        tree_data = neo4j_service.get_category_tree(project_id, node_ids)
        return jsonify(tree_data), 200
    except Exception as e:
        logger.error(f"Error getting category tree: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/utility-roots/<int:project_id>', methods=['GET'])
def get_utility_roots(project_id):
    """Get all utility root nodes for project"""
    try:
        ts_service = get_timescale_service()
        project = ts_service.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        neo4j_service = get_neo4j_service()
        roots = neo4j_service.get_utility_roots(project_id)
        
        return jsonify(roots), 200
    except Exception as e:
        logger.error(f"Error getting utility roots: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/insert-between', methods=['POST'])
def insert_node_between():
    """Insert new node between two existing nodes"""
    try:
        data = request.json
        project_id = data.get('project_id')
        source_id = data.get('source_id')
        target_id = data.get('target_id')
        node_type = data.get('node_type')
        properties = data.get('properties', {})
        
        if not all([project_id, source_id, target_id, node_type]):
            return jsonify({'error': 'project_id, source_id, target_id, and node_type are required'}), 400
        
        neo4j_service = get_neo4j_service()
        node = neo4j_service.insert_node_between(project_id, source_id, target_id, node_type, properties)
        
        if node:
            return jsonify(node), 201
        else:
            return jsonify({'error': 'Failed to insert node'}), 500
    except Exception as e:
        logger.error(f"Error inserting node: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/connect', methods=['POST'])
def connect_nodes():
    """Create connection between two nodes with validation rules"""
    try:
        data = request.json
        source_id = data.get('source_id')
        target_id = data.get('target_id')
        
        if not all([source_id, target_id]):
            return jsonify({'error': 'source_id and target_id are required'}), 400
        
        neo4j_service = get_neo4j_service()
        success, error_message = neo4j_service.create_connection_between_nodes(source_id, target_id)
        
        if success:
            return jsonify({'message': 'Connection created'}), 201
        else:
            return jsonify({'error': error_message or 'Failed to create connection'}), 400
    except Exception as e:
        logger.error(f"Error creating connection: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/search-global', methods=['GET'])
def search_global():
    """Search nodes globally across all projects by name, description, or serial_number"""
    try:
        query = request.args.get('q', '')
        
        if not query or len(query) < 2:
            return jsonify([]), 200
        
        neo4j_service = get_neo4j_service()
        nodes = neo4j_service.search_nodes_global(query)
        
        return jsonify(nodes), 200
    except Exception as e:
        logger.error(f"Error in global search: {e}")
        return jsonify({'error': str(e)}), 500
