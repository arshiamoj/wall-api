from flask import Flask, jsonify, request
from flask_cors import CORS  # Import Flask-CORS
import json
import os
import subprocess
from functools import wraps

app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# File paths
QUOTES_PATH = "/home/mojtaba/wall/quotes.json"
APPROVED_QUOTES_PATH = "/home/mojtaba/wall/approved_quotes.json"
REMOVED_QUOTES_PATH = "/home/mojtaba/wall/removed_quotes.json"
REPO_PATH = "/home/mojtaba/wall/"

# Basic authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        # You should replace 'your_secret_api_key' with a secure key
        if not api_key or api_key != 'your_secret_api_key':
            return jsonify({"error": "Unauthorized access"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Helper function to read JSON file
def read_json_file(file_path):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                return json.load(file)
        return []
    except Exception as e:
        app.logger.error(f"Error reading {file_path}: {str(e)}")
        return []

# Helper function to write JSON file
def write_json_file(file_path, data):
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=2)
        return True
    except Exception as e:
        app.logger.error(f"Error writing to {file_path}: {str(e)}")
        return False

# Endpoint to get all quotes
@app.route('/api/quotes', methods=['GET'])
@require_api_key
def get_all_quotes():
    quotes = read_json_file(QUOTES_PATH)
    approved_quotes = read_json_file(APPROVED_QUOTES_PATH)
    removed_quotes = read_json_file(REMOVED_QUOTES_PATH)
    
    return jsonify({
        "quotes": quotes,
        "approved_quotes": approved_quotes,
        "removed_quotes": removed_quotes
    })

# Endpoint to move a quote from unapproved to either quotes or removed
@app.route('/api/quotes/move', methods=['POST'])
@require_api_key
def move_quote():
    data = request.json
    if not data or 'index' not in data or 'destination' not in data:
        return jsonify({"error": "Missing required parameters"}), 400
    
    index = data['index']
    destination = data['destination']
    
    if destination not in ['quotes', 'removed']:
        return jsonify({"error": "Destination must be 'quotes' or 'removed'"}), 400
    
    # Read source file (approved quotes)
    source_quotes = read_json_file(APPROVED_QUOTES_PATH)
    
    if index < 0 or index >= len(source_quotes):
        return jsonify({"error": "Index out of range"}), 400
    
    # Get the quote to move
    quote_to_move = source_quotes.pop(index)
    
    # Write back the source file without the moved quote
    if not write_json_file(APPROVED_QUOTES_PATH, source_quotes):
        return jsonify({"error": "Failed to update source file"}), 500
    
    # Add to destination file
    if destination == 'quotes':
        dest_file = QUOTES_PATH
    else:
        dest_file = REMOVED_QUOTES_PATH
    
    dest_quotes = read_json_file(dest_file)
    dest_quotes.append(quote_to_move)
    
    if not write_json_file(dest_file, dest_quotes):
        return jsonify({"error": "Failed to update destination file"}), 500
    
    return jsonify({"success": True, "message": f"Quote moved to {destination}"})


# Endpoint to run git pull
@app.route('/api/git/pull', methods=['POST'])
@require_api_key
def git_pull():
    try:
        result = subprocess.run(
            ['git', 'pull'],
            cwd=REPO_PATH,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return jsonify({
                "success": True,
                "message": "Git pull successful",
                "output": result.stdout
            })
        else:
            return jsonify({
                "success": False,
                "message": "Git pull failed",
                "error": result.stderr
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Git pull failed",
            "error": str(e)
        }), 500

# Endpoint to reboot Raspberry Pi
@app.route('/api/system/reboot', methods=['POST'])
@require_api_key
def reboot_system():
    try:
        # This requires sudo privileges or appropriate permissions
        subprocess.Popen(['sudo', 'reboot'])
        return jsonify({
            "success": True,
            "message": "Reboot initiated"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Reboot failed",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Do not use debug=True in production
    app.run(host='0.0.0.0', port=5000)
