import os
import sqlite3
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
import threading
import time
import json
import random
import csv
import xml.etree.ElementTree as ET
from flask import Flask, request, render_template_string, redirect, url_for, jsonify
from concurrent.futures import ThreadPoolExecutor
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
import requests
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://tnsr-q.ai')
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_PASSWORD = os.getenv('SHOPIFY_PASSWORD')
SHOPIFY_SHOP_NAME = os.getenv('SHOPIFY_SHOP_NAME')
DB_NAME = 'bot_logs.db'
TABLE_BOT_VISITS = 'bot_visits'
TABLE_BOT_WORK = 'bot_work'
RESULTS_DIR = 'results'

# Ensure results directory exists
os.makedirs(RESULTS_DIR, exist_ok=True)

# Initialize Flask app
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABLE_BOT_VISITS} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            timestamp TEXT,
            user_agent TEXT
        )
    ''')
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {TABLE_BOT_WORK} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            bot_ip TEXT,
            result REAL
        )
    ''')
    conn.commit()
    conn.close()

# Load data from SQLite database
def load_data():
    conn = sqlite3.connect(DB_NAME)
    visits_df = pd.read_sql_query(f'SELECT * FROM {TABLE_BOT_VISITS}', conn)
    work_df = pd.read_sql_query(f'SELECT * FROM {TABLE_BOT_WORK}', conn)
    conn.close()
    return visits_df, work_df

# Preprocess the data
def preprocess_data(visits_df, work_df):
    # Convert timestamps to datetime
    visits_df['timestamp'] = pd.to_datetime(visits_df['timestamp'])
    work_df['timestamp'] = pd.to_datetime(work_df['timestamp'])
    
    # Calculate request frequency (requests/min per IP)
    freq_df = visits_df.groupby(['ip', pd.Grouper(key='timestamp', freq='1T')]).size().reset_index(name='request_count')
    freq_df = freq_df.groupby('ip')['request_count'].mean().reset_index()
    freq_df.rename(columns={'request_count': 'avg_request_freq'}, inplace=True)
    
    # Task completion rate (valid results submitted per IP)
    task_rate_df = work_df.groupby('ip').size().reset_index(name='task_completion_rate')
    
    # Merge features
    merged_df = pd.merge(freq_df, task_rate_df, on='ip', how='outer')
    merged_df.fillna(0, inplace=True)
    
    # Average result value
    avg_result_df = work_df.groupby('ip')['result'].mean().reset_index(name='avg_result_value')
    merged_df = pd.merge(merged_df, avg_result_df, on='ip', how='outer')
    merged_df.fillna(0, inplace=True)
    
    # Time since last request (seconds)
    merged_df['time_since_last_request'] = merged_df.groupby('ip')['timestamp'].diff().dt.total_seconds().fillna(0)
    
    # Bot type
    merged_df['bot_type'] = merged_df.apply(lambda row: 'fast' if row['avg_request_freq'] > 10 else 'slow', axis=1)
    merged_df['is_worker'] = merged_df.apply(lambda row: 1 if row['task_completion_rate'] > 0 else 0, axis=1)
    
    return merged_df

# Define a supervised learning model using TensorFlow
def create_supervised_model():
    model = Sequential([
        Dense(128, activation='relu', input_shape=(5,)),
        Dense(64, activation='relu'),
        Dense(32, activation='relu'),
        Dense(1, activation='linear')
    ])
    model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
    return model

# Train the supervised model
def train_supervised_model(model, X_train, y_train, X_test, y_test):
    model.fit(X_train, y_train, epochs=20, batch_size=32, validation_data=(X_test, y_test))
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    logger.info(f'Test RMSE: {rmse:.4f}')
    return model

# Deploy the trained supervised model
def deploy_supervised_model(model):
    # Generate 5 new fake product prices
    fake_prices = [model.predict(np.array([[random.uniform(1, 10), random.uniform(1, 10), random.uniform(1, 10), random.uniform(1, 10), random.uniform(1, 10)]]))[0][0] for _ in range(5)]
    
    # Update Shopify store with new products
    session = Session(SHOPIFY_SHOP_NAME, ApiVersion.UNSET, f"{SHOPIFY_API_KEY}:{SHOPIFY_PASSWORD}")
    ShopifyResource.activate_session(session)
    
    def create_product(price):
        product = Product()
        product.title = f'Fake Product {price:.2f}'
        product.body_html = f'A fake product created by bots with price ${price:.2f}.'
        product.variants = [{'price': str(price)}]
        product.save()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(create_product, fake_prices)
    
    ShopifyResource.clear_session()
    
    # Create 5 SEO meta descriptions
    descriptions = [f'Discover our exclusive deal: ${price:.2f} off on this product!' for price in fake_prices]
    
    # Save generated content to CSV
    with open(os.path.join(RESULTS_DIR, 'agent_output.csv'), 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['product_title', 'description'])
        for price in fake_prices:
            writer.writerow([f'Fake Product {price:.2f}', f'Discover our exclusive deal: ${price:.2f} off on this product!'])

