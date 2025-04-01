from fastapi import FastAPI, UploadFile, Form, HTTPException
from pydantic import BaseModel
import uvicorn
from fastapi.responses import JSONResponse
from typing import Dict
import hashlib
from openai import OpenAI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import firestore
import json
import re
import pandas as pd
import google.generativeai as genai
from google.generativeai import GenerativeModel
import os
load_dotenv()
client = OpenAI(api_key=os.getenv('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com",)

# Initialize Gemini LLM
# load_dotenv()
# Google_key = os.getenv("GOOGLE_API_KEY")
# print(str(Google_key))
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")
import firebase_admin
from firebase_admin import credentials

# cred = credentials.Certificate("/content/ir-502e5-firebase-adminsdk-3der0-0145a61d7a.json")
# firebase_admin.initialize_app(cred)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def generate_df():
    data = []
    cred = credentials.Certificate("G:/Cognozire/Alguru/Feeback_Api's/fir-502e5-firebase-adminsdk-3der0-0145a61d7a.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    docs = db.collection("test_results").get()
    for doc in docs:
         doc_data = doc.to_dict()
         doc_data['id'] = doc.id
         data.append(doc_data)
    df = pd.DataFrame(data)
    return df

def generate_feedback(email, test_id):
    df = generate_df()
    df_email = df[df['email'] == email]
    df_test_id = df_email[df_email['id'] == test_id]
    if not df_test_id.empty:
        response = df_test_id['responses'].values[0]
        feedback = model.generate_content(f"""You are an experienced tutor analyzing a student's test responses to provide constructive feedback. Below is the student's test history in JSON format. Your task is to:

Identify Strengths: Highlight areas where the student performed well, demonstrating a strong understanding of the concepts.

Identify Weaknesses: Point out areas where the student struggled or made consistent errors, indicating gaps in understanding.

Provide Actionable Suggestions: Offer specific advice on how the student can improve their performance in future tests.

Encourage and Motivate: End with positive reinforcement to keep the student motivated.
Test History:{str(response)} """)
        return feedback.text
    else:
        print("No test results found for this id")
def generate_overall_feedback(email):
    df = generate_df()
    df_email = df[df['email'] == email]
    if not df_email.empty:
        response = df_email['responses'].values 
        feedback = model.generate_content(f"""You are an experienced tutor analyzing a student's test responses to provide constructive feedback. Below is the student's test history in list format. Your task is to:
                                          Identify Strengths: Highlight areas where the student performed well, demonstrating a strong understanding of the concepts.

Identify Weaknesses: Point out areas where the student struggled or made consistent errors, indicating gaps in understanding.

Provide Actionable Suggestions: Offer specific advice on how the student can improve their performance in future tests.

Encourage and Motivate: End with positive reinforcement to keep the student motivated.

Test History:{str(response)} """)
        return feedback.text
    else:
        print("Please try again with a valid email")
    




@app.post("/get_single_feedback")
async def get_single_feedback(email: str, test_id: str):
    feedback = generate_feedback(email, test_id)
    return JSONResponse(content={"feedback": feedback})

@app.post("/get_overall_feedback")
async def get_overall_feedback(email: str):
    feedback = generate_overall_feedback(email)
    return JSONResponse(content={"feedback": feedback})

@app.post("/get_strong_weak_topics")
async def get_strong_weak_topics(email: str):   
    df = generate_df()
    df_email = df[df['email'] == email]
    if len(df_email)<10:
        return JSONResponse(content={"message": "Please attempt atleast 10 tests to enable this feature"})

    elif len(df)>=10:
        response = df_email['responses'].values[:10]
        # Assuming response is a list of responses
        formatted_data = str(response)  # Convert response to a string format suitable for the API call
        section_info = {
            'filename': 'student_performance',
            'schema': {
                'weak_topics': ['Topic#1', 'Topic#2', '...'],
                'strong_topics': ['Topic#1', 'Topic#2', '...']
            }
        }
        
        # Generate response using the client
        completion = client.chat.completions.create(
            model="deepseek-chat",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": f"""You are an Educational Performance Analyst focusing on {section_info['filename'].replace('_', ' ')}.
                    Analyze the provided student responses to identify and categorize topics into 'weak' and 'strong' based on their performance. Try to give
                    high level topics like algebra, trignometry, geometry etc in your response.
                    Do not add any explanations, introduction, or comments - return ONLY valid JSON.
                    """
                },
                {
                    "role": "user",
                    "content": f"""
                    Here is the raw data for {section_info['filename']}:
                    
                    {formatted_data}
                    
                    Convert this data into JSON that matches this schema:
                    {json.dumps(section_info['schema'], indent=2)}
                    """
                }
            ],
            temperature=0.0
        )
        
        # Extract the JSON content from the completion object
        strong_weak_topics = completion.choices[0].message.content  # Access the content attribute directly
        
        return JSONResponse(content=json.loads(strong_weak_topics))
    else:
        return JSONResponse(content={"error": "No test results found for this email"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)