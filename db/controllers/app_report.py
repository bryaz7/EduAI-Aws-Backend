from flask import jsonify, request
from main import db, app
from db.models import AppReport, User
from services.aws_service import register_image
from utils.auth import validate_token


@app.route('/api/app-reports/<int:id>', methods=['GET'])
@validate_token
def get_app_report(id):
    app_report = db.session.get(AppReport, id)
    if not app_report:
        return jsonify({'error': 'AppReport not found'}), 404
    return jsonify(app_report.to_dict())


@app.route('/api/app-reports', methods=['POST'])
@validate_token
def create_app_report():
    category = request.form.get("category")
    detail = request.form.get("detail")
    user_id = request.form.get("user_id", type=int)
    images = request.files.getlist("images")

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Push uploaded images to S3 and record image_url to the array
    media = []

    for image in images:
        image_mimetype = image.mimetype
        image_filename = image.filename
        if image_mimetype in ["image/jpeg", "image/png"]:
            media.append(register_image(image.read(), user_id, des="app_report")[0])
        elif image_mimetype == "":
            pass
        else:
            return jsonify({"message": f"Invalid file type found: {image_filename}"}), 400

    app_report_dict = {
        "category": category,
        "detail": detail,
        "user_id": user_id,
        "media": media
    }
    app_report = AppReport.from_dict(app_report_dict)
    db.session.add(app_report)
    db.session.commit()
    return jsonify({'message': 'Create AppReport successfully'}), 201


@app.route('/api/app-reports/<int:id>', methods=['PUT'])
@validate_token
def update_app_report(id):
    app_report = db.session.get(AppReport, id)
    if not app_report:
        return jsonify({'error': 'AppReport not found'}), 404
    data = request.get_json()
    app_report.update_fields(**data)
    db.session.commit()
    return jsonify({'message': 'Create AppReport successfully'})


@app.route('/api/app-reports/<int:id>', methods=['DELETE'])
@validate_token
def delete_app_report(id):
    app_report = db.session.get(AppReport, id)
    if not app_report:
        return jsonify({'error': 'AppReport not found'}), 404
    app_report.soft_delete()
    db.session.commit()
    return jsonify({'message': 'AppReport deleted'}), 200
