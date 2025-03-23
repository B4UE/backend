from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import base64
from PIL import Image
import io
import logging
import time
from datetime import datetime
from dotenv import load_dotenv

# Import AI21 client library
from ai21 import AI21Client
from ai21.models.chat.chat_message import SystemMessage, UserMessage, AssistantMessage

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for agent types
AGENT_DEFINE_OBJECTIVE = "defineObjective"
AGENT_DEFINE_HEALTH_PROFILE = "defineHealthProfile"
AGENT_COLLECT_HEALTH_METRICS = "collectHealthMetrics"
AGENT_SCAN_FOOD = "scanFood"

# Function to get AI21 client
def get_ai21_client():
    api_key = os.getenv("AI21_API_KEY")
    
    if not api_key:
        logger.error("AI21_API_KEY not found in environment variables")
        return None
        
    # Create the client using the API key
    return AI21Client(api_key=api_key)

# Agent type detection function
def detect_agent_type(conversation, user_profile=None):
    """
    Automatically detect which agent should handle the request based on conversation context
    using AI21's LLM for more intelligent detection
    """
    # Get the last user message
    last_message = None
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            last_message = msg
            break
    
    if not last_message:
        return AGENT_DEFINE_OBJECTIVE  # Default to objective definition if no user message
    
    # If explicit agent type is provided in the conversation context
    for msg in conversation:
        if msg.get("role") == "system" and "agent_type" in msg.get("content", ""):
            agent_type = msg.get("content").split("agent_type:")[1].strip()
            if agent_type in [AGENT_DEFINE_OBJECTIVE, AGENT_DEFINE_HEALTH_PROFILE, AGENT_COLLECT_HEALTH_METRICS, AGENT_SCAN_FOOD]:
                return agent_type
    
    try:
        # Use AI21 LLM to determine the agent type
        client = get_ai21_client()
        if not client:
            logger.error("Failed to get AI21 client for agent detection")
            return AGENT_DEFINE_OBJECTIVE
        
        # Create a system prompt that explains the agent types
        system_prompt = """
        You are an agent classifier for a health assistant application. Your task is to determine which specialized agent 
        should handle the user's request based on their message and conversation context.
        
        Available agents are:
        1. defineObjective - For setting or refining health goals and objectives (e.g., lose weight, manage diabetes)
        2. defineHealthProfile - For identifying which health metrics should be tracked for a given objective
        3. collectHealthMetrics - For collecting specific health data points from the user
        4. scanFood - For evaluating food choices against health objectives
        
        Respond with ONLY ONE of these agent names, nothing else.
        """
        
        # Create a user prompt that includes the conversation context
        user_prompt = f"Based on this conversation, which agent should handle this request? Last user message: '{last_message.get('content')}'\n\nUser profile: {json.dumps(user_profile) if user_profile else 'None'}\n\nFull conversation context: {json.dumps(conversation[-3:]) if len(conversation) > 3 else json.dumps(conversation)}"
        
        # Call the AI21 LLM
        messages = [
            SystemMessage(content=system_prompt, role="system"),
            UserMessage(content=user_prompt, role="user")
        ]
        
        response = client.chat.completions.create(
            messages=messages,
            model="jamba-large",
            max_tokens=10,     # We only need a short response
            temperature=0.1,   # Low temperature for more deterministic responses
        )
        
        # Extract the agent type from the response
        agent_response = response.choices[0].message.content.strip().lower()
        
        # Log the user message and the detected agent type
        user_message = last_message.get('content', '')
        logger.info(f"USER MESSAGE: '{user_message}'")
        logger.info(f"AI21 AGENT DETECTION: '{agent_response}'")
        
        # Map the response to one of our agent types
        selected_agent = None
        if "defineobjective" in agent_response or "objective" in agent_response:
            selected_agent = AGENT_DEFINE_OBJECTIVE
        elif "definehealth" in agent_response or "profile" in agent_response:
            selected_agent = AGENT_DEFINE_HEALTH_PROFILE
        elif "collect" in agent_response or "metrics" in agent_response:
            selected_agent = AGENT_COLLECT_HEALTH_METRICS
        elif "scan" in agent_response or "food" in agent_response:
            selected_agent = AGENT_SCAN_FOOD
        else:
            # Log the unexpected response
            logger.warning(f"Unexpected agent classification response: {agent_response}. Defaulting to defineObjective.")
            selected_agent = AGENT_DEFINE_OBJECTIVE
        
        # Log the final selected agent
        logger.info(f"SELECTED AGENT: {selected_agent}")
        return selected_agent
            
    except Exception as e:
        # Log the error and fall back to the default agent
        logger.error(f"Error in AI21 agent detection: {str(e)}")
        
        # Fall back to simple keyword matching if AI21 fails
        user_message = last_message.get("content", "").lower()
        
        # Simple fallback logic
        if any(kw in user_message for kw in ["goal", "objective", "want to", "lose weight"]):
            return AGENT_DEFINE_OBJECTIVE
        elif any(kw in user_message for kw in ["metrics", "measurement", "weight", "blood"]):
            return AGENT_COLLECT_HEALTH_METRICS
        elif any(kw in user_message for kw in ["food", "eat", "meal", "scan"]):
            return AGENT_SCAN_FOOD
        
        # Default to objective definition if we can't determine
        return AGENT_DEFINE_OBJECTIVE

