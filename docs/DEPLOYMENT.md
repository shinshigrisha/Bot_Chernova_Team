# Deployment

## Services
- postgres
- redis
- minio (S3-compatible)
- bot (aiogram)
- worker (celery/rq)
- scheduler (optional separate process)

## Environment variables
See `.env.example`.

## Migrations
- Run `alembic upgrade head` on deploy
- Always backup DB before migrations

## Backups
- Daily DB dump
- S3/MinIO bucket versioning recommended

## Updating
1) Pull code
2) Build images
3) Run migrations
4) Restart services
5) Verify health checks

## Rollback
- Restore DB backup
- Deploy previous image tag
