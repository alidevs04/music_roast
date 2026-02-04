import os
import json
import base64
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from huggingface_hub import InferenceClient # <--- New Library
import re


app = Flask(__name__)

# 1. SETUP HUGGING FACE CLIENT
# Get key from Render Environment Variables
# We use the Qwen 2.5 Vision model (Great for text/screenshots)
repo_id = "Qwen/Qwen2.5-VL-72B-Instruct" 
client = InferenceClient(api_key=os.environ.get("HF_API_TOKEN"))

# 2. HELPER: CONVERT IMAGE TO BASE64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 3. THE AI FUNCTION (HUGGING FACE)
def get_ai_roast(image_path):
    try:
        base64_image = encode_image(image_path)
        
        # 1. THE PROMPT
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    },
                    {
                        "type": "text",
                        "text": """
                        You are a mean music critic. Analyze this playlist and roast the user of this playlist, be insightful and harsh.
                        Output exactly 4 lines. Do not use markdown.
                        
                        Format:
                        SCORE: [/10]
                        TITLE: [Mean 3-word title]
                        ROAST: [A ruthless 5 sentence roast]
                        RED_FLAG: [One specific red flag]
                        """
                    }
                ]
            }
        ]

        # 2. CALL THE API
        completion = client.chat.completions.create(
            model=repo_id, 
            messages=messages, 
            max_tokens=500,
            temperature=0.7
        )

        raw_text = completion.choices[0].message.content
        print(f"DEBUG RAW AI: {raw_text}") 

        # 3. ROBUST PARSING (Regex Method)
        # Default values in case the AI fails completely
        result = {
            "score": "0/10",
            "title": "Taste Not Found",
            "roast": "The AI is speechless at how bad this is.",
            "red_flag": "Unreadable"
        }

        # Regex Explainer:
        # (?i)      -> Ignore Case (treats 'score' and 'SCORE' the same)
        # \** -> Allow optional bold asterisks (**)
        # score     -> The word we are looking for
        # \** -> Allow optional closing bold asterisks
        # \s*[:\-]\s* -> Allow a colon (:), a dash (-), and any spaces
        # (.*)      -> Capture everything else on the line
        
        score_match = re.search(r'(?i)^\s*[\*\-]*\s*score\s*[\*\-]*\s*[:\-]\s*(.*)', raw_text, re.MULTILINE)
        if score_match: result["score"] = score_match.group(1).strip()

        title_match = re.search(r'(?i)^\s*[\*\-]*\s*title\s*[\*\-]*\s*[:\-]\s*(.*)', raw_text, re.MULTILINE)
        if title_match: result["title"] = title_match.group(1).strip()

        roast_match = re.search(r'(?i)^\s*[\*\-]*\s*roast\s*[\*\-]*\s*[:\-]\s*(.*)', raw_text, re.MULTILINE)
        if roast_match: result["roast"] = roast_match.group(1).strip()

        flag_match = re.search(r'(?i)^\s*[\*\-]*\s*red_flag\s*[\*\-]*\s*[:\-]\s*(.*)', raw_text, re.MULTILINE)
        # Fallback: Sometimes AI writes "Red Flag:" with a space
        if not flag_match:
             flag_match = re.search(r'(?i)^\s*[\*\-]*\s*red flag\s*[\*\-]*\s*[:\-]\s*(.*)', raw_text, re.MULTILINE)
        
        if flag_match: result["red_flag"] = flag_match.group(1).strip()

        return result

    except Exception as e:
        print(f"HUGGING FACE ERROR: {e}")
        return {
            "score": "Error",
            "title": "Server Busy",
            "roast": "The free AI server is overloaded. Please try again.",
            "red_flag": "Rate Limit"
        }

# 4. WEB ROUTES
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def index():
    data = None
    if request.method == 'POST':
        if 'file' not in request.files: return render_template('index.html', data=None)
        file = request.files['file']
        if file.filename == '': return render_template('index.html', data=None)
        
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            data = get_ai_roast(filepath)
            
            if not data:
                data = {
                    "score": "Error", 
                    "title": "Server Busy", 
                    "roast": "The free AI server is busy. Please try again in 1 minute.", 
                    "red_flag": "Rate Limit"
                }

    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)





