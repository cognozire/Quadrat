import streamlit as st
import gspread
import json
import random
import pandas as pd
import matplotlib.pyplot as plt
import google.generativeai as genai
import os
gemini_key = st.secrets["GEMINI_KEY"]
genai.configure(api_key=str(gemini_key))
# Function to fetch user credentials from the Google Sheet


def create_service_account_file():
    secret_content = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
    if secret_content:
        with open("service_account.json", "w") as f:
            f.write(secret_content)
        return "service_account.json"
    else:
        st.error("GCP_SERVICE_ACCOUNT secret is missing!")
        return None

service_account_path = create_service_account_file()
def fetch_credentials_from_sheet():
    gc = gspread.service_account(filename=service_account_path)
    sh = gc.open_by_key("1AbgyZpYt-sln4b6Og1ahYw5uuFimL8_6Z5rQHfQYUWI")
    worksheet = sh.worksheet("Main")

    usernames = worksheet.col_values(1)[1:]  # Skip the header row
    passwords = worksheet.col_values(2)[1:]  # Skip the header row
    return dict(zip(usernames, passwords))

# Function to add a new user to the Google Sheet
def add_user_to_sheet(username, password):
    gc = gspread.service_account(filename=service_account_path)
    sh = gc.open_by_key("1AbgyZpYt-sln4b6Og1ahYw5uuFimL8_6Z5rQHfQYUWI")
    worksheet = sh.worksheet("Main")

    worksheet.append_row([username, password])

    try:
        sh.add_worksheet(title=username, rows="100", cols="20")
        user_sheet = sh.worksheet(username)
        user_sheet.append_row(["Test No", "Responses", "Score"])
    except Exception as e:
        st.error(f"Error creating sheet for user: Ensure the username is unique")

# Function to authenticate users
def authenticate(username, password):
    credentials = fetch_credentials_from_sheet()
    return credentials.get(username) == password

# Function to save test results with incrementing test number
def save_test_results(username, test_no, responses, score):
    gc = gspread.service_account(filename=service_account_path)
    sh = gc.open_by_key("1AbgyZpYt-sln4b6Og1ahYw5uuFimL8_6Z5rQHfQYUWI")
    worksheet = sh.worksheet(username)

    worksheet.append_row([str(test_no), str(responses), score])

# Function to fetch test history for a user
def fetch_test_history(username):
    gc = gspread.service_account(filename=service_account_path)
    sh = gc.open_by_key("1AbgyZpYt-sln4b6Og1ahYw5uuFimL8_6Z5rQHfQYUWI")
    worksheet = sh.worksheet(username)

    records = worksheet.get_all_records()
    return records

# Function to load questions from JSON file
def load_questions():
    with open('Q_gen_quant (1).json', 'r') as file:
        questions = json.load(file)
    return questions

