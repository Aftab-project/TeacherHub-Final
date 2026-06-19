"""
Hub integration routes.

These routes let the Team Com Flask backend serve the existing
Teacher Feature Hub pages and feature folders from the project root.
"""

import os
from flask import Blueprint, abort, send_from_directory, redirect, url_for
from flask_login import login_required


bp = Blueprint('hub', __name__)

# Project root: .../Aftab Khan - FinalYearProject
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..')
)

# Allowed top-level feature directories from the main project.
ALLOWED_FEATURE_DIRS = {
    'face-attendance',
    'mental-health'
}


def _safe_send_from_root(relative_path):
    """Serve only files that exist inside PROJECT_ROOT."""
    normalized = os.path.normpath(relative_path)

    if normalized.startswith('..') or os.path.isabs(normalized):
        abort(404)

    full_path = os.path.join(PROJECT_ROOT, normalized)
    if not os.path.isfile(full_path):
        abort(404)

    directory = os.path.dirname(normalized)
    filename = os.path.basename(normalized)
    return send_from_directory(
        os.path.join(PROJECT_ROOT, directory),
        filename
    )


@bp.route('/')
@login_required
def hub_home():
    """Main Teacher Feature Hub home page."""
    return _safe_send_from_root('index.html')


@bp.route('/index.html')
@login_required
def hub_home_alias():
    return _safe_send_from_root('index.html')


@bp.route('/login.html')
def hub_login():
    return _safe_send_from_root('login.html')


@bp.route('/style.css')
def hub_style():
    return _safe_send_from_root('style.css')


@bp.route('/auth.js')
def hub_auth():
    return _safe_send_from_root('auth.js')


@bp.route('/script.js')
def hub_script():
    return _safe_send_from_root('script.js')


@bp.route('/team-com')
@bp.route('/team-com/')
@bp.route('/team-com/index.html')
@login_required
def open_team_com_section():
    """Visible entry path from the main hub into the single Team Com backend."""
    return redirect(url_for('dashboard.index'))


@bp.route('/<feature_dir>/<path:filename>')
@login_required
def hub_feature_assets(feature_dir, filename):
    """Serve files for approved feature folders only."""
    if feature_dir not in ALLOWED_FEATURE_DIRS:
        abort(404)

    return _safe_send_from_root(os.path.join(feature_dir, filename))