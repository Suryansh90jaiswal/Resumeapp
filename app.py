from flask import Flask, request, render_template
import pdfplumber
import google.generativeai as genai
import os
import json
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set in environment variables")

# Create the Flask app instance
app = Flask(__name__)

# Configure Google Gemini API key
genai.configure(api_key=API_KEY)

# Function to extract text from PDF using pdfplumber
def extract_pdf_content(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

# Serve the landing page with upload form
@app.route('/')
def upload_form():
    return render_template('index.html')

# Handle resume upload and Google Gemini API call to optimize the resume
@app.route('/upload', methods=['POST'])
def upload_resume():
    try:
        if 'resume' not in request.files:
            return 'No file uploaded. Please upload a resume in PDF format.', 400

        file = request.files['resume']
        
        if file.filename == '':
            return 'No file selected. Please upload a PDF file.', 400

        job_description = request.form.get('job_description', '')
        if job_description.strip() == '':
            return 'Please provide a job description.', 400
        
        try:
            content = extract_pdf_content(file)
            if not content.strip():
                return 'The PDF file is empty or could not be read.', 400
        except Exception as e:
            return f"Error processing PDF: {str(e)}", 500

        try:
            prompt = (f"Please improve the following resume text based on the job description. "
                      f"Make it more organized, concise, and impactful.\n\n"
                      f"Resume:\n{content}\n\n"
                      f"Job Description:\n{job_description}")
            
            # Correct model usage for generating text
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)  # Pass the prompt directly without keyword

            optimized_resume = response.text.strip()

        except Exception as e:
            return f"An error occurred while processing your resume: {str(e)}", 500
        
        # Redirect to the result page to display the optimized resume
        return render_template('result.html', optimized_resume=optimized_resume, resume_content=content)

    except Exception as e:
        return f"An unexpected error occurred: {str(e)}", 500

# Route to improve the look and feel of the resume based on Gemini AI
@app.route('/improve_look_and_feel', methods=['POST'])
def improve_look_and_feel():
    try:
        resume_content = request.form.get('resume_content')

        if not resume_content:
            return "No resume content provided.", 400

        try:
            prompt = (f"Take the following improved resume and format it in a structured JSON format with fields: "
                      f"name, contact_info, summary, experience (with responsibilities), education, skills, and achievements.\n\n"
                      f"Resume:\n{resume_content}")

            # Use the correct model call
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)  # Pass the prompt directly

            raw_response = response.text.strip()
            print("Raw Gemini Response:", raw_response)

            # Clean the response
            clean_response = re.sub(r'```json|```', '', raw_response).strip()

            if not clean_response.startswith("{") or not clean_response.endswith("}"):
                raise ValueError("Response does not appear to be valid JSON")

            # Try parsing the JSON response
            try:
                formatted_resume = json.loads(clean_response)
            except json.JSONDecodeError as e:
                print(f"Error parsing the JSON response: {e}")
                print("Raw Response:", raw_response)
                return f"Error parsing the JSON response: {str(e)}", 500

            formatted_resume = formatted_resume if isinstance(formatted_resume, dict) else {}

            if isinstance(formatted_resume.get('achievements'), list):
                formatted_resume['achievements'] = [str(ach) for ach in formatted_resume['achievements']]

        except Exception as e:
            return f"An error occurred while formatting your resume: {str(e)}", 500

        return render_template('improved_resume.html', **formatted_resume)

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return f"An unexpected error occurred: {str(e)}", 500

# Run the app on the environment's port (needed for deployment on platforms like Render)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