# AI21 LLM service for all agents
def ai21_conversation(conversation, user_profile=None, objective=None, agent_type=None):
    """
    Process conversation using AI21's LLM
    Returns appropriate responses based on context
    """
    client = get_ai21_client()
    if not client:
        # Fallback to a simple response if AI21 client is not available
        logger.error("AI21 client not available. Check API key.")
        conversation.append({
            "role": "assistant",
            "content": "I'm sorry, but I'm having trouble connecting to my language model. Please try again later."
        })
        return {
            "status": "error",
            "message": "AI21 client not available",
            "updatedConversation": conversation
        }
    
    # Get the last user message
    last_message = conversation[-1] if conversation else {"role": "system", "content": ""}
    
    if last_message.get("role") != "user":
        return {
            "status": "error",
            "message": "Last message must be from user"
        }
    
    # Handle the case where content might be an object instead of a string
    user_message_content = last_message.get("content", "")
    if isinstance(user_message_content, dict):
        # If it's an object (like a PointerEvent), convert to a generic message
        user_message = "User interaction received"
        # Update the conversation with the string version
        conversation[-1]["content"] = user_message
    else:
        user_message = user_message_content
    
    # Prepare context based on agent type
    base_content = "You are a health advisor specialized in nutrition and personalized health recommendations."
    
    # Set system content based on agent type
    if agent_type == AGENT_DEFINE_OBJECTIVE:
        # Define objective agent
        if len(conversation) >= 5:
            # If we have several messages, we might be finalizing the objective
            system_content = base_content + """
            Based on the conversation so far, create a finalized health objective for the user.
            Format your response as: 'Based on our conversation, I've refined your health objective: [OBJECTIVE]'
            The objective should be specific, measurable, achievable, relevant, and time-bound.
            IMPORTANT: Preserve the user's exact wording for units (e.g., if they say 'lbs', don't change it to 'pounds').
            """
        else:
            system_content = base_content + """
            You're helping the user define a health objective. Ask relevant follow-up questions to understand their goals better.
            Focus on gathering information about their current health status, preferences, and constraints.
            Ask one question at a time to guide the conversation efficiently.
            """
    
    elif agent_type == AGENT_DEFINE_HEALTH_PROFILE:
        # Define health profile agent
        system_content = base_content + """
        Your task is to determine which health metrics will be needed to support the user's objective.
        DO NOT collect values yet - only identify the metrics that should be tracked.
        For each metric you identify, explain why it's relevant to the objective.
        Format your response to clearly list each metric needed.
        """
    
    elif agent_type == AGENT_COLLECT_HEALTH_METRICS:
        # Collect health metrics agent
        system_content = base_content + """
        You're helping the user track their health metrics. Ask for specific values for metrics relevant to their objective.
        Extract precise values from the user's responses and acknowledge when you've recorded a metric.
        Ask for one metric at a time and confirm values before moving to the next one.
        Format your responses to clearly show what metrics you've recorded.
        """
    
    elif agent_type == AGENT_SCAN_FOOD:
        # Scan food agent
        system_content = base_content + """
        Analyze the food item mentioned by the user and provide feedback on whether it aligns with their health objectives.
        Consider nutritional value, portion size, and how it fits into their overall diet plan.
        Format your response to clearly state whether the food is recommended or not, and provide a brief explanation.
        Your response MUST include a clear yes/no recommendation and detailed reasoning.
        """
    
    # Default general conversation
    else:
        system_content = base_content + """
        Provide helpful, accurate health information based on the user's query. If you're unsure about something,
        be transparent about your limitations and avoid giving potentially harmful advice.
        """
    
    # Add user profile context if available
    if user_profile:
        profile_context = "User profile information:\n"
        for key, value in user_profile.items():
            profile_context += f"- {key}: {value}\n"
        system_content += "\n\n" + profile_context
    
    # Add objective context if available
    if objective:
        system_content += f"\n\nThe user's current health objective is: {objective}"
    
    try:
        # Convert conversation history to AI21 format
        ai21_messages = []
        
        # Add system message
        ai21_messages.append(SystemMessage(content=system_content, role="system"))
        
        # Add conversation history (excluding the last user message which we'll add separately)
        for msg in conversation[:-1]:
            if msg["role"] == "user":
                ai21_messages.append(UserMessage(content=msg["content"], role="user"))
            elif msg["role"] == "assistant":
                ai21_messages.append(AssistantMessage(content=msg["content"], role="assistant"))
        
        # Add the last user message
        ai21_messages.append(UserMessage(content=user_message, role="user"))
        
        # Call AI21 API
        response = client.chat.completions.create(
            messages=ai21_messages,
            model="jamba-mini",  # Use appropriate model
            max_tokens=500,
            temperature=0.7,
        )
        
        # Extract the response
        assistant_response = response.choices[0].message.content
        
        # Add AI21 response to conversation
        conversation.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # Process response based on agent type
        if agent_type == AGENT_DEFINE_OBJECTIVE:
            # For objective definition
            objective_text = ""
            
            # Try to extract the objective from the AI21 response - more permissive extraction
            if "I've refined your health objective:" in assistant_response:
                objective_text = assistant_response.split("I've refined your health objective:")[1].strip()
            elif "health objective:" in assistant_response.lower():
                objective_text = assistant_response.split("health objective:")[1].strip()
            
            # Try to extract objective from user's message if not found in assistant response
            if not objective_text:
                # Check for common objective patterns in the user's message
                user_msg = user_message.lower()
                
                # Weight loss objectives
                if ("lose" in user_msg or "losing" in user_msg) and any(unit in user_msg for unit in ["pound", "pounds", "lbs", "kg", "kilo", "kilos", "weight"]):
                    # Extract the amount and timeframe if available
                    import re
                    amount_match = re.search(r'\b(\d+)\s*(pound|pounds|lbs|kg|kilo|kilos)\b', user_message)
                    time_match = re.search(r'\b(in|within|over)\s*(\d+)\s*(week|weeks|month|months|day|days)\b', user_message)
                    
                    if amount_match:
                        amount = amount_match.group(1)
                        unit = amount_match.group(2)
                        timeframe = ""
                        if time_match:
                            timeframe = f" in {time_match.group(2)} {time_match.group(3)}"
                        objective_text = f"Lose {amount} {unit}{timeframe}"
                
                # Diabetes management
                elif "diabetes" in user_msg:
                    objective_text = "Manage diabetes through diet, exercise, and regular monitoring"
                    if "type 2" in user_msg or "type2" in user_msg:
                        objective_text = "Manage type 2 diabetes through diet, exercise, and regular monitoring"
                    elif "type 1" in user_msg or "type1" in user_msg:
                        objective_text = "Manage type 1 diabetes through diet, exercise, and regular monitoring"
                
                # Blood pressure objectives
                elif "blood pressure" in user_msg or "hypertension" in user_msg:
                    objective_text = "Lower blood pressure through diet, exercise, and stress management"
                
                # Fitness objectives
                elif "fitness" in user_msg or "muscle" in user_msg or "strength" in user_msg:
                    if "build" in user_msg or "gain" in user_msg or "increase" in user_msg:
                        objective_text = "Build muscle and increase strength through regular exercise"
                    else:
                        objective_text = "Improve overall fitness and physical health"
            
            # Return both the conversation and the detected objective
            return {
                "status": "success",
                "updatedConversation": conversation,
                "objective": objective_text,
                "detectedObjective": objective_text if objective_text else None
            }
            
        elif agent_type == AGENT_DEFINE_HEALTH_PROFILE:
            # For health profile definition
            updated_profile = user_profile.copy() if user_profile else {}
            metrics = []
            
            # Try to extract metrics from the AI21 response
            # This is a simplified approach - in production, you'd use more sophisticated NLP
            potential_metrics = [
                "weight", "height", "bmi", "bloodSugar", "bloodPressure", "cholesterol", 
                "heartRate", "allergies", "dietaryRestrictions", "activityLevel", "sleepHours",
                "waterIntake", "calorieIntake", "proteinIntake", "carbIntake", "fatIntake"
            ]
            
            for metric in potential_metrics:
                if metric.lower() in assistant_response.lower():
                    # Add the metric to the user profile with empty value
                    if "metrics" not in updated_profile:
                        updated_profile["metrics"] = []
                        
                    # Check if metric already exists
                    metric_exists = False
                    for existing_metric in updated_profile.get("metrics", []):
                        if existing_metric.get("name") == metric:
                            # Add the objective to the metric's objectives list if not already there
                            if objective and objective not in existing_metric.get("objectives", []):
                                if "objectives" not in existing_metric:
                                    existing_metric["objectives"] = []
                                existing_metric["objectives"].append(objective)
                            metric_exists = True
                            break
                    
                    # Add new metric if it doesn't exist
                    if not metric_exists and objective:
                        updated_profile["metrics"].append({
                            "name": metric,
                            "value": "",
                            "objectives": [objective]
                        })
                        metrics.append(metric)
            
            return {
                "status": "success",
                "updatedConversation": conversation,
                "updatedUserProfile": updated_profile
            }
            
        elif agent_type == AGENT_COLLECT_HEALTH_METRICS:
            # For health metrics collection
            updated_profile = user_profile.copy() if user_profile else {}
            
            # Initialize metrics array if it doesn't exist
            if "metrics" not in updated_profile:
                updated_profile["metrics"] = []
                
            # Extract metrics from the conversation
            # This is a simplified approach - in production, you'd use more sophisticated NLP
            metrics_to_check = {
                "weight": ["weight", "pounds", "kg", "lbs"],
                "height": ["height", "feet", "inches", "cm", "tall"],
                "bloodSugar": ["blood sugar", "glucose", "diabetes", "mg/dl"],
                "bloodPressure": ["blood pressure", "bp", "systolic", "diastolic", "mmHg"],
                "cholesterol": ["cholesterol", "ldl", "hdl", "triglycerides"],
                "allergies": ["allergy", "allergic", "reaction"],
                "dietaryRestrictions": ["diet", "restriction", "vegetarian", "vegan", "gluten"]
            }
            
            for metric_name, keywords in metrics_to_check.items():
                if any(keyword in user_message.lower() for keyword in keywords):
                    # Try to extract the value from the user message
                    # This is a simplified extraction - in production you'd use NER or regex
                    value = "Updated from conversation"
                    
                    # Check if metric already exists
                    metric_exists = False
                    for metric in updated_profile.get("metrics", []):
                        if metric.get("name") == metric_name:
                            metric["value"] = value
                            metric_exists = True
                            break
                    
                    # Add new metric if it doesn't exist
                    if not metric_exists:
                        updated_profile["metrics"].append({
                            "name": metric_name,
                            "value": value,
                            "objectives": [objective] if objective else []
                        })
            
            return {
                "status": "success",
                "updatedConversation": conversation,
                "updatedUserProfile": updated_profile
            }
            
        elif agent_type == AGENT_SCAN_FOOD:
            # For food scanning
            is_allowed = True  # Default to allowed
            food_item = "food item"  # Default food item
            
            # Simple heuristic to determine if food is allowed
            negative_terms = ["not recommended", "avoid", "limit", "high in calories", "unhealthy", "processed", "not allowed", "shouldn't eat"]
            if any(term in assistant_response.lower() for term in negative_terms):
                is_allowed = False
            
            # Try to extract food item name (simplified approach)
            food_terms = ["apple", "banana", "pizza", "burger", "salad", "chicken", "fish", "meat", "vegetables", "fruit"]
            for term in food_terms:
                if term in user_message.lower() or term in assistant_response.lower():
                    food_item = term
                    break
            
            return {
                "status": "success",
                "updatedConversation": conversation,
                "result": {
                    "isAllowed": is_allowed,
                    "reason": assistant_response
                }
            }
        
        # Default return for general conversation
        return {
            "status": "success",
            "updatedConversation": conversation
        }
        
    except Exception as e:
        logger.error(f"Error in AI21 conversation: {str(e)}")
        conversation.append({
            "role": "assistant",
            "content": "I apologize, but I encountered an error processing your request. Please try again."
        })
        return {
            "status": "error",
            "message": str(e),
            "updatedConversation": conversation
        }

