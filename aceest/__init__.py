"""ACEest Fitness & Gym application package.

Contains the Flask application factory, blueprint registration and
database initialisation logic.
"""
import os

from flask import Flask, jsonify

from .db import close_db, init_db


def create_app(test_config=None):
    """Application factory.

    Args:
        test_config: Optional dict of overrides used by the test suite.

    Returns:
        A configured :class:`flask.Flask` application.
    """
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        DATABASE=os.environ.get(
            "DATABASE", os.path.join(app.instance_path, "aceest_fitness.db")
        ),
        TESTING=False,
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    app.teardown_appcontext(close_db)
    register_blueprints(app)

    # Create the schema on startup so a fresh container is immediately usable.
    with app.app_context():
        init_db()

    @app.get("/health")
    def health():
        """Simple liveness probe used by Docker and the CI pipeline."""
        return jsonify({"status": "healthy", "service": "aceest-fitness"})

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(_error):
        return jsonify({"error": "Internal server error"}), 500

    return app


def register_blueprints(app):
    """Attach all HTTP blueprints to the given application."""
    from .clients import bp as clients_bp
    from .workouts import bp as workouts_bp

    app.register_blueprint(clients_bp)
    app.register_blueprint(workouts_bp)
