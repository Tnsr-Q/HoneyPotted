from flask import request, jsonify, Blueprint, g, current_app
import hmac
import hashlib
import json
import base64
import logging
import time
import os
import secrets

from honeypot.injection.router import profile_difficulty_bias

logger = logging.getLogger('quantum_nexus.challenge')


def _injection_difficulty_bias():
    """Difficulty bias for the current request's actor from injection history.

    Reads the prompt-injection guard's telemetry (if installed) so a client
    with a track record of injection probes receives harder challenges even on
    an otherwise-clean challenge request. Fails closed to 0 bias.
    """
    try:
        guard = current_app.extensions.get('injection_guard')
        if not guard or guard.store is None:
            return 0
        profile = guard.store.get_profile(guard.actor_key(request))
        return profile_difficulty_bias(profile)
    except Exception:
        logger.debug("injection bias lookup failed", exc_info=True)
        return 0

challenge_bp = Blueprint('challenge', __name__)
SECRET_KEY = os.environ.get('CHALLENGE_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('CHALLENGE_SECRET_KEY environment variable must be set')

def create_hmac(challenge_data, secret_key):
    message = json.dumps(challenge_data, sort_keys=True).encode()
    hmac_value = hmac.new(secret_key.encode(), message, hashlib.sha256).digest()
    return base64.b64encode(hmac_value).decode()

def verify_hmac(challenge_data, hmac_value, secret_key):
    expected_hmac = create_hmac(challenge_data, secret_key)
    return hmac.compare_digest(expected_hmac, hmac_value)

@challenge_bp.route('/', methods=['POST'])
def generate_challenge_route():
    try:
        # Arithmetic challenge whose size scales with the actor's injection
        # history: a clean client gets the simple baseline; a repeat injector
        # gets more operands of larger magnitude (more work to solve).
        bias = _injection_difficulty_bias()
        operand_count = 2 + min(bias, 6)            # 2..8 operands
        ceiling = 10 + bias * 15                    # magnitude grows with bias
        numbers = [secrets.randbelow(ceiling) + 1 for _ in range(operand_count)]
        challenge_data = {
            'operation': 'sum',
            'numbers': numbers,
            'difficulty': bias,
            'timestamp': int(time.time()),
            'timeout': 180 + bias * 20
        }
        challenge_id = "chal_" + secrets.token_hex(16)
        hmac_payload = {
            'challenge_id': challenge_id,
            'data': challenge_data
        }
        hmac_value = create_hmac(hmac_payload, SECRET_KEY)
        return jsonify({
            "challenge_id": challenge_id,
            "data": challenge_data,
            "hmac": hmac_value
        })
    except Exception:
        logger.exception("Error generating challenge")
        return jsonify({"error": "Failed to generate challenge"}), 400

@challenge_bp.route('/verify', methods=['POST'])
def verify_challenge_route():
    try:
        data = request.get_json()
        challenge_id = data.get('challenge_id')
        response = data.get('response')
        hmac_value = data.get('hmac')
        challenge_data = data.get('data')
        bot_id = data.get('bot_id', 'unknown')

        if not all([challenge_id, response, hmac_value, challenge_data]):
             return jsonify({"error": "Missing required fields"}), 400

        hmac_payload = {
            'challenge_id': challenge_id,
            'data': challenge_data
        }

        if not verify_hmac(hmac_payload, hmac_value, SECRET_KEY):
            return jsonify({"error": "HMAC verification failed"}), 400

        # Verify answer
        answer = int(response.get('answer', -1))
        expected_answer = sum(challenge_data.get('numbers', []))
        success = (answer == expected_answer)

        # Log outcome
        log_entry = {
            "event": "challenge_completed",
            "challenge_id": challenge_id,
            "bot_id": bot_id,
            "cycles": 1, # placeholder for MVP
            "outcome": "success" if success else "failure"
        }
        logger.info(json.dumps(log_entry))

        return jsonify({
            "challenge_id": challenge_id,
            "success": success
        })
    except Exception:
        logger.exception("Error verifying challenge")
        return jsonify({"error": "Failed to verify challenge"}), 400
