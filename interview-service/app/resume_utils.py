from sqlalchemy.orm import Session
from app.models import User

def get_user_resume_data(session: Session, username: str):
    print(f"Fetching resume data for user: {username}")
    try:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            print("No user found with the given username.")
            return None

        print("User found, retrieving resume data...")

        resume_data = {
            "resume_text_full": user.resume_text_full,
            "key_technical_skills": user.key_technical_skills,
            "key_soft_skills": user.key_soft_skills,
            "most_recent_job_title": user.most_recent_job_title,
            "second_most_recent_job_title": user.second_most_recent_job_title,
            "most_recent_job_title_summary": user.most_recent_job_title_summary,
            "second_most_recent_job_title_summary": user.second_most_recent_job_title_summary,
            "top_listed_skill_keyword": user.top_listed_skill_keyword,
            "second_most_top_listed_skill_keyword": user.second_most_top_listed_skill_keyword,
            "third_most_top_listed_skill_keyword": user.third_most_top_listed_skill_keyword,
            "fourth_most_top_listed_skill_keyword": user.fourth_most_top_listed_skill_keyword,
            "educational_background": user.educational_background,
            "certifications_and_awards": user.certifications_and_awards,
            "most_recent_successful_project": user.most_recent_successful_project,
            "areas_for_improvement": user.areas_for_improvement,
            "questions_about_experience": user.questions_about_experience,
            "resume_length": user.resume_length,
            "top_challenge": user.top_challenge
        }

        for key, value in resume_data.items():
            if not value:
                print(f"{key} returned blank value.")

        return tuple(resume_data.values())

    except Exception as e:
        print(f"An error occurred while fetching resume data: {e}")
        return None
