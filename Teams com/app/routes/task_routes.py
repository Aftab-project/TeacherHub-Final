"""
Task routes for Team Collaboration Platform.

This module covers task management lifecycle:
1. List team tasks with status filtering
2. Create tasks and optionally assign during creation
3. View task details
4. Update task status (todo/in_progress/done)
5. Reassign tasks
6. Delete tasks
7. Return task summary counts for dashboard widgets
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, Task, Team, TeamMember, User, Notification
from datetime import datetime

# ===== BLUEPRINT SETUP =====
# All routes in this module are mounted at /tasks/*
bp = Blueprint('tasks', __name__, url_prefix='/tasks')


@bp.route('/team/<int:team_id>')
@login_required
def list_team_tasks(team_id):
    """List all tasks in a team."""
    
    team = Team.query.get_or_404(team_id)
    
    # Authorization
    if team not in current_user.teams:
        flash('You do not have access to this team.', 'error')
        return redirect(url_for('teams.list_teams'))
    
    # Optional filter from query string (?status=todo|in_progress|done|all)
    status = request.args.get('status', 'all')
    
    # Base query = tasks belonging to this team
    query = Task.query.filter_by(team_id=team_id)
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    # Earliest due tasks first for better planning visibility
    tasks = query.order_by(Task.due_date.asc()).all()
    
    return render_template('tasks/list.html', team=team, tasks=tasks, status=status)


@bp.route('/team/<int:team_id>/create', methods=['GET', 'POST'])
@login_required
def create_task(team_id):
    """Create a new task."""
    
    team = Team.query.get_or_404(team_id)
    
    # Authorization
    if team not in current_user.teams:
        flash('You do not have access to this team.', 'error')
        return redirect(url_for('teams.list_teams'))
    
    if request.method == 'POST':
        # Read form values
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        assigned_to_id = request.form.get('assigned_to', type=int)
        priority = request.form.get('priority', 'medium')
        due_date_str = request.form.get('due_date')
        
        # Validation
        if not title or len(title) < 3:
            flash('Task title must be at least 3 characters.', 'error')
            return redirect(url_for('tasks.create_task', team_id=team_id))
        
        # Parse optional due date; keep None if missing/invalid
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.fromisoformat(due_date_str)
            except:
                pass
        
        # ===== CREATE TASK =====
        task = Task(
            title=title,
            description=description,
            team_id=team_id,
            assigned_to_id=assigned_to_id,
            priority=priority,
            due_date=due_date,
            created_by_id=current_user.id,
            status='todo'
        )
        db.session.add(task)
        
        # Notify assignee if task was assigned to another person
        if assigned_to_id and assigned_to_id != current_user.id:
            notification = Notification(
                user_id=assigned_to_id,
                type='task_assigned',
                title=f'Task assigned: {title}',
                message=f'{current_user.username} assigned you a task: {title}',
                related_id=task.id
            )
            db.session.add(notification)
        
        db.session.commit()
        
        flash('Task created successfully.', 'success')
        return redirect(url_for('tasks.list_team_tasks', team_id=team_id))
    
    # GET: render form and provide team members for assignee dropdown
    members = TeamMember.query.filter_by(team_id=team_id).all()
    return render_template('tasks/create.html', team=team, members=members)


@bp.route('/<int:task_id>')
@login_required
def view_task(task_id):
    """View task details."""
    
    task = Task.query.get_or_404(task_id)
    team = task.team
    
    # Authorization
    # Team-level access check protects task details
    if team not in current_user.teams:
        flash('You do not have access to this task.', 'error')
        return redirect(url_for('dashboard.index'))
    
    return render_template('tasks/view.html', task=task, team=team)


@bp.route('/<int:task_id>/status', methods=['POST'])
@login_required
def update_task_status(task_id):
    """
    Update task status.
    
    Valid statuses: 'todo', 'in_progress', 'done'
    """
    
    task = Task.query.get_or_404(task_id)
    team = task.team
    
    # Authorization
    if team not in current_user.teams:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Normalize status input to lowercase for consistency
    status = request.form.get('status', '').lower()
    
    if status not in ['todo', 'in_progress', 'done']:
        return jsonify({'error': 'Invalid status'}), 400
    
    # Capture old state for notification message
    old_status = task.status
    task.status = status
    task.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Notify creator when someone else changes task progress
    if task.created_by_id != current_user.id:
        notification = Notification(
            user_id=task.created_by_id,
            type='task_updated',
            title=f'Task status updated: {task.title}',
            message=f'Task status changed from {old_status} to {status}',
            related_id=task_id
        )
        db.session.add(notification)
        db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/<int:task_id>/assign', methods=['POST'])
@login_required
def assign_task(task_id):
    """Assign task to a team member."""
    
    task = Task.query.get_or_404(task_id)
    team = task.team
    
    # Current implementation: only task creator can reassign
    if task.created_by_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    assigned_to_id = request.form.get('assigned_to', type=int)
    
    # Prevent assigning tasks to users outside the team
    if assigned_to_id:
        member = TeamMember.query.filter_by(
            team_id=team.id,
            user_id=assigned_to_id
        ).first()
        
        if not member:
            return jsonify({'error': 'User is not a team member'}), 400
    
    # Update assignee
    task.assigned_to_id = assigned_to_id
    db.session.commit()
    
    # Notify new assignee (unless assigning to self)
    if assigned_to_id and assigned_to_id != current_user.id:
        notification = Notification(
            user_id=assigned_to_id,
            type='task_assigned',
            title=f'Task assigned: {task.title}',
            message=f'{current_user.username} assigned you the task: {task.title}',
            related_id=task_id
        )
        db.session.add(notification)
        db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    """Delete task (only creator)."""
    
    task = Task.query.get_or_404(task_id)
    
    # Authorization
    if task.created_by_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Permanently delete task row
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/api/team/<int:team_id>/summary')
@login_required
def api_task_summary(team_id):
    """
    API: Get task summary for team.
    
    Returns counts of tasks by status.
    """
    
    team = Team.query.get_or_404(team_id)
    
    if team not in current_user.teams:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Compute per-status counts for quick charts/widgets
    todo_count = Task.query.filter_by(team_id=team_id, status='todo').count()
    in_progress_count = Task.query.filter_by(team_id=team_id, status='in_progress').count()
    done_count = Task.query.filter_by(team_id=team_id, status='done').count()
    
    return jsonify({
        'todo': todo_count,
        'in_progress': in_progress_count,
        'done': done_count,
        'total': todo_count + in_progress_count + done_count
    })
