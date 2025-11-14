from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

app = Flask(__name__)

users = {}
ads = {}
user_tokens = {}
ad_id_counter = 1
user_id_counter = 1

@app.route('/register', methods=['POST'])
def register():
    global user_id_counter
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Missing email or password"}), 400
    
    for user in users.values():
        if user['email'] == data['email']:
            return jsonify({"error": "Email already registered"}), 400

    user = {
        "id": user_id_counter,
        "email": data['email'],
        "password_hash": generate_password_hash(data['password'])
    }
    users[user_id_counter] = user
    user_id_counter += 1
    return jsonify({"message": "User registered successfully"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Missing email or password"}), 400
    
    # Find user
    user = next((u for u in users.values() if u['email'] == data['email']), None)
    if not user or not check_password_hash(user['password_hash'], data['password']):
        return jsonify({"error": "Invalid credentials"}), 401

    # Generate a token
    token = str(uuid.uuid4())
    user_tokens[token] = user['id']
    return jsonify({"token": token})


def get_authenticated_user():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split()[1]
    user_id = user_tokens.get(token)
    if user_id is None:
        return None
    return users[user_id]

@app.route('/ads', methods=['POST'])
def create_ad():
    global ad_id_counter
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data or 'title' not in data or 'description' not in data:
        return jsonify({"error": "Missing title or description"}), 400
    
    ad = {
        "id": ad_id_counter,
        "title": data['title'],
        "description": data['description'],
        "date_of_creation": datetime.utcnow().isoformat(),
        "owner": user['id']
    }
    ads[ad_id_counter] = ad
    ad_id_counter += 1
    return jsonify(ad), 201


@app.route('/ads/<int:ad_id>', methods=['GET'])
def get_ad(ad_id):
    ad = ads.get(ad_id)
    if not ad:
        return jsonify({"error": "Ad not found"}), 404
    return jsonify(ad)


@app.route('/ads/<int:ad_id>', methods=['DELETE'])
def delete_ad(ad_id):
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    ad = ads.get(ad_id)
    if not ad:
        return jsonify({"error": "Ad not found"}), 404
    if ad['owner'] != user['id']:
        return jsonify({"error": "Forbidden: You are not the owner"}), 403
    
    del ads[ad_id]
    return jsonify({"message": "Ad deleted successfully"}), 200


@app.route('/ads/<int:ad_id>', methods=['PUT'])
def edit_ad(ad_id):
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    ad = ads.get(ad_id)
    if not ad:
        return jsonify({"error": "Ad not found"}), 404
    if ad['owner'] != user['id']:
        return jsonify({"error": "Forbidden: You are not the owner"}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing data"}), 400
    
    ad['title'] = data.get('title', ad['title'])
    ad['description'] = data.get('description', ad['description'])
    return jsonify(ad)


if __name__ == '__main__':
    app.run(debug=True)
