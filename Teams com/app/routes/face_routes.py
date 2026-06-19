"""
Face-attendance persistence routes.

These endpoints let the face recognition page save and restore its student
roster from SQLite instead of relying only on browser localStorage.
"""

import json

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.models import db, FaceStudent


bp = Blueprint('face_students', __name__, url_prefix='/api/face-students')


def _group_students(rows):
    """Convert FaceStudent rows into the class-grouped payload used by the page."""
    grouped = {}

    for row in rows:
        grouped.setdefault(row.class_name, []).append(row.to_dict())

    return grouped


@bp.route('', methods=['GET'])
@login_required
def list_face_students():
    """Return all saved face students for the current user."""
    rows = (
        FaceStudent.query
        .filter_by(user_id=current_user.id)
        .order_by(FaceStudent.class_name.asc(), FaceStudent.name.asc())
        .all()
    )
    return jsonify({'studentsByClass': _group_students(rows)})


@bp.route('/sync', methods=['PUT'])
@login_required
def sync_face_students():
    """Replace the current user's roster with the payload from the browser."""
    payload = request.get_json(silent=True) or {}
    students_by_class = payload.get('studentsByClass')

    if not isinstance(students_by_class, dict):
        return jsonify({'error': 'studentsByClass must be an object'}), 400

    # Step 1: Validate all student records before making any database changes.
    # This ensures we don't delete existing records if new ones are invalid.
    validated_students = []

    for class_name, class_students in students_by_class.items():
        if not isinstance(class_name, str) or not class_name.strip() or not isinstance(class_students, list):
            continue

        normalized_class_name = class_name.strip()

        for record in class_students:
            if not isinstance(record, dict):
                continue

            name = record.get('name')
            photo_data_url = record.get('photoDataUrl')
            descriptor = record.get('descriptor')

            # Validate required fields.
            if not isinstance(name, str) or not name.strip():
                continue
            if not isinstance(photo_data_url, str) or not photo_data_url:
                continue
            if not isinstance(descriptor, list):
                continue

            # All validations passed; record this student for insertion.
            validated_students.append({
                'class_name': normalized_class_name,
                'name': name.strip(),
                'email': record.get('email') if isinstance(record.get('email'), str) else '',
                'photo_data_url': photo_data_url,
                'descriptor_json': json.dumps(descriptor)
            })

    # Step 2: Delete old records only after validation succeeds.
    # Then insert all validated students in a single transaction.
    # If anything fails, the transaction rolls back and data is not lost.
    try:
        FaceStudent.query.filter_by(user_id=current_user.id).delete()

        for student_data in validated_students:
            student = FaceStudent(
                user_id=current_user.id,
                **student_data
            )
            db.session.add(student)

        db.session.commit()
        saved_count = len(validated_students)

        return jsonify({'success': True, 'saved': saved_count})

    except Exception as error:
        # If any error occurs during save, roll back the transaction.
        # This prevents data loss if the commit fails.
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(error)}'}), 500
