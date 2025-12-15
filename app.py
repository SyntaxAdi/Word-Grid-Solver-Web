from flask import Flask, render_template, request, jsonify
import os
import secrets
from werkzeug.utils import secure_filename
import solver

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Ensure upload dir exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/solve', methods=['POST'])
def solve():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    file = request.files['image']
    clues = request.form.get('clues', '')
    
    if file.filename == '':
        return jsonify({"error": "No image selected"}), 400
        
    if file:
        filename = secure_filename(f"{secrets.token_hex(8)}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Call the solver
            result = solver.solve_challenge(filepath, clues)
            
            # Clean up uploaded file
            try:
                os.remove(filepath)
            except:
                pass
                
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))
    app.run(debug=False, host='0.0.0.0', port=port)
