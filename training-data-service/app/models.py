from app import db
from sqlalchemy import func

class TrainingData(db.Model):
    __tablename__ = 'training_data'
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(255), nullable=False)
    company_name = db.Column(db.String(255), nullable=False)
    data = db.Column(db.Text, nullable=False)
    embeddings = db.Column(db.LargeBinary, nullable=True)
    processed_files = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.TIMESTAMP, server_default=func.now())
