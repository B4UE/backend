import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import base64
from openai import OpenAI
import logging
import json

# Initialize Flask app with explicit static folder
app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/analyze": {"origins": "http://localhost:3000"}})  # Allow Next.js dev server
load_dotenv()

# Set up logging with secure format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client securely
try:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment")
        raise ValueError("API key configuration error")
    client = OpenAI()
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error("API client initialization error")
    client = None

@app.route('/')
def index():
    try:
        return app.send_static_file('index.html')
    except Exception as e:
        logger.error("Error serving index.html")
        return "Error loading application", 500

@app.route('/static/<path:path>')
def serve_static(path):
    try:
        return send_from_directory(app.static_folder, path)
    except Exception as e:
        logger.error(f"Error serving static file: {path}")
        return "File not found", 404

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('static/js', path)

@app.route('/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        if not client:
            return jsonify({
                'success': False,
                'error': 'Service configuration error'
            }), 500

        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'error': 'No image data provided'}), 400

        # Extract base64 image data
        image_data = data['image']
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]

        # Get user preferences (sanitize for logging)
        diet_type = data.get('dietType', 'none')
        allergies = data.get('allergies', [])
        health_conditions = data.get('healthConditions', [])
        
        # Log user preferences without sensitive data
        logger.info("Processing request with preferences: %s", {
            'diet_type': diet_type,
            'allergies_count': len(allergies),
            'conditions_count': len(health_conditions)
        })

        # Use GPT-4-vision-preview with a focused prompt
        logger.info("Extracting ingredients from image")
        vision_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract and list all ingredients from this image. Format them as a clean, comma-separated list."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )

        # Extract ingredients text from vision model
        ingredients_text = vision_response.choices[0].message.content
        logger.info("Ingredients extracted successfully")

        # Create system message with user preferences for analysis
        system_message = """You are a nutrition expert API that MUST return responses in valid JSON format.
CRITICAL: Your entire response must be a single JSON object with no additional text or explanation.
You must follow the exact structure below, replacing the example values with real analysis:

{
    "identified_ingredients": ["ingredient1", "ingredient2"],
    "health_benefits": ["benefit1", "benefit2"],
    "health_risks": ["risk1", "risk2"],
    "diet_compatibility": {
        "status": "positive",
        "details": ["detail1", "detail2"]
    },
    "health_impact": {
        "status": "positive",
        "details": ["detail1", "detail2"]
    }
}

For status fields, only use:
- "positive" for beneficial/compatible ingredients
- "negative" for concerning/incompatible ingredients"""

        user_message = f"""Analyze these ingredients considering the following preferences:
- Diet Type: {diet_type}
- Allergies: {', '.join(allergies) if allergies else 'None'}
- Health Conditions: {', '.join(health_conditions) if health_conditions else 'None'}

Ingredients to analyze: {ingredients_text}

Remember: Return ONLY the JSON object, no other text."""

        # Send to GPT-4 for detailed analysis
        logger.info("Analyzing ingredients")
        analysis_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=800,
            temperature=0.3  # Lower temperature for more consistent JSON formatting
        )

        analysis = analysis_response.choices[0].message.content.strip()
        logger.info("Analysis completed successfully")

        try:
            # Parse the analysis to ensure it's valid JSON
            import json
            
            # Remove any potential non-JSON text before or after the JSON object
            json_start = analysis.find('{')
            json_end = analysis.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise json.JSONDecodeError("No JSON object found", analysis, 0)
            
            analysis_json = json.loads(analysis[json_start:json_end])
            
            # Validate the required fields are present
            required_fields = ['identified_ingredients', 'health_benefits', 'health_risks', 
                             'diet_compatibility', 'health_impact']
            
            missing_fields = [field for field in required_fields if field not in analysis_json]
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
                
            # Validate nested structures
            if not isinstance(analysis_json['diet_compatibility'], dict) or \
               not isinstance(analysis_json['health_impact'], dict):
                raise ValueError("Invalid format for diet_compatibility or health_impact")
                
            # Validate status fields
            for field in ['diet_compatibility', 'health_impact']:
                if 'status' not in analysis_json[field] or \
                   analysis_json[field]['status'] not in ['positive', 'negative']:
                    raise ValueError(f"Invalid {field} status")
                    
            return jsonify({
                'success': True,
                'analysis': analysis_json
            })
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis as JSON: {str(e)}")
            logger.error(f"Raw response: {analysis}")
            return jsonify({
                'success': False,
                'error': 'Invalid analysis format'
            }), 500
        except ValueError as e:
            logger.error(f"Invalid analysis structure: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        except Exception as e:
            logger.error(f"Unexpected error processing analysis: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Error processing analysis'
            }), 500

    except Exception as e:
        error_msg = str(e)
        # Ensure we're not logging any sensitive data
        if any(sensitive in error_msg.lower() for sensitive in ['api', 'key', 'token', 'secret']):
            error_msg = 'Service configuration error'
        logger.error("Error processing request: %s", error_msg)
        return jsonify({
            'success': False,
            'error': 'Error analyzing ingredients. Please try again.'
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
