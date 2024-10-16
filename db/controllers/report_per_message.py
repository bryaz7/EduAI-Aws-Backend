from flask import jsonify, request
from main import db, app
from db.models.report_per_message import ReportPerMessage
from utils.auth import validate_token


@app.route('/api/report_per_message', methods=['POST'])
@validate_token
def create_report_per_message():
    try:
        data = request.get_json()
        # history_message_id = data.get('history_message_id')
        # detail = data.get('detail')
        # timestamp = data.get('timestamp')

        report = ReportPerMessage.from_dict(data)
        db.session.add(report)
        db.session.commit()
        
        return jsonify({'message': 'This message report created successfully'}), 201
    except Exception as e:
        return jsonify({'message': 'Error from server', "error": e}), 500
    

@app.route('/api/report_per_message', methods=['DELETE'])
@validate_token
def delete_report_per_message():
    try:
        data = request.get_json()
        history_message_id = data.get('history_message_id')
        timestamp = data.get('timestamp')
        
        # report = db.session.get(ReportPerMessage, history_message_id, timestamp)
        report = db.session.query(ReportPerMessage).filter_by(history_message_id=history_message_id, timestamp=timestamp).first()
        if not report:
            return jsonify({'message': 'The report not found'}), 404

        report.soft_delete()
        db.session.commit()
        
        return jsonify({'message': 'This message report delete successfully'}), 201
    except Exception as e:
        return jsonify({'message': 'Error from server', "error": e}), 500
