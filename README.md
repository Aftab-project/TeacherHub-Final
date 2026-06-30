# TeacherHub Final Project

This repository contains the final-year project submission for a Microsoft Teams-inspired collaboration platform.

## Project Location

The full web application is inside:

- [Teams com](Teams%20com/)

## Quick Summary

TeacherHub is a Flask-based team collaboration platform with:

- User authentication and profile management
- Team and channel management
- Channel and direct messaging
- Mentions and notifications
- File sharing
- Task management
- Call/transcription-related workflows

## Complete Functionality Summary

1. Authentication and user accounts
	- Users can register, log in, log out, and update profile details.
	- Passwords are stored securely using hashing.

2. Team workspace management
	- Users can create teams, join teams by code, and manage member roles.
	- Team owners/admins can control membership and settings.

3. Channel communication
	- Each team can have multiple channels for topic-based discussion.
	- Members can create, edit, delete, and search channel messages.

4. Direct messaging
	- Users can message each other privately in one-to-one conversations.
	- Direct message history is persisted in the database.

5. Mentions and notifications
	- Mentions trigger notifications for tagged users.
	- Task assignment and team activity also generate notifications.

6. File sharing
	- Users can upload and download files within team/channel contexts.
	- File access and metadata are managed by the application.

7. Task management
	- Teams can create tasks with assignee, status, priority, and due dates.
	- Members can track and update task progress.

8. Calls and transcripts
	- The project includes call-related workflows and transcript storage/retrieval.
	- Transcript records support communication review and analysis.

9. Security and reliability
	- Role checks, form validation, and ORM-based data access protect operations.
	- The project includes tests and reliability fixes documented in report logs.

## How To Run

Open a terminal in the `Teams com` folder and run:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Then open:

- http://localhost:5000

## Main Documentation

- [Teams com/README.md](Teams%20com/README.md)
- [Teams com/report.md](Teams%20com/report.md)
- [FinalReport.md](FinalReport.md)
