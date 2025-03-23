# Ingredient Health Analyzer

This application analyzes ingredient lists from photos and provides personalized health insights based on user dietary preferences and health conditions.

## Features
- Capture photos of ingredient lists using device camera
- User health profile management (diet type, allergies, health conditions)
- Real-time ingredient analysis using OpenAI's Vision model
- Personalized health insights and warnings

## Setup

1. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

4. Run the application:
```bash
python app.py
```

The app will be available at `http://localhost:5000`

## Usage
1. Fill in your health profile (diet type, allergies, health conditions)
2. Click "Start Camera" to activate your device's camera
3. Take a photo of an ingredient list
4. Click "Analyze Ingredients" to get personalized health insights

## Requirements
- Python 3.8+
- OpenAI API key
- Device with camera access
- Modern web browser
