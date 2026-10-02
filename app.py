import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

# Configurations
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB Max upload size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# MongoDB Setup
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/sprites_db')
client = MongoClient(MONGO_URI)
db = client.get_default_database()
sprites_collection = db.sprites

@app.route('/')
def index():
    # Fetch all sprites to display on dashboard
    sprites = list(sprites_collection.find())
    return render_template('index.html', sprites=sprites)

@app.route('/upload', methods=['POST'])
def upload_sprites():
    category = request.form.get('category', 'general').strip().lower()
    tags_raw = request.form.get('tags', '')
    tags = [t.strip().lower() for t in tags_raw.split(',') if t.strip()]
    
    # Retrieve multiple files from the 'sprites' input field
    uploaded_files = request.files.getlist('sprites')
    
    if not uploaded_files or (len(uploaded_files) == 1 and uploaded_files[0].filename == ''):
        return "No files selected", 400

    for file in uploaded_files:
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Construct base URL dynamically for the API response
            image_url = f"/static/uploads/{filename}"
            
            # Insert into MongoDB
            sprite_data = {
                "name": filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title(),
                "filename": filename,
                "image_url": image_url,
                "category": category,
                "tags": tags
            }
            sprites_collection.insert_one(sprite_data)

    return redirect(url_for('index'))

# ==================== REST API ENDPOINTS ====================

@app.route('/api/sprites', methods=['GET'])
def get_all_sprites():
    category = request.args.get('category')
    tag = request.args.get('tag')
    
    query = {}
    if category:
        query['category'] = category.strip().lower()
    if tag:
        query['tags'] = tag.strip().lower()
        
    sprites = list(sprites_collection.find(query))
    
    output = []
    # Build complete absolute URLs based on the current host domain
    base_url = request.url_root.rstrip('/')
    
    for s in sprites:
        output.append({
            "id": str(s['_id']),
            "name": s['name'],
            "category": s['category'],
            "tags": s['tags'],
            "image_url": f"{base_url}{s['image_url']}"
        })
        
    return jsonify({"count": len(output), "sprites": output})

@app.route('/api/sprites/<id>', methods=['GET'])
def get_sprite_by_id(id):
    try:
        sprite = sprites_collection.find_one({"_id": ObjectId(id)})
        if not sprite:
            return jsonify({"error": "Sprite not found"}), 404
            
        base_url = request.url_root.rstrip('/')
        return jsonify({
            "id": str(sprite['_id']),
            "name": sprite['name'],
            "category": sprite['category'],
            "tags": sprite['tags'],
            "image_url": f"{base_url}{sprite['image_url']}"
        })
    except Exception:
        return jsonify({"error": "Invalid ID format"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
