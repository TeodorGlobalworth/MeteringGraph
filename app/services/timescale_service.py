import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class TimescaleService:
    """Service for TimescaleDB/PostgreSQL operations"""
    
    def __init__(self, host, port, database, user, password):
        self.conn_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = psycopg2.connect(**self.conn_params)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def create_project(self, name, utility_type='multi'):
        """Create a new project (utility_type defaults to 'multi' as projects have all 3 utilities)"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO projects (name, utility_type)
                    VALUES (%s, %s)
                    RETURNING id, name, utility_type, created_at, updated_at
                """, (name, utility_type))
                return dict(cur.fetchone())
    
    def get_all_projects(self):
        """Get all projects"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, name, utility_type, created_at, updated_at
                    FROM projects
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in cur.fetchall()]
    
    def get_project(self, project_id):
        """Get a project by ID"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, name, utility_type, created_at, updated_at
                    FROM projects
                    WHERE id = %s
                """, (project_id,))
                result = cur.fetchone()
                return dict(result) if result else None
    
    def delete_project(self, project_id):
        """Delete a project (cascade deletes readings and categories)"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
                return cur.rowcount > 0
    
    def create_category(self, project_id, node_type, category_name):
        """Create a new category for a project"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                try:
                    cur.execute("""
                        INSERT INTO categories (project_id, node_type, category_name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (project_id, node_type, category_name) DO NOTHING
                        RETURNING id, project_id, node_type, category_name, created_at
                    """, (project_id, node_type, category_name))
                    result = cur.fetchone()
                    return dict(result) if result else None
                except psycopg2.IntegrityError:
                    return None
    
    def get_categories(self, project_id, node_type=None):
        """Get categories for a project, optionally filtered by node type"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if node_type:
                    cur.execute("""
                        SELECT id, project_id, node_type, category_name, created_at
                        FROM categories
                        WHERE project_id = %s AND node_type = %s
                        ORDER BY category_name
                    """, (project_id, node_type))
                else:
                    cur.execute("""
                        SELECT id, project_id, node_type, category_name, created_at
                        FROM categories
                        WHERE project_id = %s
                        ORDER BY node_type, category_name
                    """, (project_id,))
                return [dict(row) for row in cur.fetchall()]
    
    def seed_default_categories(self, project_id):
        """Seed default categories for a new project"""
        default_categories = [
            ('Consumer', 'Lighting'),
            ('Consumer', 'HVAC'),
            ('Consumer', 'Elevator'),
            ('Consumer', 'Pumps'),
            ('Consumer', 'Ventilation'),
            ('Consumer', 'Outlets'),
            ('Meter', 'Main'),
            ('Meter', 'Submeter'),
            ('Distribution', 'Main Panel'),
            ('Distribution', 'Sub Panel')
        ]
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for node_type, category_name in default_categories:
                    try:
                        cur.execute("""
                            INSERT INTO categories (project_id, node_type, category_name)
                            VALUES (%s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (project_id, node_type, category_name))
                    except Exception as e:
                        logger.warning(f"Failed to seed category {node_type}/{category_name}: {e}")
    
    def add_reading(self, project_id, node_id, value, unit, timestamp=None):
        """Add a meter reading"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if timestamp:
                    cur.execute("""
                        INSERT INTO readings (time, project_id, node_id, value, unit)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING time, project_id, node_id, value, unit, created_at
                    """, (timestamp, project_id, node_id, value, unit))
                else:
                    cur.execute("""
                        INSERT INTO readings (time, project_id, node_id, value, unit)
                        VALUES (NOW(), %s, %s, %s, %s)
                        RETURNING time, project_id, node_id, value, unit, created_at
                    """, (project_id, node_id, value, unit))
                return dict(cur.fetchone())
    
    def get_readings(self, project_id, node_id, limit=50, offset=0):
        """Get readings for a node"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT time, project_id, node_id, value, unit, created_at
                    FROM readings
                    WHERE project_id = %s AND node_id = %s
                    ORDER BY time DESC
                    LIMIT %s OFFSET %s
                """, (project_id, node_id, limit, offset))
                return [dict(row) for row in cur.fetchall()]
    
    def get_readings_range(self, project_id, node_id, start_time, end_time):
        """Get readings for a node within a time range"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT time, project_id, node_id, value, unit
                    FROM readings
                    WHERE project_id = %s AND node_id = %s 
                      AND time BETWEEN %s AND %s
                    ORDER BY time ASC
                """, (project_id, node_id, start_time, end_time))
                return [dict(row) for row in cur.fetchall()]
    
    def get_daily_aggregates(self, project_id, node_id, days=30):
        """Get daily aggregated readings"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT day, avg_value, min_value, max_value, reading_count
                    FROM daily_readings
                    WHERE project_id = %s AND node_id = %s
                      AND day >= NOW() - INTERVAL '%s days'
                    ORDER BY day ASC
                """, (project_id, node_id, days))
                return [dict(row) for row in cur.fetchall()]
    
    def delete_readings(self, project_id):
        """Delete all readings for a project"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM readings WHERE project_id = %s", (project_id,))
                return cur.rowcount
    
    def get_all_readings_for_export(self, project_id):
        """Get all readings for a project for export"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT time, node_id, value, unit
                    FROM readings
                    WHERE project_id = %s
                    ORDER BY time ASC
                """, (project_id,))
                return [dict(row) for row in cur.fetchall()]
    
    # ===== Consumer Category Settings =====
    
    def get_consumer_categories(self):
        """Get all consumer category settings"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, category_name, display_name, icon_name, color, 
                           sort_order, is_active, created_at, updated_at
                    FROM consumer_category_settings
                    ORDER BY sort_order, category_name
                """)
                return [dict(row) for row in cur.fetchall()]
    
    def get_active_consumer_categories(self):
        """Get only active consumer category settings (for dropdowns)"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT category_name, display_name, icon_name, color
                    FROM consumer_category_settings
                    WHERE is_active = TRUE
                    ORDER BY sort_order, category_name
                """)
                return [dict(row) for row in cur.fetchall()]
    
    def create_consumer_category(self, category_name, display_name, icon_name='box-fill', 
                                  color='#868e96', sort_order=50):
        """Create a new consumer category"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO consumer_category_settings 
                        (category_name, display_name, icon_name, color, sort_order)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, category_name, display_name, icon_name, color, 
                              sort_order, is_active, created_at, updated_at
                """, (category_name, display_name, icon_name, color, sort_order))
                return dict(cur.fetchone())
    
    def update_consumer_category(self, category_id, display_name=None, icon_name=None, 
                                  color=None, sort_order=None, is_active=None):
        """Update a consumer category"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build dynamic update query
                updates = []
                params = []
                
                if display_name is not None:
                    updates.append("display_name = %s")
                    params.append(display_name)
                if icon_name is not None:
                    updates.append("icon_name = %s")
                    params.append(icon_name)
                if color is not None:
                    updates.append("color = %s")
                    params.append(color)
                if sort_order is not None:
                    updates.append("sort_order = %s")
                    params.append(sort_order)
                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)
                
                if not updates:
                    return None
                
                updates.append("updated_at = NOW()")
                params.append(category_id)
                
                query = f"""
                    UPDATE consumer_category_settings
                    SET {', '.join(updates)}
                    WHERE id = %s
                    RETURNING id, category_name, display_name, icon_name, color, 
                              sort_order, is_active, created_at, updated_at
                """
                cur.execute(query, params)
                result = cur.fetchone()
                return dict(result) if result else None
    
    def delete_consumer_category(self, category_id):
        """Delete a consumer category"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM consumer_category_settings
                    WHERE id = %s
                """, (category_id,))
                return cur.rowcount > 0

# Global service instance
_timescale_service = None

def init_timescale_service(host, port, database, user, password):
    """Initialize TimescaleDB service with config"""
    global _timescale_service
    _timescale_service = TimescaleService(host, port, database, user, password)
    return _timescale_service

def get_timescale_service():
    """Get TimescaleDB service instance"""
    if _timescale_service is None:
        raise RuntimeError("TimescaleDB service not initialized. Call init_timescale_service first.")
    return _timescale_service
