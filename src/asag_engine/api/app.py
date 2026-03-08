import os
from flask import Flask, jsonify
from dotenv import load_dotenv
from asag_engine.db import init_db

from .health_routes import bp as health_bp
from .papers_routes import bp as papers_bp
from .questions_routes import bp as questions_bp
from .grading_routes import bp as grading_bp
from .submissions_routes import bp as submissions_bp


load_dotenv()
def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__)

    auto_create = os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true"
    init_db(auto_create=auto_create)

    app.register_blueprint(health_bp)
    app.register_blueprint(papers_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(grading_bp)
    app.register_blueprint(submissions_bp)

    @app.get("/")
    def root():
        return jsonify({
            "name": "ASAG Engine Option A (MindNLP/Pangu) + Paper Upload",
            "status": "ok",
            "endpoints": [
                "/api/v1/health",
                "/api/v1/papers/upload [POST multipart]",
                "/api/v1/papers [GET]",
                "/api/v1/papers/<id> [GET]",
                "/api/v1/questions [POST,GET]",
                "/api/v1/questions/<id> [GET]",
                "/api/v1/questions/<id>/rubric [GET]",
                "/api/v1/grade [POST]",
                "/api/v1/submissions [GET]",
                "/api/v1/submissions/<id> [GET]",
                "/api/v1/submissions/<id>/override [PATCH]"
            ]
        })

    return app

if __name__ == "__main__":
    app = create_app()
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug, use_reloader=False)