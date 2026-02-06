"""Error handlers registration."""

from flask import Flask, jsonify, render_template, request


def register_error_handlers(app: Flask) -> None:
    """Register common error handlers for 404 and 500 responses."""

    @app.errorhandler(404)
    def not_found(error):
        if (
            request.accept_mimetypes.accept_json
            and not request.accept_mimetypes.accept_html
        ):
            return jsonify({"error": "Not Found"}), 404
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        if (
            request.accept_mimetypes.accept_json
            and not request.accept_mimetypes.accept_html
        ):
            return jsonify({"error": "Internal Server Error"}), 500
        return render_template("500.html"), 500
