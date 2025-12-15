from flask import Blueprint, request, jsonify
from app.services.neo4j_service import get_neo4j_service
from app.services.timescale_service import get_timescale_service
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('nodes', __name__, url_prefix='/api/nodes')

@bp.route('', methods=['POST'])
def create_node():
    """Create a new node"""
    try:
        data = request.json
        project_id = data.get('project_id')
        node_type = data.get('type')
        parent_id = data.get('parent_id')
        properties = data.get('properties', {})
        
        if not all([project_id, node_type, properties.get('name')]):
            return jsonify({'error': 'project_id, type, and name are required'}), 400
        
        # Get project
        ts_service = get_timescale_service()
        project = ts_service.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Create node
        neo4j_service = get_neo4j_service()
        node = neo4j_service.create_node(
            project_id,
            node_type,
            properties
        )
        
        if not node:
            return jsonify({'error': 'Failed to create node'}), 500
        
        # Determine parent for relationship
        actual_parent_id = parent_id
        
        # If no parent specified, connect to appropriate utility root (except Consumer)
        if not parent_id and node_type != 'Consumer':
            utility_type = properties.get('utility_type', 'electricity')
            utility_root = neo4j_service.get_utility_root(project_id, utility_type)
            if utility_root:
                actual_parent_id = utility_root['id']
        
        # Create relationship to parent if we have one
        if actual_parent_id:
            neo4j_service.create_relationship(
                project_id,
                actual_parent_id,
                node['id'],
                'CONNECTED_TO'
            )
        
        return jsonify(node), 201
    except Exception as e:
        logger.error(f"Error creating node: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<node_id>', methods=['GET'])
def get_node(node_id):
    """Get a single node by ID"""
    try:
        project_id = request.args.get('project_id', type=int)
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        # Get project
        ts_service = get_timescale_service()
        project = ts_service.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Get node
        neo4j_service = get_neo4j_service()
        node = neo4j_service.get_node(project_id, node_id)
        
        if not node:
            return jsonify({'error': 'Node not found'}), 404
        
        return jsonify(node), 200
    except Exception as e:
        logger.error(f"Error getting node: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<node_id>', methods=['PUT'])
def update_node(node_id):
    """Update a node"""
    try:
        data = request.json
        project_id = data.get('project_id')
        properties = data.get('properties', {})
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        # Get project
        ts_service = get_timescale_service()
        project = ts_service.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Update node
        neo4j_service = get_neo4j_service()
        node = neo4j_service.update_node(
            project_id,
            node_id,
            properties
        )
        
        if not node:
            return jsonify({'error': 'Node not found'}), 404
        
        return jsonify(node), 200
    except Exception as e:
        logger.error(f"Error updating node: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<node_id>', methods=['DELETE'])
def delete_node(node_id):
    """Delete a node"""
    try:
        project_id = request.args.get('project_id', type=int)
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        # Get project
        ts_service = get_timescale_service()
        project = ts_service.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Delete node
        neo4j_service = get_neo4j_service()
        success = neo4j_service.delete_node(
            project_id,
            node_id
        )
        
        if not success:
            return jsonify({'error': 'Node not found'}), 404
        
        return jsonify({'message': 'Node deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting node: {e}")
        return jsonify({'error': str(e)}), 500
