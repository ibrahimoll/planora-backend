# Planora Backend Instructions for Codex

## Project Overview

Planora is an AI-powered project planning and collaboration system.

Backend stack:
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- JWT authentication

The backend supports:
- Normal registration/login
- Email verification
- Forgot/reset password
- Google login
- Protected routes requiring active and email-verified users
- Personal projects
- Teams
- Team projects
- Tasks
- Team task assignment
- Attachments/comments/notifications/progress features as development continues

## Important Rules

1. Do not change the database design unless the task explicitly asks for database/schema changes.
2. Do not touch `.env` or expose secrets.
3. Do not invent environment variables. Use `app/core/config.py`.
4. Keep routes protected using the current-user dependency where required.
5. Normal users and admins must not bypass authentication.
6. No guest access past authentication.
7. Make minimal, high-confidence changes.
8. Explain every changed file after editing.
9. Prefer fixing one module at a time instead of making huge unrelated changes.

## Commands

Use these commands when checking the backend:

```bash
python -m pytest
uvicorn app.main:app --reload