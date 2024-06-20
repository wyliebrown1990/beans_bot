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
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # Debug print statements
    print("Full response object:", response)
    print("Response choices:", response.choices)

    # Extract response content
    response_content = response.choices[0].message.content.strip()

    # Debug print statement
    print("Response content:", response_content)

    try:
        response_json = json.loads(response_content)
    except json.JSONDecodeError:
        print(f"JSON format not returned for {job_title}")
        return None

    if not isinstance(response_json, dict) or job_title not in response_json:
        print(f"JSON format not returned for {job_title}")
        return None

    return response_json

# Main function
def main():
    job_titles = [
    "tech lead",
    "software engineer",
    "Full-Stack Developer",
    "Project Manager",
    "Data Analyst",
    "Business Analyst",
    "Data Engineer",
    "Mobile Developer",
    "Network Architect",
    "Data Warehouse Architect",
    "Software Architect",
    "Enterprise Architect",
    "Site Reliability Engineer",
    "Back-End Developer",
    "Software Engineering Manager",
    "Accountant",
    "Marketing Manager",
    "Financial Analyst",
    "Sales Representative, sales rep",
    "business development representative",
    "HR business partner",
    "Human Resources Manager",
    "Operations Manager",
    "IT Manager",
    "devops",
    "Product Manager",
    "Administrative Assistant, Admin",
    "Customer Service Representative",
    "Sales Manager",
    "Network Engineer",
    "Financial Manager",
    "Systems Analyst",
    "systems administrator, sys admin",
    "Senior Software Engineer",
    "Executive Assistant",
    "Mechanical Engineer",
    "Electrical Engineer",
    "Database Administrator",
    "Technical Support Specialist",
    "Professional Services Manager",
    "Quality Assurance Engineer, QA Engineer",
    "Procurement Manager",
    "Brand Manager",
    "Supply Chain Manager",
    "Web Developer",
    "Graphic Designer",
    "Software Developer",
    "Compliance Manager",
    "Auditor",
    "Logistics Manager",
    "Manufacturing Engineer",
    "Industrial Engineer",
    "Marketing Specialist",
    "Corporate Attorney",
    "Risk Manager",
    "Environmental Engineer",
    "Training and Development Manager",
    "Product Development Manager",
    "Public Relations Specialist",
    "Investment Analyst",
    "Journalist",
    "Supply Chain Analyst",
    "UX/UI Designer",
    "Network Administrator, Network Admin",
    "Biomedical Engineer",
    "Corporate Communications Manager",
    "Business Development Manager",
    "IT Support Specialist",
    "Tax Manager",
    "Cybersecurity Analyst",
    "Cybersecurity Specialist",
    "Project Coordinator",
    "Internal Auditor",
    "Process Engineer",
    "Health and Safety Manager",
    "Executive Chef",
    "Facilities Manager",
    "Purchasing Manager",
    "Real Estate Manager",
    "Operations Analyst",
    "Marketing Coordinator",
    "Strategy Consultant",
    "Investment Banker",
    "Legal Assistant",
    "Production Manager",
    "Regulatory Affairs Specialist",
    "Product Marketing Manager",
    "Mechanical Designer",
    "Data Scientist",
    "HR Generalist",
    "Corporate Trainer",
    "Field Service Engineer",
    "Event Coordinator",
    "Financial Planner",
    "Clinical Research Associate",
    "Systems Administrator",
    "Actuary",
    "Scrum Master",
    "Cloud Engineer",
    "Biostatistician",
    "Occupational Health and Safety Specialist",
    "Sales Operations Manager",
    "Firmware Engineer",
    "Customer Success Manager",
    "Credit Analyst",
    "Digital Marketing Specialist",
    "Hardware Engineer",
    "Machine Learning Engineer",
    "Information Security Manager",
    "Information Security Analyst",
    "Change Management Specialist",
    "Energy Manager",
    "Partner Account Manager",
    "Pharmacovigilance Specialist",
    "Research Scientist",
    "Application Developer",
    "Technical Writer",
    "Retail Salesperson",
    "Cashier",
    "Office Clerk",
    "Fast Food Worker",
    "Registered Nurse",
    "Waiter/Waitress",
    "Laborer",
    "Stock Clerk",
    "Janitor",
    "Food Preparation Worker",
    "General Manager",
    "Receptionist",
    "Maintenance Worker",
    "Bookkeeper",
    "Security Guard",
    "Construction Laborer",
    "Truck Driver",
    "Delivery Driver",
    "Personal Care Aide",
    "Teacher Assistant",
    "Teacher",
    "Nursing Assistant",
    "Cook",
    "Shipping Clerk",
    "Medical Assistant",
    "Chemist",
    "Home Health Aide",
    "Grounds Maintenance Worker",
    "Licensed Practical Nurse",
    "Pharmacy Technician",
    "adops, advertising operations",
    "First-Line Supervisor",
    "Cleaner",
    "Market Research Analyst",
    "Machinist",
    "Electrician",
    "Manager",
    "Childcare Worker",
    "Computer User Support Specialist",
    "Police Officer",
    "Construction Manager",
    "Human Resources Specialist",
    "Plumber",
    "Painter",
    "Dental Assistant",
    "Fitness Trainer",
    "Medical Secretary",
    "Production Worker",
    "Legal Secretary",
    "Pharmacist",
    "Quality Control Inspector",
    "Engineer",
    "Physical Therapist",
    "Occupational Therapist",
    "Veterinary Technician",
    "Paralegal",
    "Chef",
    "Dietitian",
    "Veterinarian",
    "Social Worker",
    "Radiologic Technologist",
    "Dental Hygienist",
    "Loan Officer",
    "Therapist",
    "Sales Engineer",
    "Librarian",
    "Environmental Scientist",
    "Statistician",
    "Biochemist",
    "Architect",
    "Surveyor",
    "Economist",
    "Computer Systems Analyst",
    "Computer Systems Administrator",
    "Microbiologist",
    "Art Director",
    "Epidemiologist",
    "Industrial Designer",
    "Logistician",
    "Market Research Specialist",
    "Physician",
    "Computer Programer",
    "help desk analyst",
    "social media manager",
    "video game designer",
    ".NET developer",
    "Bartender"
]  
    questions_path = Path("questions/questions.json")

    # Ensure the directory exists
    questions_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize or load existing data
    if questions_path.exists():
        with questions_path.open("r") as file:
            all_questions = json.load(file)
    else:
        all_questions = {}

    # Loop through each job title
    for job_title in job_titles:
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
