from flask import jsonify, request

from db.models import User, UserProgressTracking
from main import db, app
from utils.auth import validate_token


@app.route('/api/user-progress-tracking/get-latest-progress', methods=['GET'])
@validate_token
def get_latest_progress():
    user_id = request.args.get('user_id', type=int)
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"})

    user_latest_progress_tracking = UserProgressTracking.get_latest_progress_tracking(user_id)
    if not user_latest_progress_tracking:
        return jsonify(UserProgressTracking.get_zeros(user_id).to_dict())
    else:
        return jsonify(user_latest_progress_tracking.to_dict())


@app.route('/api/user-progress-tracking/get-line-chart-data', methods=['GET'])
@validate_token
def get_line_chart_data():
    user_id = request.args.get('user_id', type=int)
    skill = request.args.get('skill')
    days = request.args.get('days', type=int, default=7)
    freq = request.args.get('freq', default="day")
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    if skill is None:
        return jsonify({"message": "Skill cannot be null"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"})

    records = UserProgressTracking.get_line_chart_data(
        user_id=user_id,
        skill=skill,
        days=days,
        freq=freq,
        from_date=from_date,
        to_date=to_date
    )
    return records
