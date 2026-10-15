# Krishi Kotha

See PROJECT_SPEC.md. Full setup instructions are completed in Phase 13.

## Voice and Twilio (optional)

The simulator works with no Twilio account. Voice advice uses gTTS (needs internet the first time a message is spoken; MP3 files are cached in `data/audio/`).

To receive real SMS and calls:

1. Set `ADMIN_API_KEY` to a secret value in `.env`.
2. Start the backend on port 8000.
3. Open a public HTTPS tunnel to port 8000, for example `ngrok http 8000` or `cloudflared tunnel --url http://localhost:8000`. Twilio cannot reach `localhost`.
4. In `.env` set `PUBLIC_BASE_URL` to the tunnel URL (no trailing slash), `TWILIO_ENABLED=true`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` and `TWILIO_FROM_NUMBER`, then restart the backend. `PUBLIC_BASE_URL` must match the URL Twilio calls exactly, because the webhook signature is checked against it.
5. In the Twilio console, set the number's messaging webhook (HTTP POST) to `{PUBLIC_BASE_URL}/api/sms/inbound` and the voice webhook (HTTP POST) to `{PUBLIC_BASE_URL}/api/voice/inbound`.
6. Trial accounts can message and call only verified numbers.

With `TWILIO_ENABLED=false` (the default) the Twilio package is never imported and both webhooks return 404.

### Broadcast preview

Admin routes need the header `X-Admin-Key`. A broadcast is a dry run unless you send `"dry_run": false`:

```
curl -X POST http://localhost:8000/api/admin/broadcast   -H "X-Admin-Key: <your key>" -H "Content-Type: application/json"   -d '{"district_id": "sylhet", "min_level": "moderate"}'
```

The response is `{"recipients": N, "sample_text_bn": "...", "sent": 0}`.
