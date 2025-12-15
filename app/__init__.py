from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.utils import Neo4jJSONEncoder
import logging

def create_app():
    """Create and configure Flask application"""
    import os
    # Get the base directory (one level up from app/)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    app = Flask(__name__, 
                template_folder=os.path.join(base_dir, 'templates'),
                static_folder=os.path.join(base_dir, 'static'))
    app.config.from_object(Config)
    
    # Set custom JSON encoder for Neo4j types
    app.json_encoder = Neo4jJSONEncoder
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Enable CORS
    CORS(app)
    
    # Initialize services with app context
    with app.app_context():
        from app.services.neo4j_service import init_neo4j_service
        from app.services.timescale_service import init_timescale_service
        
        neo4j_svc = init_neo4j_service(
            app.config['NEO4J_URI'],
            app.config['NEO4J_USER'],
            app.config['NEO4J_PASSWORD']
        )
        # Initialize constraints once at startup
        neo4j_svc.init_database_constraints()
        
        init_timescale_service(
            app.config['POSTGRES_HOST'],
            app.config['POSTGRES_PORT'],
            app.config['POSTGRES_DB'],
            app.config['POSTGRES_USER'],
            app.config['POSTGRES_PASSWORD']
        )
    
    # Register blueprints
    from app.routes import projects, nodes, graph, readings, bulk, categories, settings
    app.register_blueprint(projects.bp)
    app.register_blueprint(nodes.bp)
    app.register_blueprint(graph.bp)
    app.register_blueprint(readings.bp)
    app.register_blueprint(bulk.bp)
    app.register_blueprint(categories.bp)
    app.register_blueprint(settings.bp)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found', 'message': str(error)}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error', 'message': str(error)}, 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Bad request', 'message': str(error)}, 400
    
    # Main route
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')
    
    # Settings route
    @app.route('/settings')
    def settings():
        from flask import render_template
        return render_template('settings.html')
    
    return app
