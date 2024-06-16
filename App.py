from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
import pickle
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

conn = psycopg2.connect(database="Crop", user="postgres", password="XXXXXX", host="localhost", port="5432")

with open('XGBoost.pkl', 'rb') as model_file:
    model = pickle.load(model_file)

label_encoder = LabelEncoder()
label_encoder.fit(['apple', 'banana', 'blackgram', 'chickpea', 'coconut', 'coffee', 'cotton',
                   'grapes', 'jute', 'kidneybeans', 'lentil', 'maize', 'mango', 'mothbeans',
                   'mungbean', 'muskmelon', 'orange', 'papaya', 'pigeonpeas', 'pomegranate',
                   'rice', 'watermelon'])

def recommend_crop(input_features):
    input_df = pd.DataFrame([input_features], columns=['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall'])
    predicted_class = model.predict(input_df)[0]
    crop_name = label_encoder.inverse_transform([predicted_class])[0]
    return crop_name

global session_email
session_email = None

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    global session_email
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        username = request.form['first']
        password = request.form['password']
        email = request.form['email']
        session_email = email
        cur.execute("SELECT * FROM farmers WHERE mail_id = %s", (email,))
        existing_user = cur.fetchone()
        if existing_user:
            flash('User with this email already exists! Please login instead.', 'error')
            return redirect(url_for('login'))
        else:
            cur.execute("INSERT INTO farmers (fname, mail_id, password) VALUES (%s, %s, %s)", (username, email, password))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/', methods=['GET', 'POST'])
def login():
    global session_email
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM farmers WHERE mail_id = %s AND password = %s", (email, password))
        user = cur.fetchone()
        if user:
            session_email = email  # Store email in global variable
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials! Please try again.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/home')
def home():
    global session_email
    if session_email is None:
        flash('You need to login first!', 'error')
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    global session_email
    if session_email is None:
        flash('You need to login first!', 'error')
        return redirect(url_for('login'))
    
    N = request.form['N']
    P = request.form['P']
    K = request.form['K']
    temperature = request.form['temperature']
    humidity = request.form['humidity']
    ph = request.form['ph']
    rainfall = request.form['rainfall']

    input_features = [N, P, K, temperature, humidity, ph, rainfall]
    input_features = list(map(float, input_features))  # Ensure all inputs are converted to float

    prediction = recommend_crop(input_features)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT farmer_id FROM farmers WHERE mail_id = %s", (session_email,))
    farmer_id = cur.fetchone()['farmer_id']
    cur.execute("INSERT INTO recommendation (farmer_id, res) VALUES (%s, %s)", (farmer_id, prediction))
    conn.commit()

    if prediction:
        img_url = f'static/img/{prediction.lower()}.jpg'  # Assuming your images are named after the crop
    else:
        img_url = None

    return render_template('index.html', prediction=prediction, src=img_url)

@app.route('/about')
def about():
    return render_template('About.html')

if __name__ == '__main__':
    app.run(debug=True)
