import os
import json
import google.generativeai as genai
from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.secret_key = 'super_secret_key'  # Needed for flash messages

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- CONFIGURATION ---
# Replace with your actual key from aistudio.google.com
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_ai_roast(image_path):
    """Sends image to Gemini and robustly parses the JSON."""
    model = genai.GenerativeModel('gemini-flash-latest')
    myfile = genai.upload_file(image_path)
    
    prompt = """
    Analyze this music playlist/profile screenshot. 
    Return a raw JSON object with exactly these 4 keys:
    1. "score": A number out of 10 (e.g., "3/10").
    2. "title": A mean 3-word title for this user (e.g., "Sad Boy Hours").
    3. "roast": A 2-sentence ruthless roast of their taste.
    4. "red_flag": One specific "Red Flag" observation.
    
    IMPORTANT: Return ONLY the JSON. No markdown formatting, no backticks, no intro text.
    """
    
    try:
        response = model.generate_content([myfile, prompt])
        raw_text = response.text
        
        # DEBUG: Print what the AI actually sent (Check your terminal!)
        print(f"--- RAW AI RESPONSE ---\n{raw_text}\n-----------------------")

        # FIX: Use Regex to find the JSON object { ... }
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            clean_json = match.group(0)
            return json.loads(clean_json)
        else:
            raise ValueError("No JSON found in response")

    except Exception as e:
        print(f"ERROR: {e}") # Print error to terminal
        return {
            "score": "?/10", 
            "title": "Parsing Error", 
            "roast": "The AI is confused. Check your terminal to see why.", 
            "red_flag": "Code issue."
        }

@app.route('/', methods=['GET', 'POST'])
def index():
    data = None
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Get the structured roast
            data = get_ai_roast(filepath)
            
            # Clean up file immediately (Privacy)
            os.remove(filepath)
            
    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)