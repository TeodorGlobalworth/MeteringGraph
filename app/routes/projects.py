from flask import Blueprint, request, jsonify, render_template
from app.services.neo4j_service import get_neo4j_service
from app.services.timescale_service import get_timescale_service
import uuid
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('projects', __name__, url_prefix='/api/projects')

@bp.route('', methods=['GET'])
def get_projects():
    """Get all projects"""
    try:
        ts_service = get_timescale_service()
        projects = ts_service.get_all_projects()
        
        # Add node count for each project
        neo4j_service = get_neo4j_service()
        for project in projects:
            try:
                count = neo4j_service.get_node_count(project['id'])
                project['node_count'] = count
            except:
                project['node_count'] = 0
        
        return jsonify(projects), 200
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('', methods=['POST'])
def create_project():
    """Create a new project with 3 utility infrastructures"""
    try:
        data = request.json
        name = data.get('name')
        
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        
        # Create project in TimescaleDB first to get ID
        ts_service = get_timescale_service()
        project = ts_service.create_project(name)
        
        # Create 3 utility root nodes in Neo4j
        neo4j_service = get_neo4j_service()
        roots = neo4j_service.ensure_utility_roots(project['id'])
        
        # Seed default categories
        ts_service.seed_default_categories(project['id'])
        
        return jsonify(project), 201
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a single project"""
    try:
        ts_service = get_timescale_service()
        project = ts_service.get_project(project_id)
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Add node count
        neo4j_service = get_neo4j_service()
        try:
            count = neo4j_service.get_node_count(project['id'])
            project['node_count'] = count
        except:
            project['node_count'] = 0
        
        return jsonify(project), 200
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project"""
    try:
        ts_service = get_timescale_service()
        project = ts_service.get_project(project_id)
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Delete Neo4j nodes for this project
        neo4j_service = get_neo4j_service()
        neo4j_service.delete_project_nodes(project_id)
        
        # Delete project from TimescaleDB (cascade deletes readings and categories)
        ts_service.delete_project(project_id)
        
        return jsonify({'message': 'Project deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:project_id>/export', methods=['GET'])
def export_project(project_id):
    """Export project as JSON"""
    try:
        ts_service = get_timescale_service()
        project = ts_service.get_project(project_id)
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        neo4j_service = get_neo4j_service()
        
        # Get all nodes and relationships
        nodes = neo4j_service.get_all_nodes(project_id)
        relationships = neo4j_service.get_relationships(project_id)
        
        # Get categories
        categories = ts_service.get_categories(project_id)
        
        # Get all readings
        readings = ts_service.get_all_readings_for_export(project_id)
        
        export_data = {
            'version': '1.0',
            'project': {
                'name': project['name'],
                'utility_type': project['utility_type'],
                'exported_at': str(project['updated_at'])
            },
            'nodes': nodes,
            'relationships': relationships,
            'categories': categories,
            'readings': readings
        }
        
        return jsonify(export_data), 200
    except Exception as e:
        logger.error(f"Error exporting project: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/import', methods=['POST'])
def import_project():
    """Import project from JSON"""
    try:
        data = request.json
        
        if not data or 'version' not in data or 'project' not in data:
            return jsonify({'error': 'Invalid import format'}), 400
        
        project_data = data['project']
        nodes = data.get('nodes', [])
        relationships = data.get('relationships', [])
        categories = data.get('categories', [])
        readings = data.get('readings', [])
        
        # Create new project
        db_name = f"project_{uuid.uuid4().hex[:12]}"
        
        neo4j_service = get_neo4j_service()
        neo4j_service.create_database(db_name)
        neo4j_service.init_database_constraints(db_name)
        
        ts_service = get_timescale_service()
        new_project = ts_service.create_project(
            project_data['name'] + ' (Imported)',
            db_name,
            project_data['utility_type']
        )
        
        # Import nodes (preserving IDs)
        with neo4j_service.driver.session(database=db_name) as session:
            for node in nodes:
                labels = ':'.join(node.get('labels', ['Node']))
                props = {k: v for k, v in node.items() if k != 'labels'}
                
                # Build property string
                prop_items = []
                for k, v in props.items():
                    if isinstance(v, str):
                        prop_items.append(f"{k}: '{v}'")
                    else:
                        prop_items.append(f"{k}: {v}")
                prop_string = ', '.join(prop_items)
                
                query = f"CREATE (:{labels} {{{prop_string}}})"
                session.run(query)
        
        # Import relationships
        with neo4j_service.driver.session(database=db_name) as session:
            for rel in relationships:
                start_id = rel['start_node']
                end_id = rel['end_node']
                rel_type = rel['type']
                props = rel.get('properties', {})
                
                if props:
                    prop_items = []
                    for k, v in props.items():
                        if isinstance(v, str):
                            prop_items.append(f"{k}: '{v}'")
                        else:
                            prop_items.append(f"{k}: {v}")
                    prop_string = ', '.join(prop_items)
                    query = f"""
                    MATCH (a {{id: '{start_id}'}}), (b {{id: '{end_id}'}})
                    CREATE (a)-[:{rel_type} {{{prop_string}}}]->(b)
                    """
                else:
                    query = f"""
                    MATCH (a {{id: '{start_id}'}}), (b {{id: '{end_id}'}})
                    CREATE (a)-[:{rel_type}]->(b)
                    """
                session.run(query)
        
        # Import categories
        for cat in categories:
            ts_service.create_category(
                new_project['id'],
                cat['node_type'],
                cat['category_name']
            )
        
        # Import readings
        for reading in readings:
            ts_service.add_reading(
                new_project['id'],
                reading['node_id'],
                reading['value'],
                reading['unit'],
                reading['time']
            )
        
        return jsonify(new_project), 201
    except Exception as e:
        logger.error(f"Error importing project: {e}")
        return jsonify({'error': str(e)}), 500

# View route
@bp.route('/<int:project_id>/view', methods=['GET'])
def view_project(project_id):
    """Render project view page"""
    try:
        ts_service = get_timescale_service()
        project = ts_service.get_project(project_id)
        
        if not project:
            return "Project not found", 404
        
        return render_template('project.html', project=project)
    except Exception as e:
        logger.error(f"Error viewing project: {e}")
        return str(e), 500
