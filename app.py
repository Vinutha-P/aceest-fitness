"""ACEest Fitness & Gym - Flask application entry point.

Exposes the application factory and creates the WSGI application instance
used by both the local dev server and the production container.
"""
from aceest import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
