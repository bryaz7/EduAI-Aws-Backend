import traceback
import logging

from flask import jsonify

from main import app, socketio
from utils.exceptions import ItemNotFoundError, ValidationError, NotificationGenerationError, BadRequestError


@app.errorhandler(ItemNotFoundError)
def handle_item_not_found_error(e):
    logging.exception("An item is not found", exc_info=e)
    return jsonify({"message": str(e)}), 404


@app.errorhandler(ValidationError)
def handle_validation_error(e):
    logging.exception("Validation error", exc_info=e)
    return jsonify({"message": str(e)}), 403


@app.errorhandler(NotificationGenerationError)
def handle_notification_generation_error(e):
    logging.exception("Notification error", exc_info=e)
    return jsonify({"message": str(e)}), 501


@app.errorhandler(BadRequestError)
def handle_bad_request_error(e):
    logging.exception("Bad request error", exc_info=e)
    return jsonify({"message": str(e)}), 400


@app.errorhandler(Exception)
def handle_error(e):
    logging.exception("General error", exc_info=e)
    return jsonify({"message": f"Unexpected error occurred. Detail: {e}"}), 500


@socketio.on_error_default
def error_handler(e):
    logging.exception("Bad request error", exc_info=e)
