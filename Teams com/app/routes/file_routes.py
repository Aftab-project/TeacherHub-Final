"""
File routes for Team Collaboration Platform.

This module handles file lifecycle operations:
1. List files at team or channel scope
2. Upload files with extension validation
3. Download files with access control
4. Delete files (uploader-only)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import login_required, current_user
from app.models import db, File, Team, Channel, TeamMember
from werkzeug.utils import secure_filename
from config import Config
import os

# ===== BLUEPRINT SETUP =====
# Every route in this file starts with /files/*
bp = Blueprint('files', __name__, url_prefix='/files')


def allowed_file(filename):
    """Check if file extension is allowed."""
    # Must include extension and be in configured allow-list
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


@bp.route('/team/<int:team_id>')
@login_required
def list_team_files(team_id):
    """List files shared in a team."""
    
    team = Team.query.get_or_404(team_id)
    
    # Check authorization
    if team not in current_user.teams:
        flash('You do not have access to this team.', 'error')
        return redirect(url_for('teams.list_teams'))
    
    # Newest uploads shown first
    files = File.query.filter_by(team_id=team_id).order_by(
        File.created_at.desc()
    ).all()
    
    return render_template('files/team_files.html', team=team, files=files)


@bp.route('/channel/<int:channel_id>')
@login_required
def list_channel_files(channel_id):
    """List files shared in a channel."""
    
    channel = Channel.query.get_or_404(channel_id)
    team = channel.team
    
    # Check authorization
    if team not in current_user.teams:
        flash('You do not have access to this channel.', 'error')
        return redirect(url_for('dashboard.index'))
    
    # Newest uploads shown first
    files = File.query.filter_by(channel_id=channel_id).order_by(
        File.created_at.desc()
    ).all()
    
    return render_template('files/channel_files.html', channel=channel, team=team, files=files)


@bp.route('/team/<int:team_id>/upload', methods=['POST'])
@login_required
def upload_to_team(team_id):
    """Upload file to team."""
    
    team = Team.query.get_or_404(team_id)
    
    # Authorization
    member = TeamMember.query.filter_by(
        team_id=team_id,
        user_id=current_user.id
    ).first()
    
    if not member:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Validate multipart payload contains file field
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # ===== SAVE TO DISK =====
    # Sanitize filename to avoid path traversal or unsafe chars
    filename = secure_filename(file.filename)
    # Add timestamp to filename to prevent conflicts
    import time
    filename = f"{int(time.time())}_{filename}"
    
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # Capture metadata for database row
    file_size = os.path.getsize(filepath)
    mime_type = file.content_type
    
    # Persist metadata (original name + stored path)
    file_record = File(
        filename=secure_filename(file.filename),  # Store original name
        filepath=filename,  # Store relative path
        file_size=file_size,
        mime_type=mime_type,
        uploaded_by_id=current_user.id,
        team_id=team_id
    )
    db.session.add(file_record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'file_id': file_record.id,
        'filename': file_record.filename
    })


@bp.route('/channel/<int:channel_id>/upload', methods=['POST'])
@login_required
def upload_to_channel(channel_id):
    """Upload file to channel."""
    
    channel = Channel.query.get_or_404(channel_id)
    team = channel.team
    
    # Authorization
    if team not in current_user.teams:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if file provided
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    
    # ===== SAVE TO DISK =====
    filename = secure_filename(file.filename)
    import time
    filename = f"{int(time.time())}_{filename}"
    
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # Capture metadata for db
    file_size = os.path.getsize(filepath)
    mime_type = file.content_type
    
    # Save file metadata in File table
    file_record = File(
        filename=secure_filename(file.filename),
        filepath=filename,
        file_size=file_size,
        mime_type=mime_type,
        uploaded_by_id=current_user.id,
        channel_id=channel_id,
        team_id=team.id
    )
    db.session.add(file_record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'file_id': file_record.id,
        'filename': file_record.filename
    })


@bp.route('/<int:file_id>/download')
@login_required
def download_file(file_id):
    """
    Download a file.
    
    Security:
    - Verify user has access to team/channel
    - Use secure_filename to prevent directory traversal
    - Send file from restricted upload folder
    """
    
    file_record = File.query.get_or_404(file_id)
    
    # Authorization depends on where file belongs
    if file_record.team_id:
        team = Team.query.get(file_record.team_id)
        if team not in current_user.teams:
            return jsonify({'error': 'Unauthorized'}), 403
    elif file_record.channel_id:
        channel = Channel.query.get(file_record.channel_id)
        if channel.team not in current_user.teams:
            return jsonify({'error': 'Unauthorized'}), 403
    
    # Stream file from configured upload directory
    try:
        return send_from_directory(
            Config.UPLOAD_FOLDER,
            file_record.filepath,
            as_attachment=True,
            download_name=file_record.filename
        )
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404


@bp.route('/<int:file_id>/delete', methods=['POST'])
@login_required
def delete_file(file_id):
    """Delete a file (only uploader can delete)."""
    
    file_record = File.query.get_or_404(file_id)
    
    # Authorization: only uploader
    if file_record.uploaded_by_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Remove physical file first (if still present)
    filepath = os.path.join(Config.UPLOAD_FOLDER, file_record.filepath)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except:
            pass  # Continue even if file deletion fails
    
    # Remove metadata row from database
    db.session.delete(file_record)
    db.session.commit()
    
    return jsonify({'success': True})
