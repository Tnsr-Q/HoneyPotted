### 2. `challenge_generator.py`
This file generates unique challenges and includes HMAC verification.

```python
import time
import json
import random
import string
import hashlib
import hmac
import base64
from challenge_types import ArithmeticChallenge, StringManipulationChallenge, ImageProcessingChallenge, GraphProblemChallenge, CaptchaChallenge, LogicPuzzleChallenge

def generate_unique_challenge(challenge_type, difficulty):
    base_data = {
        'difficulty': difficulty,
        'timestamp': int(time.time())
    }
    if challenge_type == 'arithmetic':
        base_data['operation'] = random.choice(['+', '-', '*', '/'])
        base_data['num1'] = random.randint(1, 100)
        base_data['num2'] = random.randint(1, 100)
    elif challenge_type == 'string_manipulation':
        base_data['string'] = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        base_data['operation'] = random.choice(['reverse', 'uppercase', 'lowercase'])
    elif challenge_type == 'image_processing':
        base_data['image_url'] = f"https://example.com/images/{random.randint(1, 100)}.jpg"
        base_data['operation'] = random.choice(['resize', 'grayscale', 'rotate'])
    elif challenge_type == 'graph_problem':
        base_data['graph'] = {'nodes': ['A', 'B', 'C'], 'edges': [('A', 'B'), ('B', 'C')]}
        base_data['operation'] = random.choice(['find_path', 'count_nodes'])
    elif challenge_type == 'captcha':
        base_data['captcha_image'] = "https://example.com/captcha.png"
        base_data['captcha_text'] = "example_text"
    elif challenge_type == 'logic_puzzle':
        base_data['puzzle'] = "What is the capital of France?"
        base_data['answer'] = "Paris"

    challenge_data = json.dumps(base_data, sort_keys=True)
    challenge_id = hashlib.sha256(challenge_data.encode()).hexdigest()
    return challenge_id, base_data

def generate_challenge(challenge_type, difficulty):
    challenge_id, challenge_data = generate_unique_challenge(challenge_type, difficulty)
    if challenge_type == 'arithmetic':
        return ArithmeticChallenge(challenge_id, challenge_data)
    elif challenge_type == 'string_manipulation':
        return StringManipulationChallenge(challenge_id, challenge_data)
    elif challenge_type == 'image_processing':
        return ImageProcessingChallenge(challenge_id, challenge_data)
    elif challenge_type == 'graph_problem':
        return GraphProblemChallenge(challenge_id, challenge_data)
    elif challenge_type == 'captcha':
        return CaptchaChallenge(challenge_id, challenge_data)
    elif challenge_type == 'logic_puzzle':
        return LogicPuzzleChallenge(challenge_id, challenge_data)

def create_hmac(challenge_data, secret_key):
    message = json.dumps(challenge_data, sort_keys=True).encode()
    hmac_value = hmac.new(secret_key.encode(), message, hashlib.sha256).digest()
    return base64.b64encode(hmac_value).decode()