
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
import json
import os
import secrets

app = Flask(__name__, template_folder='.')
app.secret_key = os.environ.get('SESSION_SECRET', secrets.token_hex(32))

API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
DEEPINFRA_API_KEY = os.environ.get('DEEPINFRA_API_KEY', '')

def get_api_headers():
    headers = {
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Origin": "https://deepinfra.com",
        "Referer": "https://deepinfra.com/",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "X-Deepinfra-Source": "web-page",
        "accept": "text/event-stream",
    }
    if DEEPINFRA_API_KEY:
        headers["Authorization"] = f"Bearer {DEEPINFRA_API_KEY}"
    return headers

users = {
    "admin": "admin123",
    "user": "password"
}

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if username in users and users[username] == password:
            session['username'] = username
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'})
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/generate', methods=['POST'])
def generate():
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    user_prompt = data.get('prompt', '')
    
    if not user_prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    system_message = """You are an expert web developer. Generate complete, working HTML/CSS/JavaScript code based on the user's request.
    
    IMPORTANT FORMATTING RULES:
    1. Return ONLY the code, no explanations
    2. Format your response EXACTLY like this:
    
    HTML:
    [complete HTML code here]
    
    CSS:
    [complete CSS code here]
    
    JAVASCRIPT:
    [complete JavaScript code here]
    
    3. Always include all three sections (HTML, CSS, JAVASCRIPT) even if some are empty
    4. Make the code modern, responsive, and visually appealing
    5. Use modern CSS with animations and gradients
    6. Include proper HTML5 structure"""
    
    chat_history = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_prompt}
    ]
    
    payload = {
        "model": "zai-org/GLM-4.5",
        "messages": chat_history,
        "stream": True,
        "stream_options": {
            "include_usage": True,
            "continuous_usage_stats": True,
        },
    }
    
    try:
        full_response = ""
        api_headers = get_api_headers()
        with requests.post(API_URL, headers=api_headers, json=payload, stream=True, timeout=60) as response:
            if response.status_code != 200:
                return jsonify({'error': 'API request failed'}), 500
            
            for line in response.iter_lines():
                if line:
                    try:
                        decoded_line = line.decode("utf-8")
                        if decoded_line.startswith("data: "):
                            decoded_line = decoded_line[6:]
                            if decoded_line == "[DONE]":
                                break
                            data_json = json.loads(decoded_line)
                            if "choices" in data_json:
                                delta = data_json["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    full_response += content
                    except Exception:
                        continue
        
        html_code = ""
        css_code = ""
        js_code = ""
        
        if "HTML:" in full_response and "CSS:" in full_response:
            parts = full_response.split("CSS:")
            html_part = parts[0].split("HTML:")[1].strip() if "HTML:" in parts[0] else ""
            
            if "JAVASCRIPT:" in parts[1]:
                css_js_parts = parts[1].split("JAVASCRIPT:")
                css_code = css_js_parts[0].strip()
                js_code = css_js_parts[1].strip() if len(css_js_parts) > 1 else ""
            else:
                css_code = parts[1].strip()
            
            html_code = html_part
        else:
            html_code = full_response
        
        html_code = html_code.replace("```html", "").replace("```", "").strip()
        css_code = css_code.replace("```css", "").replace("```", "").strip()
        js_code = js_code.replace("```javascript", "").replace("```js", "").replace("```", "").strip()
        
        return jsonify({
            'html': html_code,
            'css': css_code,
            'javascript': js_code
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