# Define a custom environment for RL
class HoneypotEnv(gym.Env):
    def __init__(self, bot_data):
        super(HoneypotEnv, self).__init__()
        self.bot_data = bot_data
        self.action_space = gym.spaces.Discrete(4)  # Number of integers to sum (2-5)
        self.observation_space = gym.spaces.Box(low=0, high=1, shape=(3,), dtype=np.float32)
        self.state = None
        self.reset()
    
    def reset(self):
        self.state = self.bot_data.sample(n=1).values[0]
        return self.state
    
    def step(self, action):
        reward = 0
        done = False
        
        if action == 0:  # Valid submission
            reward = 1
        elif action == 1:  # No submission
            reward = -0.5
        elif action == 2:  # High-value result
            reward = 2
        
        self.state = self.bot_data.sample(n=1).values[0]
        return self.state, reward, done, {}

# Train the RL agent
def train_rl_agent(bot_data):
    env = make_vec_env(lambda: HoneypotEnv(bot_data), n_envs=1)
    model = PPO('MlpPolicy', env, verbose=1)
    model.learn(total_timesteps=20000)
    model.save(os.path.join(RESULTS_DIR, 'bot_rl_agent.zip'))

# Deploy the RL agent
def deploy_rl_agent(model):
    # Example of adjusting task difficulty based on bot type
    def adjust_task_difficulty(bot_type):
        if bot_type == 'fast':
            return random.randint(4, 5)
        else:
            return random.randint(2, 3)
    
    # Serve dynamic tasks at /hidden-deals
    @app.route('/hidden-deals')
    def honeypot_page():
        # Log the visit
        log_visit(request.remote_addr, request.user_agent.string)
        
        # Generate a dynamic task based on bot type
        bot_type = get_bot_type(request.remote_addr)
        task_difficulty = adjust_task_difficulty(bot_type)
        task = {
            'instruction': 'sum these',
            'numbers': [random.randint(1, 100) for _ in range(task_difficulty)],
            'redirect_url': url_for('submit_results')
        }
        return render_template_string(HONEYPOT_TEMPLATE, task=json.dumps(task))

# Function to log visits
def log_visit(ip, user_agent):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f'''
        INSERT INTO {TABLE_BOT_VISITS} (ip, timestamp, user_agent)
        VALUES (?, ?, ?)
    ''', (ip, time.strftime('%Y-%m-%d %H:%M:%S'), user_agent))
    conn.commit()
    conn.close()

# Function to store results
def store_result(ip, result):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f'''
        INSERT INTO {TABLE_BOT_WORK} (timestamp, bot_ip, result)
        VALUES (?, ?, ?)
    ''', (time.strftime('%Y-%m-%d %H:%M:%S'), ip, result))
    conn.commit()
    conn.close()

# Function to get bot type
def get_bot_type(ip):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f'SELECT bot_type FROM {TABLE_BOT_WORK} WHERE bot_ip = ? LIMIT 1', (ip,))
    bot_type = cursor.fetchone()
    conn.close()
    return bot_type[0] if bot_type else 'slow'

# Main function to run the pipeline
def main():
    # Initialize database
    init_db()
    
    # Load data
    visits_df, work_df = load_data()
    
    # Preprocess data
    merged_df = preprocess_data(visits_df, work_df)
    
    # Split data into features and target
    X = merged_df[['avg_request_freq', 'task_completion_rate', 'avg_result_value', 'time_since_last_request', 'is_worker']]
    y = merged_df['result']
    
    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Standardize features
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    
    # Create and train the supervised model
    model = create_supervised_model()
    model = train_supervised_model(model, X_train, y_train, X_test, y_test)
    
    # Save the trained model
    model.save(os.path.join(RESULTS_DIR, 'bot_agent_model.h5'))
    
    # Deploy the supervised model
    deploy_supervised_model(model)
    
    # Train the RL agent
    train_rl_agent(merged_df)
    
    # Deploy the RL agent
    rl_model = PPO.load(os.path.join(RESULTS_DIR, 'bot_rl_agent.zip'))
    deploy_rl_agent(rl_model)
    
    # Start the Flask server
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()