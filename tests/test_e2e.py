import pytest
import json

def test_full_challenge_loop(client):
    # Simulate bot -> fingerprint (skipped as we only test the challenge API here for now) -> challenge -> verify

    # 1. Get a challenge
    response = client.post('/api/challenge/')
    assert response.status_code == 200

    data = response.get_json()
    assert 'challenge_id' in data
    assert 'data' in data
    assert 'hmac' in data

    challenge_id = data['challenge_id']
    challenge_data = data['data']
    hmac_val = data['hmac']

    # Extract the correct answer from the challenge data
    # We set operation to 'sum' and numbers to [5, 10] in the MVP
    assert challenge_data['operation'] == 'sum'
    expected_answer = sum(challenge_data['numbers'])

    # 2. Submit a correct response
    verify_payload = {
        'challenge_id': challenge_id,
        'data': challenge_data,
        'hmac': hmac_val,
        'response': {'answer': expected_answer},
        'bot_id': 'test_bot_123'
    }

    verify_res = client.post('/api/challenge/verify', json=verify_payload)
    assert verify_res.status_code == 200

    verify_data = verify_res.get_json()
    assert verify_data['challenge_id'] == challenge_id
    assert verify_data['success'] is True

    # 3. Submit an incorrect response
    verify_payload_wrong = verify_payload.copy()
    verify_payload_wrong['response'] = {'answer': 999}

    verify_res_wrong = client.post('/api/challenge/verify', json=verify_payload_wrong)
    assert verify_res_wrong.status_code == 200

    verify_data_wrong = verify_res_wrong.get_json()
    assert verify_data_wrong['success'] is False

    # 4. Tamper with the payload (invalid HMAC)
    tampered_payload = verify_payload.copy()
    tampered_payload['data']['numbers'] = [1, 1] # changed data

    verify_res_tamper = client.post('/api/challenge/verify', json=tampered_payload)
    assert verify_res_tamper.status_code == 400
    assert 'HMAC verification failed' in verify_res_tamper.get_json()['error']
