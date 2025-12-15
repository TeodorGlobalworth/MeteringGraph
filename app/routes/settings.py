from flask import Blueprint, request, jsonify, render_template
from app.services.timescale_service import get_timescale_service
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('settings', __name__, url_prefix='/api/settings')


@bp.route('/consumer-categories', methods=['GET'])
def get_consumer_categories():
    """Get all consumer category settings"""
    try:
        ts_service = get_timescale_service()
        categories = ts_service.get_consumer_categories()
        return jsonify(categories), 200
    except Exception as e:
        logger.error(f"Error getting consumer categories: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/consumer-categories', methods=['POST'])
def create_consumer_category():
    """Create a new consumer category"""
    try:
        data = request.json
        
        if not data.get('category_name') or not data.get('display_name'):
            return jsonify({'error': 'category_name and display_name are required'}), 400
        
        ts_service = get_timescale_service()
        category = ts_service.create_consumer_category(
            category_name=data['category_name'],
            display_name=data['display_name'],
            icon_name=data.get('icon_name', 'box-fill'),
            color=data.get('color', '#868e96'),
            sort_order=data.get('sort_order', 50)
        )
        
        return jsonify(category), 201
    except Exception as e:
        logger.error(f"Error creating consumer category: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/consumer-categories/<int:category_id>', methods=['PUT'])
def update_consumer_category(category_id):
    """Update a consumer category"""
    try:
        data = request.json
        
        ts_service = get_timescale_service()
        category = ts_service.update_consumer_category(
            category_id=category_id,
            display_name=data.get('display_name'),
            icon_name=data.get('icon_name'),
            color=data.get('color'),
            sort_order=data.get('sort_order'),
            is_active=data.get('is_active')
        )
        
        if category:
            return jsonify(category), 200
        else:
            return jsonify({'error': 'Category not found'}), 404
    except Exception as e:
        logger.error(f"Error updating consumer category: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/consumer-categories/<int:category_id>', methods=['DELETE'])
def delete_consumer_category(category_id):
    """Delete a consumer category"""
    try:
        ts_service = get_timescale_service()
        success = ts_service.delete_consumer_category(category_id)
        
        if success:
            return jsonify({'message': 'Category deleted'}), 200
        else:
            return jsonify({'error': 'Category not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting consumer category: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/bootstrap-icons', methods=['GET'])
def get_bootstrap_icons():
    """Get list of available Bootstrap icons for selection"""
    # Popular/useful icons for metering system
    icons = [
        # Lighting
        {'name': 'lightbulb', 'label': 'Lightbulb'},
        {'name': 'lightbulb-fill', 'label': 'Lightbulb (filled)'},
        {'name': 'lamp', 'label': 'Lamp'},
        {'name': 'lamp-fill', 'label': 'Lamp (filled)'},
        
        # HVAC / Temperature
        {'name': 'snow', 'label': 'Snow (cooling)'},
        {'name': 'snow2', 'label': 'Snowflake'},
        {'name': 'thermometer', 'label': 'Thermometer'},
        {'name': 'thermometer-half', 'label': 'Thermometer (half)'},
        {'name': 'fire', 'label': 'Fire (heating)'},
        
        # Mechanical
        {'name': 'gear', 'label': 'Gear'},
        {'name': 'gear-fill', 'label': 'Gear (filled)'},
        {'name': 'gears', 'label': 'Gears'},
        {'name': 'fan', 'label': 'Fan'},
        {'name': 'wind', 'label': 'Wind'},
        
        # Electrical
        {'name': 'plug', 'label': 'Plug'},
        {'name': 'plug-fill', 'label': 'Plug (filled)'},
        {'name': 'outlet', 'label': 'Outlet'},
        {'name': 'lightning', 'label': 'Lightning'},
        {'name': 'lightning-fill', 'label': 'Lightning (filled)'},
        {'name': 'battery', 'label': 'Battery'},
        {'name': 'battery-charging', 'label': 'Battery charging'},
        
        # Transport / Movement
        {'name': 'arrows-expand', 'label': 'Arrows expand'},
        {'name': 'arrow-up-square', 'label': 'Arrow up square'},
        {'name': 'arrow-down-square', 'label': 'Arrow down square'},
        {'name': 'elevator', 'label': 'Elevator'},
        
        # Water
        {'name': 'droplet', 'label': 'Droplet'},
        {'name': 'droplet-fill', 'label': 'Droplet (filled)'},
        {'name': 'water', 'label': 'Water'},
        {'name': 'moisture', 'label': 'Moisture'},
        
        # Tools / Equipment
        {'name': 'tools', 'label': 'Tools'},
        {'name': 'wrench', 'label': 'Wrench'},
        {'name': 'wrench-adjustable', 'label': 'Adjustable wrench'},
        {'name': 'hammer', 'label': 'Hammer'},
        
        # Buildings / Rooms
        {'name': 'building', 'label': 'Building'},
        {'name': 'house', 'label': 'House'},
        {'name': 'door-open', 'label': 'Door open'},
        {'name': 'door-closed', 'label': 'Door closed'},
        
        # Generic / Other
        {'name': 'box', 'label': 'Box'},
        {'name': 'box-fill', 'label': 'Box (filled)'},
        {'name': 'archive', 'label': 'Archive'},
        {'name': 'server', 'label': 'Server'},
        {'name': 'cpu', 'label': 'CPU'},
        {'name': 'pc-display', 'label': 'PC Display'},
        {'name': 'printer', 'label': 'Printer'},
        {'name': 'wifi', 'label': 'WiFi'},
        
        # Meters / Gauges
        {'name': 'speedometer', 'label': 'Speedometer'},
        {'name': 'speedometer2', 'label': 'Speedometer 2'},
        {'name': 'graph-up', 'label': 'Graph up'},
        {'name': 'bar-chart', 'label': 'Bar chart'},
        
        # Safety / Security
        {'name': 'shield', 'label': 'Shield'},
        {'name': 'shield-fill', 'label': 'Shield (filled)'},
        {'name': 'exclamation-triangle', 'label': 'Warning'},
        {'name': 'bell', 'label': 'Bell'},
        {'name': 'bell-fill', 'label': 'Bell (filled)'},
        
        # Miscellaneous
        {'name': 'star', 'label': 'Star'},
        {'name': 'star-fill', 'label': 'Star (filled)'},
        {'name': 'heart', 'label': 'Heart'},
        {'name': 'circle', 'label': 'Circle'},
        {'name': 'circle-fill', 'label': 'Circle (filled)'},
        {'name': 'square', 'label': 'Square'},
        {'name': 'square-fill', 'label': 'Square (filled)'},
        {'name': 'triangle', 'label': 'Triangle'},
        {'name': 'triangle-fill', 'label': 'Triangle (filled)'},
        {'name': 'hexagon', 'label': 'Hexagon'},
        {'name': 'hexagon-fill', 'label': 'Hexagon (filled)'},
    ]
    
    return jsonify(icons), 200
