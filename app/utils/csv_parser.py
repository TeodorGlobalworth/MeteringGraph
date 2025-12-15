import csv
import io
import logging

logger = logging.getLogger(__name__)

# Valid values for validation
VALID_NODE_TYPES = ['Meter', 'Distribution', 'Consumer']
VALID_UTILITY_TYPES = ['electricity', 'water', 'heating', 'gas']
VALID_METER_SUBTYPES = ['Main', 'Submeter']
VALID_DISTRIBUTION_SUBTYPES = ['Main Panel', 'Sub Panel']
VALID_CONSUMER_CATEGORIES = ['Lighting', 'HVAC', 'Elevator', 'Pumps', 'Ventilation', 'Outlets', 'Equipment', 'Other']


def preprocess_csv_content(csv_content):
    """
    Remove comment lines (starting with #) from CSV content.
    This allows users to include instructions in the CSV file.
    """
    lines = csv_content.split('\n')
    filtered_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Skip comment lines (starting with #)
        if stripped.startswith('#'):
            continue
        # Skip completely empty lines before header is found
        if not stripped and not filtered_lines:
            continue
        filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)


def parse_bulk_csv(csv_content):
    """Parse CSV content for bulk node import"""
    try:
        # Preprocess to remove comments
        cleaned_content = preprocess_csv_content(csv_content)
        
        if not cleaned_content.strip():
            return {'error': 'CSV file is empty or contains only comments'}
        
        # Read CSV
        csv_file = io.StringIO(cleaned_content)
        reader = csv.DictReader(csv_file)
        
        # Check if we have any fieldnames
        if not reader.fieldnames:
            return {'error': 'CSV file has no header row'}
        
        # Required columns
        required_columns = ['name', 'type', 'subtype_or_category']
        
        # Check for required columns
        missing_columns = [col for col in required_columns if col not in reader.fieldnames]
        if missing_columns:
            return {
                'error': f"Missing required columns: {', '.join(missing_columns)}. Required: {', '.join(required_columns)}",
                'found': list(reader.fieldnames)
            }
        
        nodes = []
        row_num = 1  # Header is row 1, data starts at row 2
        
        for row in reader:
            row_num += 1
            
            # Skip empty rows (check if name is empty or whitespace)
            name_value = row.get('name', '').strip()
            if not name_value:
                continue
            
            # Extract and validate type
            node_type = row.get('type', '').strip()
            if not node_type:
                return {
                    'error': f"Missing 'type' value at row {row_num}. Must be one of: {', '.join(VALID_NODE_TYPES)}"
                }
            
            if node_type not in VALID_NODE_TYPES:
                return {
                    'error': f"Invalid type '{node_type}' at row {row_num}. Must be one of: {', '.join(VALID_NODE_TYPES)}"
                }
            
            # Extract subtype/category
            subtype_or_category = row.get('subtype_or_category', '').strip()
            if not subtype_or_category:
                return {
                    'error': f"Missing 'subtype_or_category' value at row {row_num}"
                }
            
            # Build properties
            properties = {
                'name': name_value,
                'description': row.get('description', '').strip(),
            }
            
            # Add utility_type if provided
            utility_type = row.get('utility_type', '').strip().lower()
            if utility_type:
                if utility_type not in VALID_UTILITY_TYPES:
                    return {
                        'error': f"Invalid utility_type '{utility_type}' at row {row_num}. Must be one of: {', '.join(VALID_UTILITY_TYPES)}"
                    }
                properties['utility_type'] = utility_type
            
            # Add subtype or category based on node type
            if node_type in ['Meter', 'Distribution']:
                properties['subtype'] = subtype_or_category
            else:  # Consumer
                properties['category'] = subtype_or_category
            
            # Optional fields
            if row.get('serial_number'):
                properties['serial_number'] = row.get('serial_number').strip()
            if row.get('location'):
                properties['location'] = row.get('location').strip()
            if row.get('installation_date'):
                date_str = row.get('installation_date').strip()
                # Basic date format validation
                if date_str and not _is_valid_date_format(date_str):
                    logger.warning(f"Invalid date format at row {row_num}: {date_str}. Expected YYYY-MM-DD")
                properties['installation_date'] = date_str
            
            node_data = {
                'type': node_type,
                'properties': properties
            }
            
            # Add parent reference if specified
            parent_name = row.get('parent_name', '').strip()
            if parent_name:
                node_data['parent_name'] = parent_name
            
            nodes.append(node_data)
        
        if not nodes:
            return {'error': 'No valid data rows found in CSV. Make sure you have data after the header row.'}
        
        return {'nodes': nodes, 'count': len(nodes)}
        
    except csv.Error as e:
        logger.error(f"CSV parsing error: {e}")
        return {'error': f"Invalid CSV format: {str(e)}"}
    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")
        return {'error': f"Failed to parse CSV: {str(e)}"}


def _is_valid_date_format(date_str):
    """Check if date string matches YYYY-MM-DD format"""
    import re
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(pattern, date_str))
