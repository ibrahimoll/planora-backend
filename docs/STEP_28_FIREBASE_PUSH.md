# Step 28 — Firebase Cloud Messaging Real Push Sending

Status: working manually as of 2026-05-17.

## Purpose

Step 28 connects the existing Planora push-notification foundation to Firebase Cloud Messaging so the backend can send real push notifications to registered Android, iOS, or web device tokens.

This step builds on:

- Step 26 — `device_tokens` and `notification_preferences` foundation.
- Step 27 — CORS/frontend-mobile integration.

## Main behavior

- Backend stores FCM tokens through `POST /push-notifications/device-tokens`.
- Backend sends a manual test push through `POST /push-notifications/test`.
- Backend checks Firebase configuration through `GET /push-notifications/status`.
- Push sending uses active tokens from `device_tokens`.
- User preferences from `notification_preferences` are respected.
- Invalid/unregistered Firebase tokens are deactivated when Firebase returns invalid-token errors.
- Push sending is best-effort and should not block normal in-app notification creation.

## Tables used

No new database tables were added in Step 28.

Existing tables used:

- `device_tokens`
- `notification_preferences`
- `notifications`
- `users`

Optional future table:

- Firebase push delivery log table, only if delivery audit/history is required later.

## Files added or updated

Important backend files:

- `app/services/firebase_push_service.py`
- `app/routers/push_notification_routes.py`
- `app/schemas/push_notification_schema.py`
- `app/services/notification_service.py`
- `app/core/config.py`
- `.env.example`
- `.gitignore`
- `requirements.txt`
- `tests/test_20_firebase_push_service.py`

Manual web testing files:

- `tools/firebase-web-test/firebase_token_test.html`
- `tools/firebase-web-test/firebase-messaging-sw.js`

## Configuration

Local `.env` requires:

```env
FIREBASE_ENABLED=true
FIREBASE_CREDENTIALS_PATH=firebase-service-account-local.json
FIREBASE_CREDENTIALS_JSON=
```

The service-account JSON file must stay local and must never be committed.

Expected backend layout:

```txt
backend/
  .env
  firebase-service-account-local.json
  app/
  tests/
```

## Secret safety

Do not commit:

- `firebase-service-account-local.json`
- any Firebase Admin SDK service-account JSON
- private keys
- JWTs
- real user tokens

The web Firebase config and VAPID public key are not the same as the backend service-account private key. The service-account JSON is the sensitive backend credential.

## Verified test result

Unit/API test file:

```powershell
python -m pytest tests/test_20_firebase_push_service.py -v
```

Confirmed result:

```txt
5 passed
```

## Verified manual result

Manual Swagger endpoint:

```txt
POST /push-notifications/test
```

Confirmed response:

```json
{
  "status": "sent",
  "detail": "Push notification sent successfully.",
  "sent_count": 1,
  "skipped_count": 0,
  "failed_count": 0,
  "deactivated_tokens": 0
}
```

This means the Planora backend successfully authenticated with Firebase and Firebase accepted the push message for one registered FCM token.

## Manual testing flow

1. Put Firebase Admin SDK service-account JSON in backend root as `firebase-service-account-local.json`.
2. Set Firebase environment variables in `.env`.
3. Restart FastAPI.
4. Open `tools/firebase-web-test/firebase_token_test.html` from a local server such as port `5500`.
5. Paste Firebase web app config into the page.
6. Paste Firebase Web Push VAPID public key into the page.
7. Generate a browser FCM token.
8. Register the FCM token through `POST /push-notifications/device-tokens`.
9. Send a push through `POST /push-notifications/test`.

## Useful commands

Run local web tester:

```powershell
cd tools\firebase-web-test
python -m http.server 5500
```

Open:

```txt
http://127.0.0.1:5500/firebase_token_test.html
```

Check backend Firebase configuration:

```powershell
python -c "from app.core.config import settings; print(settings.firebase_enabled); print(settings.firebase_credentials_path); print(bool(settings.firebase_credentials_json))"
```

Expected:

```txt
True
firebase-service-account-local.json
False
```

## Notes

If the backend returns `sent` but the browser does not show a visible notification:

- Check browser notification permission.
- Check whether the page is in the foreground.
- Check Chrome DevTools → Application → Service Workers.
- Unregister the old service worker and refresh if the Firebase config changed.
- Make sure the FCM token and backend service account belong to the same Firebase project.

## Next recommended step

After Step 28, the next backend priority should be one of:

1. Alembic migrations to stop manual schema drift.
2. Firebase Storage for attachments, if file storage becomes urgent.
3. Admin/notification polish and frontend integration.

Docker should still remain final polish after the core system is stable.
