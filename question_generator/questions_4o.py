import os
import json
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Function to generate questions
def generate_questions(job_title):
    prompt = f"""
    You are a world class job interview coach. Your job is to provide 30 of the most common questions that are asked of a {job_title}. Each question needs to be unique and different. As you return new questions make them more specific and challenging to answer. Your response needs to be formatted in JSON with {job_title} being the key and each of the 30 questions a unique value. I’m going to tell you my job title now.
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # Debug print statements
    print("Full response object:", response)
    print("Response choices:", response.choices)

    # Extract response content
    response_message = response.choices[0].message.content.strip()
    print("Response content:", response_message)

    try:
        response_json = json.loads(response_message)
    except json.JSONDecodeError:
        print(f"JSON format not returned for {job_title}")
        return None

    if not isinstance(response_json, dict) or job_title not in response_json:
        print(f"JSON format not returned for {job_title}")
        return None

    return response_json

# Main function
def main():
    job_titles = ["product manager", "sales engineer"]  # Placeholder for job titles
    questions_dir = Path("questions")
    questions_path = questions_dir / "questions_4o.json"

    # Ensure the directory and file exist
    questions_dir.mkdir(parents=True, exist_ok=True)

    all_questions = {}
    if questions_path.exists():
        with questions_path.open("r") as file:
            all_questions = json.load(file)

    # Loop through each job title
    for job_title in job_titles:
        print(f"Generating questions for {job_title}...")
        questions_returned = generate_questions(job_title)

        if questions_returned:
            all_questions.update(questions_returned)

            with questions_path.open("w") as file:
                json.dump(all_questions, file, indent=4)

            print(f"{job_title} questions saved. Moving on to next job title.")

    print("Question generation job is done")

# Run the main function
if __name__ == "__main__":
    main()
