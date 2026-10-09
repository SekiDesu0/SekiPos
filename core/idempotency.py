import functools
import random
import uuid
from flask import request, jsonify
from core.db import get_db_connection


def idempotency_key(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.headers.get('X-Idempotency-Key')

        if not key:
            key = str(uuid.uuid4())

        with get_db_connection() as conn:
            existing = conn.execute(
                'SELECT key FROM idempotency_keys WHERE key = ?', (key,)
            ).fetchone()

            if existing:
                return jsonify({
                    "status": "duplicate",
                    "message": "Esta solicitud ya fue procesada."
                }), 409

            conn.execute(
                'INSERT INTO idempotency_keys (key, endpoint) VALUES (?, ?)',
                (key, request.endpoint)
            )

            # Probabilistic purge of keys older than 48 hours (~1% of requests)
            if random.random() < 0.01:
                conn.execute("DELETE FROM idempotency_keys WHERE created_at < datetime('now', 'localtime', '-2 days')")

            conn.commit()

        return f(*args, **kwargs)

    return decorated_function
