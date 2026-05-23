from flask import request, jsonify, Blueprint
import hmac
import hashlib
import json
import base64
import logging
import time

logger = logging.getLogger('quantum_nexus.challenge')

challenge_bp = Blueprint('challenge', __name__)
SECRET_KEY = 'super_secret_challenge_key' # for MVP

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
        # Simple arithmetic challenge for MVP
        challenge_data = {
            'operation': 'sum',
            'numbers': [5, 10], # Keep it simple for now
            'timestamp': int(time.time()),
            'timeout': 180
        }
        hmac_value = create_hmac(challenge_data, SECRET_KEY)
        return jsonify({
            "challenge_id": "chal_" + hashlib.md5(str(time.time()).encode()).hexdigest(),
            "data": challenge_data,
            "hmac": hmac_value
        })
    except Exception as e:
        logger.error(f"Error generating challenge: {e}")
        return jsonify({"error": str(e)}), 400

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

        if not verify_hmac(challenge_data, hmac_value, SECRET_KEY):
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
    except Exception as e:
         logger.error(f"Error verifying challenge: {e}")
         return jsonify({"error": str(e)}), 400