# Page: Authentication
def authentication_page():
    st.title("Student Portal - Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate(username, password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.success(f"Welcome, {username}!")
        else:
            st.error("Invalid username or password.")

# Page: Signup
def signup_page():
    st.title("Student Portal - Signup")
    username = st.text_input("Choose a Username")
    password = st.text_input("Choose a Password", type="password")

    if st.button("Signup"):
        credentials = fetch_credentials_from_sheet()

        if username in credentials:
            st.error("Username already exists.")
        elif username and password:
            add_user_to_sheet(username, password)
            st.success("Signup successful! You can now log in.")
        else:
            st.error("Please provide both username and password.")

# Page: Test
def test_page():
    if "authenticated" in st.session_state and st.session_state["authenticated"]:
        username = st.session_state["username"]
        st.title(f"{username}'s Test")

        if "test_started" not in st.session_state:
            st.session_state["test_started"] = False
        if "current_question" not in st.session_state:
            st.session_state["current_question"] = 0
        if "responses" not in st.session_state:
            st.session_state["responses"] = []
        if "score" not in st.session_state:
            st.session_state["score"] = 0
        if "selected_questions" not in st.session_state:
            st.session_state["selected_questions"] = []

        questions = load_questions()

        if not st.session_state["test_started"]:
            if st.button("Start Test"):
                st.session_state["selected_questions"] = random.sample(questions, 10)
                st.session_state["test_started"] = True
                st.session_state["current_question"] = 0
                st.session_state["responses"] = []
                st.session_state["score"] = 0
        else:
            q = st.session_state["selected_questions"][st.session_state["current_question"]]
            st.write(f"Q{st.session_state['current_question'] + 1}: {q['question']}")
            options = [q['option_1'], q['option_2'], q['option_3'], q['option_4']]
            response = st.radio("Choose an option:", options, index=None, key=f"q{st.session_state['current_question']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Previous") and st.session_state["current_question"] > 0:
                    st.session_state["current_question"] -= 1
            with col2:
                if st.button("Next"):
                    if response is None:
                        st.warning("Please choose an option.")
                    else:
                        st.session_state["responses"].append({
                            "question": q['question'],
                            "correct_answer": q['correct_answer'],
                            "user_answer": response
                        })
                        if response == q['correct_answer']:
                            st.session_state["score"] += 1

                        if st.session_state["current_question"] < 9:
                            st.session_state["current_question"] += 1
                        else:
                            test_history = fetch_test_history(username)

                            if test_history:
                                test_no = max(int(str(test["Test No"])) for test in test_history if str(test["Test No"]).isdigit()) + 1
                            else:
                                test_no = 1

                            save_test_results(username, test_no, st.session_state["responses"], st.session_state["score"])
                            st.success(f"Test submitted! Your score is {st.session_state['score']}/10")
                            st.session_state["test_started"] = False

    else:
        st.warning("Please log in.")

# Page: Progress
# def progress_page():
#     if "authenticated" in st.session_state and st.session_state["authenticated"]:
#         username = st.session_state["username"]
#         st.title(f"{username}'s Progress")

#         test_history = fetch_test_history(username)

#         if test_history:
#             test_numbers = [int(test['Test No']) for test in test_history]
#             scores = [test['Score'] for test in test_history]

#             fig, ax = plt.subplots()
#             ax.bar(test_numbers, scores, color='blue', width=0.4)
#             ax.set_xlabel("Test No")
#             ax.set_ylabel("Score")
#             ax.set_title("Test Scores Over Time")
#             ax.set_ylim(0, 10) 
#             ax.set_xticks(test_numbers)
#             st.pyplot(fig)

#             # Feedback Selection
#             selected_test = st.selectbox("Select a test to view feedback", test_numbers)
#             if st.button("Get Feedback"):
#                 test_data = next((test for test in test_history if int(test['Test No']) == selected_test), None)
#                 if test_data:
                    
#                     model = genai.GenerativeModel("gemini-1.5-flash")
#                     response = model.generate_content(f"""
#                     You are an experienced tutor analyzing a student's test responses to provide constructive feedback. Below is the student's test history in JSON format. Your task is to:

#                     - Identify Strengths: Highlight areas where the student performed well.
#                     - Identify Weaknesses: Point out areas where the student struggled.
#                     - Provide Actionable Suggestions: Offer advice for improvement.
#                     - Encourage and Motivate: End with positive reinforcement.

#                     Test History: {str(test_data)}
#                     """)
                    
#                     st.success("Feedback Generated!")
#                     st.markdown(f"AI Feedback:{response.text}",unsafe_allow_html =True)
#         else:
#             st.info("No test history available.")
#     else:
#         st.warning("Please log in.")
def progress_page():
    if "authenticated" in st.session_state and st.session_state["authenticated"]:
        username = st.session_state["username"]
        st.title(f"{username}'s Progress")

        test_history = fetch_test_history(username)

        if test_history:
            test_numbers = [int(test['Test No']) for test in test_history]
            scores = [test['Score'] for test in test_history]

            fig, ax = plt.subplots()
            ax.bar(test_numbers, scores, color='blue', width=0.4)
            ax.set_xlabel("Test No")
            ax.set_ylabel("Score")
            ax.set_title("Test Scores Over Time")
            ax.set_ylim(0, 10) 
            ax.set_xticks(test_numbers)
            st.pyplot(fig)

            # Feedback Selection
            selected_test = st.selectbox("Select a test to view feedback", test_numbers)
            if st.button("Get Feedback"):
                test_data = next((test for test in test_history if int(test['Test No']) == selected_test), None)
                if test_data:
                    # Check if feedback already exists for this test
                    if "Feedback" in test_data and test_data["Feedback"]:
                        feedback = test_data["Feedback"]
                    else:
                        # Generate feedback using the AI model
                        model = genai.GenerativeModel("gemini-1.5-flash")
                        response = model.generate_content(f"""
                        You are an experienced tutor analyzing a student's test responses to provide constructive feedback. Your task is to:
                        
                        - Identify Strengths: Highlight areas where the student performed well.
                        - Identify Weaknesses: Point out areas where the student struggled.
                        - Provide Actionable Suggestions: Offer advice for improvement.
                        - Encourage and Motivate: End with positive reinforcement.
                        
                        Test History: {str(test_data)}
                        """)
                        feedback = response.text.strip()

                        # Update the Google Sheet with the feedback
                        import gspread
                        gc = gspread.service_account(filename=service_account_path)
                        sh = gc.open_by_key("1AbgyZpYt-sln4b6Og1ahYw5uuFimL8_6Z5rQHfQYUWI")
                        worksheet = sh.worksheet(username)
                        
                        # Get header row to determine the Feedback column index; add it if missing
                        header = worksheet.row_values(1)
                        if "Feedback" not in header:
                            col_index = len(header) + 1
                            worksheet.update_cell(1, col_index, "Feedback")
                        else:
                            col_index = header.index("Feedback") + 1
                        
                        # Find the row corresponding to the selected test
                        records = worksheet.get_all_records()
                        row_num = None
                        for i, record in enumerate(records, start=2):  # start=2 because row 1 is header
                            if str(record.get("Test No", "")) == str(selected_test):
                                row_num = i
                                break
                        if row_num:
                            worksheet.update_cell(row_num, col_index, feedback)
                    
                    # st.success("Feedback Retrieved!")
                    st.markdown(f"# AI Feedback:\n {feedback}", unsafe_allow_html=True)
        else:
            st.info("No test history available.")
    else:
        st.warning("Please log in.")


# Main App
def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Login", "Signup", "Test", "Progress"])

    if page == "Login":
        authentication_page()
    elif page == "Signup":
        signup_page()
    elif page == "Test":
        test_page()
    elif page == "Progress":
        progress_page()

if __name__ == "__main__":
    st.set_page_config(page_title="Student Portal")
    main()
