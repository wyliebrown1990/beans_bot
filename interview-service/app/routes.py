from flask import render_template, request, redirect, url_for

def setup_routes(app, session):

    @app.route('/', methods=['GET'])
    def index():
        job_title = request.args.get('job_title')
        company_name = request.args.get('company_name')
        industry = request.args.get('industry')
        username = request.args.get('username')

        print(f"Received parameters: job_title={job_title}, company_name={company_name}, industry={industry}, username={username}")

        if not username:
            return "Username is missing", 400

        if job_title == 'generic':
            print("Redirecting to generic_interview")
            return redirect(url_for('generic_interview', username=username))
        elif job_title and company_name and industry:
            print("Redirecting to specific_interview")
            return redirect(url_for('specific_interview', job_title=job_title, company_name=company_name, industry=industry, username=username))
        else:
            return render_template('index.html')  # Render index.html if no parameters or invalid parameters

    @app.route('/generic_interview')
    def generic_interview():
        username = request.args.get('username')
        first_question = "I'm all ears and whiskers! Tell me about your purr-sonal work experience and background. Can you share the tail of your career so far? I'd love to hear about the pawsitive impact you've made in your previous jobs."
        return render_template('generic_interview.html', first_question=first_question, username=username)

    @app.route('/specific_interview')
    def specific_interview():
        job_title = request.args.get('job_title')
        company_name = request.args.get('company_name')
        industry = request.args.get('industry')
        username = request.args.get('username')
        first_question = "I'm all ears and whiskers! Tell me about your purr-sonal work experience and background. Can you share the tail of your career so far? I'd love to hear about the pawsitive impact you've made in your previous jobs."
        return render_template('specific_interview.html', first_question=first_question, job_title=job_title, company_name=company_name, industry=industry, username=username)
