import numpy as np
import psycopg2

# Database connection parameters
db_params = {
    'dbname': 'interview_bot',
    'user': 'wyliebrown',
    'password': 'test123',
    'host': 'localhost'
}

# Connect to the database
conn = psycopg2.connect(**db_params)
cursor = conn.cursor()

# Query to fetch embeddings
query = "SELECT username, resume_embeddings FROM users;"
cursor.execute(query)
rows = cursor.fetchall()

for row in rows:
    username, embeddings_binary = row
    embeddings = np.frombuffer(embeddings_binary, dtype='float32')
    print(f"Username: {username}")
    print(f"Embeddings shape: {embeddings.shape}")
    print(f"Embeddings data: {embeddings}\n")

query = "SELECT job_title, embeddings FROM training_data;"
cursor.execute(query)
rows = cursor.fetchall()

for row in rows:
    job_title, embeddings_binary = row
    embeddings = np.frombuffer(embeddings_binary, dtype='float32')
    print(f"Job Title: {job_title}")
    print(f"Embeddings shape: {embeddings.shape}")
    print(f"Embeddings data: {embeddings}\n")

# Close the database connection
cursor.close()
conn.close()
