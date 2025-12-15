"""Utility functions for the application"""
from neo4j.time import DateTime, Date, Time, Duration
from datetime import datetime, date, time, timedelta
import json


def neo4j_to_python(obj):
    """
    Convert Neo4j types to Python native types for JSON serialization
    """
    if isinstance(obj, DateTime):
        # Neo4j DateTime to Python datetime
        return datetime(
            obj.year, obj.month, obj.day,
            obj.hour, obj.minute, int(obj.second),
            int((obj.second % 1) * 1000000)
        ).isoformat()
    elif isinstance(obj, Date):
        # Neo4j Date to Python date
        return date(obj.year, obj.month, obj.day).isoformat()
    elif isinstance(obj, Time):
        # Neo4j Time to Python time
        return time(
            obj.hour, obj.minute, int(obj.second),
            int((obj.second % 1) * 1000000)
        ).isoformat()
    elif isinstance(obj, Duration):
        # Neo4j Duration to total seconds
        return obj.seconds
    elif isinstance(obj, dict):
        # Recursively convert dictionary values
        return {key: neo4j_to_python(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        # Recursively convert list items
        return [neo4j_to_python(item) for item in obj]
    else:
        return obj


def serialize_node(node):
    """
    Serialize a Neo4j node to JSON-compatible dict
    """
    if not node:
        return None
    
    result = {
        'id': node.get('id'),
        'type': list(node.labels)[0] if node.labels else None,
        'properties': {}
    }
    
    # Convert all properties
    for key, value in node.items():
        result['properties'][key] = neo4j_to_python(value)
    
    return result


def serialize_relationship(rel):
    """
    Serialize a Neo4j relationship to JSON-compatible dict
    """
    if not rel:
        return None
    
    result = {
        'type': rel.type,
        'properties': {}
    }
    
    # Convert all properties
    for key, value in rel.items():
        result['properties'][key] = neo4j_to_python(value)
    
    return result


class Neo4jJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles Neo4j types
    """
    def default(self, obj):
        converted = neo4j_to_python(obj)
        if converted is not obj:
            return converted
        return super().default(obj)
