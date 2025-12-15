from flask import Blueprint, request, jsonify
from app.services.neo4j_service import get_neo4j_service
from app.services.timescale_service import get_timescale_service
from app.utils.csv_parser import parse_bulk_csv
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('bulk', __name__, url_prefix='/api/bulk')


def decode_csv_content(raw_bytes):
    """
    Try to decode CSV content with multiple encodings.
    Returns decoded string or raises an error.
    """
    # List of encodings to try (in order of preference)
    encodings = [
        'utf-8-sig',    # UTF-8 with BOM (Excel often saves this way)
        'utf-8',        # Standard UTF-8
        'cp1250',       # Windows Central European (Polish)
        'cp1252',       # Windows Western European
        'iso-8859-2',   # Latin-2 (Central European)
        'iso-8859-1',   # Latin-1 (Western European)
    ]
    
    for encoding in encodings:
        try:
            return raw_bytes.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    
    # If all fail, decode with replacement characters
    return raw_bytes.decode('utf-8', errors='replace')


@bp.route('/nodes', methods=['POST'])
def bulk_import_nodes():
    """Bulk import nodes from CSV"""
    try:
        project_id = request.form.get('project_id', type=int)
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are allowed'}), 400
        
        # Get project
        ts_service = get_timescale_service()
        project = ts_service.get_project(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Parse CSV - try multiple encodings
        raw_content = file.read()
        csv_content = decode_csv_content(raw_content)
        parsed_data = parse_bulk_csv(csv_content)
        
        if 'error' in parsed_data:
            return jsonify(parsed_data), 400
        
        # Import nodes
        neo4j_service = get_neo4j_service()
        
        # Ensure utility root nodes exist for this project
        utility_roots = neo4j_service.ensure_utility_roots(project_id)
        logger.info(f"Utility roots for project {project_id}: {list(utility_roots.keys())}")
        
        success_count = 0
        errors = []
        root_connected_nodes = []  # Track nodes that need to connect to MeteringTree root
        
        for idx, node_data in enumerate(parsed_data['nodes'], start=2):  # Start from row 2 (after header)
            try:
                # Create node
                node = neo4j_service.create_node(
                    project_id,
                    node_data['type'],
                    node_data['properties']
                )
                
                # Create relationship if parent specified
                if node_data.get('parent_name'):
                    # Find parent by name
                    parent_nodes = neo4j_service.search_nodes(project_id, node_data['parent_name'])
                    matching_parents = [n for n in parent_nodes if n['name'] == node_data['parent_name']]
                    
                    if matching_parents:
                        neo4j_service.create_relationship(
                            project_id,
                            matching_parents[0]['id'],
                            node['id'],
                            'CONNECTED_TO'
                        )
                    else:
                        errors.append({
                            'row': idx,
                            'error': f"Parent '{node_data['parent_name']}' not found"
                        })
                else:
                    # No parent - this is a root node, connect to MeteringTree
                    root_connected_nodes.append({
                        'node': node,
                        'utility_type': node_data['properties'].get('utility_type', 'electricity')
                    })
                
                success_count += 1
                
            except Exception as e:
                errors.append({
                    'row': idx,
                    'error': str(e)
                })
        
        # Connect root nodes to MeteringTree utility roots
        for root_node_info in root_connected_nodes:
            try:
                utility_type = root_node_info['utility_type'] or 'electricity'
                if utility_type in utility_roots:
                    neo4j_service.create_relationship(
                        project_id,
                        utility_roots[utility_type]['id'],
                        root_node_info['node']['id'],
                        'CONNECTED_TO'
                    )
                    logger.info(f"Connected root node '{root_node_info['node'].get('name')}' to {utility_type} root")
            except Exception as e:
                logger.warning(f"Failed to connect root node to MeteringTree: {e}")
        
        return jsonify({
            'success': success_count,
            'errors': errors,
            'total': len(parsed_data['nodes'])
        }), 200 if not errors else 207  # 207 Multi-Status
        
    except Exception as e:
        logger.error(f"Error in bulk import: {e}")
        return jsonify({'error': str(e)}), 500
