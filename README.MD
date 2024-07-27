# Beans Bot (Internal Name)

Beans Bot is a micro-service application built for job seekers to practice for upcoming interviews. Each service is written in python as a flask application running on Gunicorn. Persistent data storage is done with PostgreSQL. Langchain is used when calling the openai chatGPT 3.5-turbo model for processing resumes, job descriptions and user's interviews. 

The 3 micro-services and a brief descirption include: 

Auth-service: Where users signup and login for Beans Bot. Here they can create a username and upload their resume. 

Training-data-service: Where users can edit or upload their resumes, edit and submit job listings they plan to apply to, compare who their resumes compare to job listings, review previous mock interview sessions, and select the type of mock interview they want to conduct. 

Interview-service: Where users conduct mock interviews. 

---

# Auth Service

More coming soon...

---

# Training Data Service

The Training Data Service is a web application designed to assist job seekers in preparing for interviews by analyzing their resumes and job descriptions, and providing mock interview rounds. The service offers multiple interview round types, including role-specific, behavioral, and more.

## Table of Contents

- [Beans Bot (Internal Name)](#beans-bot-internal-name)
- [Auth Service](#auth-service)
- [Training Data Service](#training-data-service)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Usage](#usage)
    - [Main Pages](#main-pages)
    - [Mock Interviews](#mock-interviews)
  - [API Endpoints](#api-endpoints)
    - [File Upload](#file-upload)
    - [Resume](#resume)
    - [Job Description](#job-description)
    - [Interview History](#interview-history)
    - [Questions](#questions)
    - [Job Titles](#job-titles)
  - [Database Models](#database-models)
- [Interview Service](#interview-service)
- [Contributing](#contributing)
  - [License](#license)

## Features

- **Resume Upload and Analysis**: Upload resumes in PDF, DOCX, or TXT format for analysis.
- **Job Description Upload and Analysis**: Upload job descriptions in PDF, DOCX, or TXT format for analysis.
- **Mock Interview Rounds**: Practice different types of interview rounds including:
  - First Round
  - Behavioral Round
  - Personality Round
  - Situational Round
  - Motivational Round
  - Competency Round
  - Ethical Round
  - Job Role Specific Round
- **Interview History**: Track and review past interview sessions.
- **Job/Resume Comparison**: Compare the skills listed in your resume against a job description.

## Installation

To run the Training Data Service locally, follow these steps:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/training-data-service.git
   cd training-data-service
   ```

2. **Set up a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**:
   Make sure you have a PostgreSQL database set up and update the database URI in your environment variables.
   ```bash
   export DATABASE_URL='postgresql://username:password@localhost:5432/yourdatabase'
   ```

5. **Apply database migrations**:
   ```bash
   flask db upgrade
   ```

6. **Run the application**:
   ```bash
   flask run
   ```

## Configuration

The application uses environment variables for configuration. Below are the required variables:

- `DATABASE_URL`: The URI for the PostgreSQL database.
- `UPLOAD_FOLDER`: The folder where uploaded files will be stored.
- `OPENAI_API_KEY`: API key for OpenAI to use for resume and job description analysis.

You can create a `.env` file in the root of your project to store these variables.

## Usage

After starting the application, you can access it in your web browser at `http://localhost:5000`.

### Main Pages

- **Home**: Overview of your data and navigation to different sections.
- **Edit Resume**: Upload and edit resume details.
- **Edit Job Listing**: Upload and edit job listing details.
- **Job/Resume Comparison**: Compare your resume against a job listing.
- **Interview History**: View past interview sessions.
- **Question Data**: Manage interview questions.

### Mock Interviews

Select the type of interview round from the dropdown menu on the home page, provide the necessary details, and start practicing.

## API Endpoints

### File Upload

- **POST `/file_upload`**: Upload resume or job description files.
- **POST `/raw_text_submission`**: Submit raw text for job descriptions.

### Resume

- **GET `/api/resume-data/<int:user_id>`**: Get resume data for a user.
- **PUT `/api/resume-data/<int:user_id>`**: Update resume data for a user.
- **DELETE `/api/resume-data/<int:resume_id>`**: Delete a resume.

### Job Description

- **GET `/api/job-description-analysis/<int:user_id>`**: Get job description analysis for a user.
- **PUT `/api/job-description-analysis/<int:user_id>`**: Update job description details.
- **DELETE `/api/job-description-analysis/delete`**: Delete job descriptions.

### Interview History

- **GET `/api/interview-history/sessions/<int:user_id>`**: Get interview sessions for a user.
- **GET `/api/interview-history/<int:user_id>/<int:session_id>`**: Get interview history for a session.

### Questions

- **POST `/api/questions`**: Create a new question.
- **GET `/api/questions`**: Get questions based on filters.
- **PUT `/api/questions/<int:question_id>`**: Update a question.
- **DELETE `/api/questions/<int:question_id>`**: Delete a question.

### Job Titles

- **GET `/api/job_titles`**: Get distinct job titles for role-specific questions.

## Database Models

The main models used in the application are:

- **Users**: Stores user information.
- **Resumes**: Stores resume data for users.
- **JobDescriptions**: Stores job description data for users.
- **Questions**: Stores interview questions.
- **InterviewHistory**: Stores details of interview sessions.

---

# Interview Service

More coming soon...

# Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -m 'Add new feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Create a pull request.

## License

This project is licensed under Elevator Pitch LLC. 