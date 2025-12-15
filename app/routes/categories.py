from flask import Blueprint, request, jsonify
from app.services.timescale_service import get_timescale_service
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('categories', __name__, url_prefix='/api/categories')

@bp.route('', methods=['GET'])
def get_categories():
    """Get categories for a project"""
    try:
        project_id = request.args.get('project_id', type=int)
        node_type = request.args.get('node_type')
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        ts_service = get_timescale_service()
        categories = ts_service.get_categories(project_id, node_type)
        
        return jsonify(categories), 200
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('', methods=['POST'])
def create_category():
    """Create a new category"""
    try:
        data = request.json
        project_id = data.get('project_id')
        node_type = data.get('node_type')
        category_name = data.get('category_name')
        
        if not all([project_id, node_type, category_name]):
            return jsonify({'error': 'project_id, node_type, and category_name are required'}), 400
        
        ts_service = get_timescale_service()
        category = ts_service.create_category(project_id, node_type, category_name)
        
        if not category:
            return jsonify({'error': 'Category already exists'}), 409
        
        return jsonify(category), 201
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        return jsonify({'error': str(e)}), 500
