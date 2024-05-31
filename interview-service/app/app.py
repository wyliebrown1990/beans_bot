import os
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    job_title = request.args.get('job_title')
    company_name = request.args.get('company_name')
    industry = request.args.get('industry')

    if job_title == 'generic':
        return redirect(url_for('generic_interview'))
    elif job_title and company_name and industry:
        return redirect(url_for('specific_interview', job_title=job_title, company_name=company_name, industry=industry))
    else:
        return "Invalid URL parameters", 400

@app.route('/generic_interview')
def generic_interview():
    first_question = "I'm all ears and whiskers! Tell me about your purr-sonal work experience and background. Can you share the tail of your career so far? I'd love to hear about the pawsitive impact you've made in your previous jobs."
    return render_template('generic_interview.html', first_question=first_question)

@app.route('/specific_interview')
def specific_interview():
    job_title = request.args.get('job_title')
    company_name = request.args.get('company_name')
    industry = request.args.get('industry')
    first_question = "I'm all ears and whiskers! Tell me about your purr-sonal work experience and background. Can you share the tail of your career so far? I'd love to hear about the pawsitive impact you've made in your previous jobs."
    return render_template('specific_interview.html', first_question=first_question, job_title=job_title, company_name=company_name, industry=industry)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5012)