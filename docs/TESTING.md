# Planora Backend Testing

## Push Notification API Tests

The push notification import guard does not need a database:

```bash
python -m pytest tests/test_00_push_notification_import_guard.py -q
```

The push notification API tests need a dedicated PostgreSQL test database. Set:

```bash
TEST_DATABASE_URL=postgresql://username:password@host:5432/planora_test
```

Then run:

```bash
python -m pytest tests/test_18_push_notifications_api.py -q
```

Do not reuse production `DATABASE_URL` as `TEST_DATABASE_URL`. The test
fixtures create and drop tables in the configured test database.

## GitHub Actions

Add this repository secret when you want CI to run the push notification API
tests:

```text
TEST_DATABASE_URL
```

Use a Neon branch or other isolated PostgreSQL database created only for tests.
Leave the secret unset if no test database is available; the import guard still
runs and the API test step is skipped clearly.
