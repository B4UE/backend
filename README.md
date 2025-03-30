# Ingredient Health Analyzer - Backend

This application analyzes ingredient lists from photos and provides personalized health insights based on user dietary preferences and health conditions.

## Overview
This is the backend server for the Ingredient Health Analyzer. It handles image processing, ingredient analysis using AI, and generates personalized health insights based on user profiles.

## Features
- RESTful API endpoints for client interaction
- Image processing and text extraction
- Real-time ingredient analysis using OpenAI's Vision model
- Personalized health insights and warnings based on user health profiles
- User data storage and management

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

The backend API will be available at `http://localhost:5000`

## API Endpoints
- `POST /analyze` - Send image and user profile for analysis
- `GET /profile/:id` - Get user profile
- `POST /profile` - Create or update user profile

## Requirements
- Python 3.8+
- OpenAI API key
- Flask and related dependencies
