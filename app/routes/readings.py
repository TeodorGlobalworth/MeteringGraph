from flask import Blueprint, request, jsonify
from app.services.timescale_service import get_timescale_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('readings', __name__, url_prefix='/api/readings')

@bp.route('/<node_id>', methods=['GET'])
def get_readings(node_id):
    """Get readings for a node"""
    try:
        project_id = request.args.get('project_id', type=int)
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        ts_service = get_timescale_service()
        readings = ts_service.get_readings(project_id, node_id, limit, offset)
        
        return jsonify(readings), 200
    except Exception as e:
        logger.error(f"Error getting readings: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<node_id>', methods=['POST'])
def add_reading(node_id):
    """Add a reading for a node"""
    try:
        data = request.json
        project_id = data.get('project_id')
        value = data.get('value')
        unit = data.get('unit')
        timestamp = data.get('timestamp')
        
        if not all([project_id, value, unit]):
            return jsonify({'error': 'project_id, value, and unit are required'}), 400
        
        # Parse timestamp if provided
        if timestamp:
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except:
                return jsonify({'error': 'Invalid timestamp format'}), 400
        
        ts_service = get_timescale_service()
        reading = ts_service.add_reading(project_id, node_id, value, unit, timestamp)
        
        return jsonify(reading), 201
    except Exception as e:
        logger.error(f"Error adding reading: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<node_id>/daily', methods=['GET'])
def get_daily_aggregates(node_id):
    """Get daily aggregated readings"""
    try:
        project_id = request.args.get('project_id', type=int)
        days = request.args.get('days', default=30, type=int)
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        ts_service = get_timescale_service()
        aggregates = ts_service.get_daily_aggregates(project_id, node_id, days)
        
        return jsonify(aggregates), 200
    except Exception as e:
        logger.error(f"Error getting daily aggregates: {e}")
        return jsonify({'error': str(e)}), 500
