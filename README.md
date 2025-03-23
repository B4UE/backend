# Health Objective Assistant

A web application that helps users define and track health objectives and make better day-to-day food choices. It leverages an LLM for interactive guidance and an image recognition service for scanning food items.

## Project Structure

```
app_health/
├── backend/         # Flask backend
│   ├── app.py       # Main Flask application
│   ├── requirements.txt
│   └── services/    # Services for LLM, image recognition, etc.
├── frontend/        # Simple UI for testing
│   ├── index.html
│   ├── styles.css
│   └── scripts.js
└── README.md
```

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the Flask application:
   ```
   python app.py
   ```
   The server will start on http://localhost:5000

### Frontend Setup

The frontend is a simple HTML/CSS/JS application for testing purposes. You can open the `index.html` file directly in your browser, or serve it using a simple HTTP server:

```
cd frontend
python -m http.server 8000
```

Then open http://localhost:8000 in your browser.

## API Endpoints

### 1. Define Objective
- **URL**: `/api/define-objective`
- **Method**: POST
- **Request Body**: 
  ```json
  { 
    "objective": "string", 
    "metrics": {
      "weight": "number",
      "dietaryRestrictions": ["string"],
      "allergies": ["string"]
    }
  }
  ```
- **Response**: 
  ```json
  { 
    "status": "success", 
    "refinedObjective": "string", 
    "refinedMetrics": {
      "startingWeight": "number",
      "targetWeight": "number",
      "dietaryRestrictions": ["string"],
      "allergies": ["string"]
    }
  }
  ```

### 2. Scan Food
- **URL**: `/api/scan-food`
- **Method**: POST
- **Request Body**: Form data with `imageFile` (file) and `objectives` (string)
- **Response**: 
  ```json
  { 
    "status": "success", 
    "isAllowed": "boolean", 
    "foodItem": "string",
    "reason": "string" 
  }
  ```

### 3. Chat
- **URL**: `/api/chat`
- **Method**: POST
- **Request Body**: 
  ```json
  { 
    "userMessage": "string", 
    "context": {
      "objectives": ["string"]
    }
  }
  ```
- **Response**: 
  ```json
  { 
    "status": "success", 
    "botResponse": "string" 
  }
  ```

## Features

- Define and refine health objectives with LLM guidance
- Scan food items to check if they align with health objectives
- Chat with the assistant for health and diet advice
- View history of scanned food items

## Note

This is a prototype version with mock LLM and image recognition services. In a production environment, these would be replaced with actual API integrations.