# Mock image recognition service
def mock_image_recognition(image_data, user_profile=None):
    """
    Mock image recognition for development purposes
    In a real implementation, this would call an image recognition API
    """
    # For demo purposes, we'll just return a mock response
    # In a real implementation, this would analyze the image and identify the food
    
    # Randomly choose between allowed and not allowed for demo purposes
    import random
    is_allowed = random.choice([True, False])
    
    if is_allowed:
        return {
            "foodItem": "Apple",
            "isAllowed": True,
            "reason": "Apples are a healthy fruit that align with your weight loss objective."
        }
    else:
        return {
            "foodItem": "Chocolate Cake",
            "isAllowed": False,
            "reason": "Chocolate cake is high in sugar and calories, which may not align with your weight loss goal."
        }

@app.route('/api/define-objective', methods=['POST'])
def define_objective():
    """
    Endpoint to define or refine a health objective through conversation
    Takes the current conversation with the user about their objective
    Returns an updated conversation with additional questions or clarifications
    """
    try:
        data = request.json
        conversation = data.get('conversation', [])
        
        if not conversation:
            return jsonify({"status": "error", "message": "Conversation is required"}), 400
        
        logger.info(f"Received objective conversation with {len(conversation)} messages")
        
        # Process the conversation with the AI21 LLM
        response = ai21_conversation(conversation)
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in define-objective: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/define-health-profile', methods=['POST'])
def define_health_profile():
    """
    Endpoint to define or update a user's health profile based on their objective
    Takes a finalized objective and existing user profile to produce an updated profile
    """
    try:
        data = request.json
        objective = data.get('objective', '')
        user_profile = data.get('userProfile', {})
        
        if not objective:
            return jsonify({"status": "error", "message": "Objective is required"}), 400
        
        logger.info(f"Received health profile update request for objective: {objective}")
        
        # In a real implementation, this would call the LLM to analyze the objective
        # and determine what metrics are needed
        
        # Mock implementation - add relevant metrics based on the objective
        updated_profile = user_profile.copy()
        
        # Check if the objective is related to weight loss
        if "lose" in objective.lower() and ("weight" in objective.lower() or "pounds" in objective.lower() or "lbs" in objective.lower()):
            # Add weight-related metrics if they don't exist
            if "weight" not in updated_profile:
                updated_profile["weight"] = "unknown"
            if "targetWeight" not in updated_profile:
                updated_profile["targetWeight"] = "unknown"
            if "height" not in updated_profile:
                updated_profile["height"] = "unknown"
            if "activityLevel" not in updated_profile:
                updated_profile["activityLevel"] = "unknown"
        
        # Check if the objective is related to dietary restrictions
        if "gluten" in objective.lower() or "allergy" in objective.lower() or "vegetarian" in objective.lower() or "vegan" in objective.lower():
            if "dietaryRestrictions" not in updated_profile:
                updated_profile["dietaryRestrictions"] = []
            if "allergies" not in updated_profile:
                updated_profile["allergies"] = []
        
        # Check if the objective is related to medical conditions
        if "diabetes" in objective.lower() or "blood sugar" in objective.lower() or "glucose" in objective.lower():
            if "bloodSugar" not in updated_profile:
                updated_profile["bloodSugar"] = "unknown"
        
        if "cholesterol" in objective.lower() or "heart" in objective.lower():
            if "cholesterol" not in updated_profile:
                updated_profile["cholesterol"] = "unknown"
            if "bloodPressure" not in updated_profile:
                updated_profile["bloodPressure"] = "unknown"
        
        # Associate metrics with the objective
        for key in updated_profile:
            if isinstance(updated_profile[key], dict) and "objectiveIds" in updated_profile[key]:
                if objective not in updated_profile[key]["objectiveIds"]:
                    updated_profile[key]["objectiveIds"].append(objective)
            else:
                # Convert simple values to objects with objectiveIds
                value = updated_profile[key]
                updated_profile[key] = {
                    "value": value,
                    "objectiveIds": [objective]
                }
        
        return jsonify({
            "status": "success",
            "updatedUserProfile": updated_profile
        })
    except Exception as e:
        logger.error(f"Error in define-health-profile: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/collect-health-metrics', methods=['POST'])
def collect_health_metrics():
    """
    Endpoint to collect health metrics through conversation
    Conducts a conversation with the user to gather health metrics
    """
    try:
        data = request.json
        conversation = data.get('conversation', [])
        objective = data.get('objective', '')
        user_profile = data.get('userProfile', {})
        
        if not conversation:
            return jsonify({"status": "error", "message": "Conversation is required"}), 400
        
        logger.info(f"Received health metrics conversation with {len(conversation)} messages")
        
        # Process the conversation with the AI21 LLM
        response = ai21_conversation(conversation, user_profile, objective)
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in collect-health-metrics: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/scan-food', methods=['POST'])
def scan_food():
    """
    Endpoint to scan food and check against user profile and objectives
    Conversational endpoint for evaluating whether a food item meets the user's constraints
    """
    try:
        data = request.json
        conversation = data.get('conversation', [])
        user_profile = data.get('userProfile', {})
        
        # Check if there's an image in the request
        image_data = None
        if request.files and 'imageFile' in request.files:
            # Handle file upload
            image_file = request.files['imageFile']
            image_data = image_file.read()
        elif data.get('imageData'):
            # Handle base64 encoded image
            image_data = base64.b64decode(data.get('imageData'))
        
        logger.info(f"Received food scan request with image: {image_data is not None}")
        
        # If there's an image, process it with image recognition
        if image_data:
            # In a real implementation, this would call an image recognition service
            recognition_result = mock_image_recognition(image_data, user_profile)
            
            # Add the recognition result to the conversation
            conversation.append({
                "role": "system",
                "content": f"Image recognized as: {recognition_result['foodItem']}"
            })
            
            # Add a user message about the recognized food
            conversation.append({
                "role": "user",
                "content": f"Is {recognition_result['foodItem']} allowed for my diet?"
            })
        
        # Process the conversation with the AI21 LLM
        response = ai21_conversation(conversation, user_profile)
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in scan-food: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/orchestrate', methods=['POST'])
def orchestrate():
    """
    Orchestration endpoint that receives all messages, categorizes the request,
    and routes it to the correct internal agent
    """
    try:
        data = request.json
        conversation = data.get('conversation', [])
        user_profile = data.get('userProfile', {})
        objective = data.get('objective', '')
        agent_type = data.get('agentType', None)
        
        if not conversation:
            return jsonify({"status": "error", "message": "Conversation is required"}), 400
        
        # Detect agent type if not explicitly provided
        if not agent_type:
            agent_type = detect_agent_type(conversation, user_profile)
        
        logger.info(f"Orchestrating request to agent type: {agent_type}")
        
        # Route to appropriate agent
        if agent_type == AGENT_DEFINE_OBJECTIVE:
            # Define objective agent
            response = ai21_conversation(conversation, user_profile, objective, AGENT_DEFINE_OBJECTIVE)
            
            # If a new objective was detected, include it in the response
            if response.get("detectedObjective"):
                response["detectedObjective"] = response.get("detectedObjective")
            
            return jsonify(response)
            
        elif agent_type == AGENT_DEFINE_HEALTH_PROFILE:
            # Define health profile agent
            if not objective:
                return jsonify({"status": "error", "message": "Objective is required for health profile definition"}), 400
                
            # Process with AI21 to determine needed metrics
            updated_profile = user_profile.copy() if user_profile else {}
            
            # Create a copy of the conversation
            profile_conversation = conversation.copy()
            
            # Make sure the last message is from the user
            if profile_conversation and profile_conversation[-1].get("role") == "user":
                # Insert the system message before the last user message
                profile_conversation.insert(len(profile_conversation) - 1, {
                    "role": "system",
                    "content": f"Based on the objective '{objective}', determine what health metrics should be tracked."
                })
            else:
                # If there's no user message at the end, just use the original conversation
                logger.warning("No user message found at the end of the conversation for health profile definition")
            
            # Process with AI21
            response = ai21_conversation(profile_conversation, updated_profile, objective, AGENT_DEFINE_HEALTH_PROFILE)
            
            # Extract metrics from AI21 response
            if "updatedUserProfile" not in response:
                response["updatedUserProfile"] = updated_profile
                
            return jsonify(response)
            
        elif agent_type == AGENT_COLLECT_HEALTH_METRICS:
            # Collect health metrics agent
            response = ai21_conversation(conversation, user_profile, objective, AGENT_COLLECT_HEALTH_METRICS)
            return jsonify(response)
            
        elif agent_type == AGENT_SCAN_FOOD:
            # Scan food agent
            # Check if there's an image in the request
            image_data = None
            if request.files and 'imageFile' in request.files:
                # Handle file upload
                image_file = request.files['imageFile']
                image_data = image_file.read()
            elif data.get('imageData'):
                # Handle base64 encoded image
                image_data = base64.b64decode(data.get('imageData'))
            
            # If there's an image, process it with image recognition
            if image_data:
                # In a real implementation, this would call an image recognition service
                recognition_result = mock_image_recognition(image_data, user_profile)
                
                # Add the recognition result to the conversation
                conversation.append({
                    "role": "system",
                    "content": f"Image recognized as: {recognition_result['foodItem']}"
                })
                
                # Add a user message about the recognized food
                conversation.append({
                    "role": "user",
                    "content": f"Is {recognition_result['foodItem']} allowed for my diet?"
                })
            
            # Process with AI21
            response = ai21_conversation(conversation, user_profile, objective, AGENT_SCAN_FOOD)
            return jsonify(response)
        
        else:
            # Unknown agent type
            return jsonify({"status": "error", "message": f"Unknown agent type: {agent_type}"}), 400
            
    except Exception as e:
        logger.error(f"Error in orchestration: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/image-scan', methods=['POST'])
def image_scan():
    """
    Endpoint for uploading an image and returning a detailed description of its contents
    """
    try:
        # Check if there's an image in the request
        image_data = None
        if request.files and 'imageFile' in request.files:
            # Handle file upload
            image_file = request.files['imageFile']
            image_data = image_file.read()
        elif request.json and request.json.get('imageData'):
            # Handle base64 encoded image
            image_data = base64.b64decode(request.json.get('imageData'))
            
        if not image_data:
            return jsonify({"status": "error", "message": "Image data is required"}), 400
            
        # Process the image
        recognition_result = mock_image_recognition(image_data)
        
        return jsonify({
            "status": "success",
            "description": f"Image recognized as: {recognition_result['foodItem']}",
            "foodItem": recognition_result['foodItem'],
            "isAllowed": recognition_result['isAllowed'],
            "reason": recognition_result['reason']
        })
        
    except Exception as e:
        logger.error(f"Error in image-scan: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
