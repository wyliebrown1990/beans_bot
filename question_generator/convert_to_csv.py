import json
import csv
import re
from datetime import datetime

# Function to remove numbers from the beginning of a question if present
def strip_numbers(question):
    return re.sub(r'^\d+\.\s*', '', question)

# Define the CSV file name
csv_file = 'job_questions.csv'

# Read JSON data from the local file
with open('questions.json', 'r') as json_file:
    data = json.load(json_file)

# Open the CSV file for writing
with open(csv_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    # Write the header
    writer.writerow([
        'id', 'user_id', 'job_title', 'is role specific?', 'is resume specific?', 
        'question_type', 'question', 'description', 'Answer Prompt', 
        'Answer Function', 'Scoring Prompt', 'Scoring Function', 
        'company_name', 'created_at', 'updated_at'
    ])

    # Initialize id counter
    id_counter = 1

    # Iterate over the JSON data and write to CSV
    for job_title, questions in data.items():
        print(f"Starting to write questions for job title: {job_title}")
        if isinstance(questions, dict):
            for key, question in questions.items():
                clean_question = strip_numbers(question)
                writer.writerow([
                    id_counter, '', job_title, 'Yes', 'No', 
                    'role specific questions', clean_question, '', 
                    '', '', '', '', '', 
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ])
                id_counter += 1
        elif isinstance(questions, list):
            for question in questions:
                clean_question = strip_numbers(question)
                writer.writerow([
                    id_counter, '', job_title, 'Yes', 'No', 
                    'role specific questions', clean_question, '', 
                    '', '', '', '', '', 
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ])
                id_counter += 1
        print(f"Successfully written questions for job title: {job_title}")

print(f"CSV file '{csv_file}' has been created successfully.")
