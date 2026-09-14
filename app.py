#!/usr/bin/env python
import sys
import traceback
from functools import wraps

print("=== DEBUG: app.py started ===")
print(f"Python version: {sys.version}")
print(f"Current directory: {__file__}")
print("=== Loading modules... ===")

try:
    from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, send_file
    print("✅ Flask imported")
except ImportError as e:
    print(f"❌ Flask not installed: {e}")
    print("Run: pip install flask flask-cors python-dotenv")
    sys.exit(1)

try:
    from flask_cors import CORS
    print("✅ Flask-CORS imported")
except ImportError as e:
    print(f"❌ Flask-CORS not installed: {e}")
    print("Run: pip install flask-cors")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print("✅ python-dotenv imported")
except ImportError as e:
    print(f"❌ python-dotenv not installed: {e}")
    print("Run: pip install python-dotenv")
    sys.exit(1)

try:
    from fraud_checker import check_both
    print("✅ fraud_checker imported")
except ImportError as e:
    print(f"❌ fraud_checker import failed: {e}")
    print("Make sure fraud_checker.py is in the same folder")
    sys.exit(1)

try:
    from search_consignments import search_consignments
    print("✅ search_consignments imported")
except ImportError as e:
    print(f"❌ search_consignments import failed: {e}")
    print("Make sure search_consignments.py is in the same folder")
    sys.exit(1)

import os
from dotenv import load_dotenv

load_dotenv()
print("✅ .env loaded")

SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24).hex()
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app, supports_credentials=True)

@app.route('/favicon.ico')
def favicon():
    import os
    if os.path.exists('favicon.ico'):
        return send_file('favicon.ico', mimetype='image/vnd.microsoft.icon')
    return '', 204

@app.route('/favicon.png')
def favicon_png():
    import os
    if os.path.exists('favicon.png'):
        return send_file('favicon.png', mimetype='image/png')
    return '', 204
print("✅ Flask app created")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return send_from_directory('.', 'login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    return send_from_directory('.', 'dashboard.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '') if data else ''
    password = data.get('password', '') if data else ''
    print(f"DEBUG: username='{username}', password='{password}'")
    print(f"DEBUG: ADMIN_USERNAME='{ADMIN_USERNAME}', ADMIN_PASSWORD='{ADMIN_PASSWORD}'")
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['logged_in'] = True
        print("DEBUG: Login successful!")
        return jsonify({'success': True})
    print("DEBUG: Login failed!")
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return jsonify({'success': True})

@app.route('/user')
def get_user():
    return jsonify({'logged_in': session.get('logged_in', False)})

@app.route('/check', methods=['GET'])
@login_required
def check_phone():
    phone = request.args.get('phone', '')
    if not phone:
        return jsonify({'error': 'No phone number provided'}), 400
    
    if not phone.isdigit() or len(phone) != 11:
        return jsonify({'error': 'Phone number must be 11 digits'}), 400
    
    try:
        result = check_both(phone)
        
        pathao = result['pathao']
        steadfast = result['steadfast']
        
        def to_int(val):
            return int(val) if val != 'N/A' and val is not None else 0
        
        p_error = pathao.get('error')
        p_total = to_int(pathao.get('processed'))
        p_delivered = to_int(pathao.get('delivered'))
        p_returned = to_int(pathao.get('returned'))
        
        s_error = steadfast.get('error')
        s_success = to_int(steadfast.get('success'))
        s_cancelled = to_int(steadfast.get('cancellation'))
        s_total = s_success + s_cancelled
        
        total_consignments = p_total + s_total
        total_success = p_delivered + s_success
        total_cancelled = p_returned + s_cancelled
        success_rate = round((total_success / total_consignments * 100), 1) if total_consignments > 0 else 0
        
        if success_rate >= 80:
            risk = 'Low Risk'
        elif success_rate >= 65:
            risk = 'Moderate Risk'
        else:
            risk = 'High Risk'
        
        response = {
            'phone': phone,
            'pathao': {
                'total': p_total,
                'delivered': p_delivered,
                'returned': p_returned,
                'success_rate': round((p_delivered / p_total * 100), 1) if p_total > 0 else 0,
                'error': p_error
            },
            'steadfast': {
                'total': s_total,
                'success': s_success,
                'cancellation': s_cancelled,
                'success_rate': round((s_success / s_total * 100), 1) if s_total > 0 else 0,
                'error': s_error
            },
            'combined': {
                'total': total_consignments,
                'success': total_success,
                'cancelled': total_cancelled,
                'success_rate': success_rate,
                'risk_level': risk
            },
            'elapsed': result.get('elapsed', 0)
        }
        return jsonify(response)
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['GET'])
@login_required
def search_phone():
    phone = request.args.get('phone', '')
    if not phone:
        return jsonify({'error': 'No phone number provided'}), 400

    if not phone.isdigit() or len(phone) != 11:
        return jsonify({'error': 'Phone number must be 11 digits'}), 400

    try:
        result = search_consignments(phone)
        return jsonify(result)
    except Exception as e:
        print(f"❌ Search error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        traceback.print_exc()
