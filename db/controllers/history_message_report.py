from flask import jsonify, request
from main import db, app
from db.models.history_message_report import HistoryMessageReport
from db.models.history_message import HistoryMessage
from utils.auth import validate_token


@app.route('/api/history-message-reports', methods=['POST'])
@validate_token
def create_history_message_report():
    data = request.get_json()
    history_message_id = data.get('history_message_id')
    detail = data.get('detail')

    if not history_message_id or not detail:
        return jsonify({'error': 'Missing required fields (either history_message_id or detail)'}), 400

    history_message = db.session.get(HistoryMessage, history_message_id)
    if not history_message:
        return jsonify({'error': 'HistoryMessage not found'}), 404

    report = HistoryMessageReport.from_dict(data)
    db.session.add(report)
    db.session.commit()

    return jsonify({'message': 'History message report created successfully'}), 201


@app.route('/api/history-message-reports/<int:report_id>', methods=['GET'])
@validate_token
def get_history_message_report(report_id):
    report = HistoryMessageReport.query.get(report_id)
    if not report:
        return jsonify({'error': 'History message report not found'}), 404
    return jsonify(report.to_dict())


@app.route('/api/history-message-reports/<int:report_id>', methods=['PUT'])
@validate_token
def update_history_message_report(report_id):
    data = request.get_json()
    report = db.session.get(HistoryMessageReport, report_id)

    if not report:
        return jsonify({'error': 'History message report not found'}), 404

    new_detail = data.get('detail')
    if not new_detail:
        return jsonify({'error': 'Missing detail field'}), 400

    report.update_fields(**data)
    db.session.commit()

    return jsonify({'message': 'History message report updated successfully'})


@app.route('/api/history-message-reports/<int:report_id>', methods=['DELETE'])
@validate_token
def delete_history_message_report(report_id):
    report = db.session.get(HistoryMessageReport, report_id)

    if not report:
        return jsonify({'error': 'History message report not found'}), 404

    report.soft_delete()
    db.session.commit()

    return jsonify({'message': 'History message report deleted successfully'})
