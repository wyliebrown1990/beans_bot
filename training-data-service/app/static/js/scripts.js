document.addEventListener('DOMContentLoaded', function () {
    const fileUploadForm = document.getElementById('file-upload-form');
    const rawTextForm = document.getElementById('raw-text-submission-form');
    const filesListContainer = document.getElementById('files-list');
    const deleteJobListingForm = document.getElementById('delete-job-listing-form');
    const deleteJobListingButton = document.getElementById('delete-job-listing-button');
    const jobListingsMessage = document.getElementById('job-listings-message');
    const userId = new URLSearchParams(window.location.search).get('user_id');
    const username = new URLSearchParams(window.location.search).get('username');
    const jobListingDataContainer = document.getElementById('job-listing-data');
    const editJobListingButton = document.getElementById('edit-job-listing-button');
    const applyChangesButton = document.getElementById('apply-changes-button');
    const resumeDataContainer = document.getElementById('resume-data');
    const editResumeButton = document.getElementById('edit-resume-button');
    const applyResumeChangesButton = document.getElementById('apply-resume-changes-button');
    const statusMessage = document.getElementById('status-message');
    const homeLink = document.getElementById('home-link');

    const jobTitleSelect = document.getElementById('job_title');
    const companyNameSelect = document.getElementById('company_name');
    const industrySelect = document.getElementById('industry');

    const editJobListingLink = document.getElementById('edit-job-listing-link');
    const editResumeLink = document.getElementById('edit-resume-link');

    const questionDataLink = document.getElementById('question-data-link');
    const questionsDataContainer = document.getElementById('questions-data');

    const interviewHistoryLink = document.getElementById('interview-history-link');
    const sessionSelect = document.getElementById('session-select');

    if (interviewHistoryLink) {
        interviewHistoryLink.addEventListener('click', function() {
            window.location.href = `/interview_history.html?user_id=${userId}&username=${username}`;
        });
    }

    if (sessionSelect) {
        sessionSelect.addEventListener('change', function() {
            const selectedSessionId = this.value;
            if (selectedSessionId) {
                fetchInterviewHistory(userId, selectedSessionId);
            }
        });
        fetchSessionDates(userId);
    }

    if (questionDataLink) {
        questionDataLink.addEventListener('click', function() {
            window.location.href = `/question_data.html?user_id=${userId}&username=${username}`;
        });
    }

    if (questionsDataContainer) {
        fetchQuestionData();
    }

    if (!filesListContainer) {
        console.error('Element with id "files-list" not found.');
    }

    if (!jobListingDataContainer) {
        console.error('Element with id "job-listing-data" not found.');
    }

    if (editJobListingLink && userId && username) {
        editJobListingLink.href = `edit_job_listing.html?user_id=${userId}&username=${username}`;
    }

    if (editResumeLink && userId && username) {
        editResumeLink.href = `edit_resume.html?user_id=${userId}&username=${username}`;
    }

    if (fileUploadForm) {
        fileUploadForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const formData = new FormData(fileUploadForm);
            uploadFiles(formData);
        });
    }

    if (rawTextForm) {
        rawTextForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const formData = new FormData(rawTextForm);
            submitRawText(formData);
        });
    }

    if (deleteJobListingForm) {
        deleteJobListingForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const selectedRadio = document.querySelector('input[name="selected_job"]:checked');
            if (selectedRadio) {
                const jobId = selectedRadio.value;
                console.debug(`Selected job ID for deletion: ${jobId}`);
                deleteJobListing(jobId);
            } else {
                showStatusMessage('Please select a job listing to delete.');
            }
        });
    }

    if (userId && username) {
        console.debug(`Fetching job listings for user ID: ${userId}`);
        fetchJobListings(userId, username);
        fetchJobDescriptionDetails(userId);
        fetchJobListingData(userId);
        fetchResumeData(userId);
    }

    if (editJobListingButton) {
        editJobListingButton.addEventListener('click', function () {
            makeJobListingFieldsEditable();
        });
    }

    if (applyChangesButton) {
        applyChangesButton.addEventListener('click', function () {
            applyJobListingChanges(userId);
        });
    }

    if (editResumeButton) {
        editResumeButton.addEventListener('click', function () {
            makeResumeFieldsEditable();
        });
    }

    if (applyResumeChangesButton) {
        applyResumeChangesButton.addEventListener('click', function () {
            applyResumeChanges(userId);
        });
    }

    if (homeLink && userId && username) {
        homeLink.addEventListener('click', function () {
            window.location.href = `/?username=${username}&user_id=${userId}`;
        });
    }

    function fetchSessionDates(userId) {
        fetch(`/api/interview-history/sessions/${userId}`)
            .then(response => response.json())
            .then(data => {
                sessionSelect.innerHTML = '<option value="">Select Session</option>';
                data.forEach(session => {
                    const option = document.createElement('option');
                    option.value = session.session_id;
                    option.textContent = new Date(session.date).toLocaleDateString();
                    sessionSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error fetching session dates:', error);
                showStatusMessage('Error fetching session dates: ' + error.message);
            });
    }

    function fetchInterviewHistory(userId, sessionId) {
        fetch(`/api/interview-history/${userId}/${sessionId}`)
            .then(response => response.json())
            .then(data => {
                displaySessionSummary(data.summary);
                displaySessionTranscript(data.transcript);
            })
            .catch(error => {
                console.error('Error fetching interview history:', error);
                showStatusMessage('Error fetching interview history: ' + error.message);
            });
    }

    function displaySessionSummary(summary) {
        document.getElementById('top-score').textContent = summary.top_score;
        document.getElementById('lowest-score').textContent = summary.lowest_score;
        document.getElementById('average-score').textContent = summary.average_score;
        document.getElementById('next-steps-summary').textContent = summary.next_steps;
    }

    function displaySessionTranscript(transcript) {
        const transcriptContainer = document.getElementById('session-transcript');
        transcriptContainer.innerHTML = '<h2>Session Transcript:</h2>';
        transcript.forEach(item => {
            const group = document.createElement('div');
            group.className = 'transcript-group';
            group.innerHTML = `
                <p><strong>Question:</strong> ${item.question}</p>
                <p><strong>Answer:</strong> ${item.answer}</p>
                <p><strong>Feedback:</strong> ${item.feedback}</p>
                <p><strong>Score:</strong> ${item.score}</p>
            `;
            transcriptContainer.appendChild(group);
        });
    }

    function fetchQuestionData(filters = {}) {
        fetch(`/api/questions?${new URLSearchParams(filters)}`)
            .then(response => response.json())
            .then(data => {
                populateQuestionDataDropdowns(data);
            })
            .catch(error => {
                console.error('Error fetching question data:', error);
                showStatusMessage('Error fetching question data: ' + error.message);
            });
    }

    function populateQuestionDataDropdowns(data) {
        const container = document.getElementById('questions-data');
        if (!container) {
            console.error('Questions data container not found');
            return;
        }
        container.innerHTML = ''; // Clear existing content

        const columns = ['id', 'created_at', 'updated_at', 'is_user_submitted', 'is_role_specific',
                         'is_resume_specific', 'is_question_ai_generated', 'question_type', 'question',
                         'description', 'job_title', 'user_id'];

        columns.forEach(column => {
            const values = [...new Set(data.map(item => item[column]))];
            const dropdownHtml = createDropdown(column, values);
            container.innerHTML += dropdownHtml;
        });

        // Add event listeners to dropdowns
        container.querySelectorAll('select').forEach(select => {
            select.addEventListener('change', handleDropdownChange);
        });
    }

    function createDropdown(column, values) {
        let options = values.map(value => `<option value="${value}">${value === null ? 'NULL' : value}</option>`).join('');
        return `
            <div class="dropdown-container">
                <label for="${column}">${column}:</label>
                <select id="${column}" name="${column}">
                    <option value="">All</option>
                    ${options}
                </select>
            </div>
        `;
    }

    function handleDropdownChange(event) {
        const filters = {};
        document.querySelectorAll('#questions-data select').forEach(select => {
            if (select.value) {
                filters[select.name] = select.value;
            }
        });
        fetchQuestionData(filters);
    }

    function uploadFiles(formData) {
        fetch('/file_upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showStatusMessage(data.error);
            } else {
                showStatusMessage('Files uploaded successfully. Processing started...');
                waitForProcessingCompletion("file_upload");
            }
        })
        .catch(error => {
            console.error('Error uploading files:', error);
            showStatusMessage('Error uploading files: ' + error.message);
        });
    }

    function submitRawText(formData) {
        fetch('/raw_text_submission', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showStatusMessage(data.error);
            } else {
                showStatusMessage('Raw text submitted successfully. Processing started...');
                waitForProcessingCompletion("raw_text_submission");
            }
        })
        .catch(error => {
            console.error('Error submitting raw text:', error);
            showStatusMessage('Error submitting raw text: ' + error.message);
        });
    }

    function fetchJobListings(userId, username) {
        fetch(`/api/job-description-analysis/${userId}`)
        .then(response => response.json())
        .then(data => {
            console.debug('Fetched job listings:', data);
            if (data.error) {
                filesListContainer.innerHTML = 'Error fetching job listings: ' + data.error;
                jobListingsMessage.innerHTML = `Hey ${username}! It looks like you haven't uploaded a job description yet. To do so, please use the file or text uploading forms below. Once submitted, you may need to refresh the page to see your job listing in the Job Listings Manager.`;
            } else if (data.length === 0) {
                filesListContainer.innerHTML = 'No job listings found. Below here you can upload a file or submit the text from the job listing you wish to interview for.';
                deleteJobListingButton.style.display = 'none';
                jobListingsMessage.innerHTML = `Hey ${username}! It looks like you haven't uploaded a job description yet. To do so, please use the file or text uploading forms below. Once submitted, you may need to refresh the page to see your job listing in the Job Listings Manager.`;
            } else {
                filesListContainer.innerHTML = '';
                data.forEach(item => {
                    const listItem = document.createElement('div');
                    listItem.innerHTML = `
                        <input type="radio" name="selected_job" value="${item.id}">
                        Job Title: ${item.job_title}, Company Name: ${item.company_name}
                    `;
                    filesListContainer.appendChild(listItem);
                });
                deleteJobListingButton.style.display = 'block';
                jobListingsMessage.innerHTML = `Hey ${username}! It looks like you’ve already uploaded a job listing. I currently allow users to store 1 job listing at a time. Review the listing below and feel free to move forward with our interview or if you would like, delete the existing listing and upload a new one.`;
            }
        })
        .catch(error => {
            console.error('Error fetching job listings:', error);
            if (filesListContainer) filesListContainer.innerHTML = 'Error fetching job listings: ' + error.message;
            if (jobListingsMessage) jobListingsMessage.innerHTML = `Hey ${username}! It looks like you haven't uploaded a job description yet. To do so, please use the file or text uploading forms below. Once submitted, you may need to refresh the page to see your job listing in the Job Listings Manager.`;
            if (deleteJobListingButton) deleteJobListingButton.style.display = 'none';
        });
    }

    function fetchJobDescriptionDetails(userId) {
        fetch(`/api/job-description-details/${userId}`)
        .then(response => response.json())
        .then(data => {
            console.debug('Fetched job description details:', data);
            if (data.error) {
                console.error('Error fetching job description details:', data.error);
            } else {
                populateSelectField(jobTitleSelect, data.job_titles, 'Job Title');
                populateSelectField(companyNameSelect, data.company_names, 'Company Name');
                populateSelectField(industrySelect, data.industries, 'Industry');
            }
        })
        .catch(error => {
            console.error('Error fetching job description details:', error);
        });
    }

    function populateSelectField(selectElement, options, placeholder) {
        if (!selectElement) {
            console.error(`Element for ${placeholder} not found.`);
            return;
        }

        selectElement.innerHTML = '';

        if (options.length > 0) {
            options.forEach(option => {
                const optionElement = document.createElement('option');
                optionElement.value = option;
                optionElement.text = option;
                selectElement.appendChild(optionElement);
            });
            selectElement.value = options[0]; // Set the first option as default
            const otherOption = document.createElement('option');
            otherOption.value = 'Other';
            otherOption.text = 'Other';
            selectElement.appendChild(otherOption);
        } else {
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.text = `Upload a job description to get started here`;
            selectElement.appendChild(defaultOption);
        }
        selectElement.disabled = false;
    }

    function deleteJobListing(jobId) {
        console.debug(`Attempting to delete job listing with ID: ${jobId}`);
        fetch('/api/job-description-analysis/delete', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ids: [jobId] })
        })
        .then(response => response.json())
        .then(data => {
            console.debug('Delete response:', data);
            if (data.error) {
                showStatusMessage(data.error);
            } else {
                showStatusMessage('Job listing deleted successfully.');
                fetchJobListings(userId);
                fetchJobDescriptionDetails(userId);
            }
        })
        .catch(error => {
            console.error('Error deleting job listing:', error);
            showStatusMessage('Error deleting job listing: ' + error.message);
        });
    }

    function fetchJobListingData(userId) {
        fetch(`/api/job-description-analysis/${userId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error fetching job listing data:', data.error);
                    showStatusMessage('Error fetching job listing data: ' + data.error);
                    if (jobListingDataContainer) jobListingDataContainer.innerHTML = 'Error fetching job listing data.';
                } else {
                    populateJobListingData(data[0]); // Assuming there's only one job listing per user
                }
            })
            .catch(error => {
                console.error('Error fetching job listing data:', error);
                showStatusMessage('Error fetching job listing data: ' + error.message);
            });
    }

    function populateJobListingData(data) {
        if (!jobListingDataContainer) {
            console.error('Element with id "job-listing-data" not found.');
            return;
        }

        jobListingDataContainer.innerHTML = `
            <div>
                <label>Job Title:</label>
                <input type="text" id="job_title" value="${data.job_title}" readonly>
            </div>
            <div>
                <label>Job Level:</label>
                <input type="text" id="job_level" value="${data.job_level}" readonly>
            </div>
            <div>
                <label>Job Location:</label>
                <input type="text" id="job_location" value="${data.job_location}" readonly>
            </div>
            <div>
                <label>Job Type:</label>
                <input type="text" id="job_type" value="${data.job_type}" readonly>
            </div>
            <div>
                <label>Job Salary:</label>
                <input type="text" id="job_salary" value="${data.job_salary}" readonly>
            </div>
            <div>
                <label>Job Responsibilities:</label>
                <textarea id="job_responsibilities" readonly>${data.job_responsibilities}</textarea>
            </div>
            <div>
                <label>Personal Qualifications:</label>
                <textarea id="personal_qualifications" readonly>${data.personal_qualifications}</textarea>
            </div>
            <div>
                <label>Company Name:</label>
                <input type="text" id="company_name" value="${data.company_name}" readonly>
            </div>
            <div>
                <label>Company Size:</label>
                <input type="text" id="company_size" value="${data.company_size}" readonly>
            </div>
            <div>
                <label>Company Industry:</label>
                <input type="text" id="company_industry" value="${data.company_industry}" readonly>
            </div>
            <div>
                <label>Company Mission and Values:</label>
                <textarea id="company_mission_and_values" readonly>${data.company_mission_and_values}</textarea>
            </div>
            <div>
                <label>Education Background:</label>
                <textarea id="education_background" readonly>${data.education_background}</textarea>
            </div>
            <div>
                <label>Required Professional Experiences:</label>
                <textarea id="required_professional_experiences" readonly>${data.required_professional_experiences}</textarea>
            </div>
            <div>
                <label>Nice to Have Experiences:</label>
                <textarea id="nice_to_have_experiences" readonly>${data.nice_to_have_experiences}</textarea>
            </div>
            <div>
                <label>Required Skill Sets:</label>
                <textarea id="required_skill_sets" readonly>${data.required_skill_sets}</textarea>
            </div>
        `;
    }

    function fetchResumeData(userId) {
        console.log(`Fetching resume data from: /api/resume-data/${userId}`);
        fetch(`/api/resume-data/${userId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok: ' + response.statusText);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    showStatusMessage('Error fetching resume data: ' + data.error);
                    return;
                }
                console.log('Resume data:', data);
                populateResumeData(data);
            })
            .catch(error => {
                showStatusMessage('Error fetching resume data: ' + error.message);
            });
    }
    
    function populateResumeData(data) {
        if (!resumeDataContainer) {
            console.error('Element with id "resume-data" not found.');
            return;
        }

        resumeDataContainer.innerHTML = generateInputField('Header Text', 'header_text', data.header_text) +
            generateInputField('Top Section Summary', 'top_section_summary', data.top_section_summary) +
            generateInputField('Top Section List of Achievements', 'top_section_list_of_achievements', data.top_section_list_of_achievements) +
            generateInputField('Education', 'education', data.education) +
            generateInputField('Bottom Section List of Achievements', 'bottom_section_list_of_achievements', data.bottom_section_list_of_achievements) +
            generateInputField('Achievements and Awards', 'achievements_and_awards', data.achievements_and_awards) +
            generateInputField('Job Title 1', 'job_title_1', data.job_title_1) +
            generateInputField('Job Title 1 Start Date', 'job_title_1_start_date', data.job_title_1_start_date) +
            generateInputField('Job Title 1 End Date', 'job_title_1_end_date', data.job_title_1_end_date) +
            generateInputField('Job Title 1 Length', 'job_title_1_length', data.job_title_1_length) +
            generateInputField('Job Title 1 Location', 'job_title_1_location', data.job_title_1_location) +
            generateInputField('Job Title 1 Description', 'job_title_1_description', data.job_title_1_description) +
            generateInputField('Job Title 2', 'job_title_2', data.job_title_2) +
            generateInputField('Job Title 2 Start Date', 'job_title_2_start_date', data.job_title_2_start_date) +
            generateInputField('Job Title 2 End Date', 'job_title_2_end_date', data.job_title_2_end_date) +
            generateInputField('Job Title 2 Length', 'job_title_2_length', data.job_title_2_length) +
            generateInputField('Job Title 2 Location', 'job_title_2_location', data.job_title_2_location) +
            generateInputField('Job Title 2 Description', 'job_title_2_description', data.job_title_2_description) +
            generateInputField('Job Title 3', 'job_title_3', data.job_title_3) +
            generateInputField('Job Title 3 Start Date', 'job_title_3_start_date', data.job_title_3_start_date) +
            generateInputField('Job Title 3 End Date', 'job_title_3_end_date', data.job_title_3_end_date) +
            generateInputField('Job Title 3 Length', 'job_title_3_length', data.job_title_3_length) +
            generateInputField('Job Title 3 Location', 'job_title_3_location', data.job_title_3_location) +
            generateInputField('Job Title 3 Description', 'job_title_3_description', data.job_title_3_description) +
            generateInputField('Job Title 4', 'job_title_4', data.job_title_4) +
            generateInputField('Job Title 4 Start Date', 'job_title_4_start_date', data.job_title_4_start_date) +
            generateInputField('Job Title 4 End Date', 'job_title_4_end_date', data.job_title_4_end_date) +
            generateInputField('Job Title 4 Length', 'job_title_4_length', data.job_title_4_length) +
            generateInputField('Job Title 4 Location', 'job_title_4_location', data.job_title_4_location) +
            generateInputField('Job Title 4 Description', 'job_title_4_description', data.job_title_4_description) +
            generateInputField('Job Title 5', 'job_title_5', data.job_title_5) +
            generateInputField('Job Title 5 Start Date', 'job_title_5_start_date', data.job_title_5_start_date) +
            generateInputField('Job Title 5 End Date', 'job_title_5_end_date', data.job_title_5_end_date) +
            generateInputField('Job Title 5 Length', 'job_title_5_length', data.job_title_5_length) +
            generateInputField('Job Title 5 Location', 'job_title_5_location', data.job_title_5_location) +
            generateInputField('Job Title 5 Description', 'job_title_5_description', data.job_title_5_description) +
            generateInputField('Job Title 6', 'job_title_6', data.job_title_6) +
            generateInputField('Job Title 6 Start Date', 'job_title_6_start_date', data.job_title_6_start_date) +
            generateInputField('Job Title 6 End Date', 'job_title_6_end_date', data.job_title_6_end_date) +
            generateInputField('Job Title 6 Length', 'job_title_6_length', data.job_title_6_length) +
            generateInputField('Job Title 6 Location', 'job_title_6_location', data.job_title_6_location) +
            generateInputField('Job Title 6 Description', 'job_title_6_description', data.job_title_6_description) +
            generateInputField('Key Technical Skills', 'key_technical_skills', data.key_technical_skills) +
            generateInputField('Key Soft Skills', 'key_soft_skills', data.key_soft_skills) +
            generateInputField('Top Listed Skill Keyword', 'top_listed_skill_keyword', data.top_listed_skill_keyword) +
            generateInputField('Second Most Top Listed Skill Keyword', 'second_most_top_listed_skill_keyword', data.second_most_top_listed_skill_keyword) +
            generateInputField('Third Most Top Listed Skill Keyword', 'third_most_top_listed_skill_keyword', data.third_most_top_listed_skill_keyword) +
            generateInputField('Fourth Most Top Listed Skill Keyword', 'fourth_most_top_listed_skill_keyword', data.fourth_most_top_listed_skill_keyword) +
            generateInputField('Certifications and Awards', 'certifications_and_awards', data.certifications_and_awards) +
            generateInputField('Most Recent Successful Project', 'most_recent_successful_project', data.most_recent_successful_project) +
            generateInputField('Areas for Improvement', 'areas_for_improvement', data.areas_for_improvement) +
            generateInputField('Questions About Experience', 'questions_about_experience', data.questions_about_experience) +
            generateInputField('Resume Length', 'resume_length', data.resume_length) +
            generateInputField('Top Challenge', 'top_challenge', data.top_challenge);
    }

    function generateInputField(label, field, value) {
        return `
            <div>
                <label>${label}:</label>
                ${field.includes('description') || field.includes('skills') || field.includes('project') || field.includes('areas') || field.includes('questions') ? `<textarea data-field="${field}" readonly>${value}</textarea>` : `<input type="text" data-field="${field}" value="${value}" readonly>`}
            </div>
        `;
    }

    function makeResumeFieldsEditable() {
        if (!resumeDataContainer) {
            console.error('Element with id "resume-data" not found.');
            return;
        }

        const inputs = resumeDataContainer.querySelectorAll('input, textarea');
        inputs.forEach(input => input.removeAttribute('readonly'));
        editResumeButton.style.display = 'none';
        applyResumeChangesButton.style.display = 'block';
    }

    function applyResumeChanges(userId) {
        const updatedData = {};
        resumeDataContainer.querySelectorAll('input[data-field], textarea[data-field]').forEach(input => {
            const fieldName = input.getAttribute('data-field');
            updatedData[fieldName] = input.value;
        });

        showStatusMessage('Changes being written to database');

        fetch(`/api/resume-data/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updatedData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showStatusMessage('Error saving changes: ' + data.error);
            } else {
                showStatusMessage('Changes saved');
                editResumeButton.style.display = 'block';
                applyResumeChangesButton.style.display = 'none';
                const inputs = resumeDataContainer.querySelectorAll('input, textarea');
                inputs.forEach(input => input.setAttribute('readonly', true));
            }
        })
        .catch(error => {
            showStatusMessage('Error saving changes: ' + error.message);
        });
    }

    function makeJobListingFieldsEditable() {
        if (!jobListingDataContainer) {
            console.error('Element with id "job-listing-data" not found.');
            return;
        }

        const inputs = jobListingDataContainer.querySelectorAll('input, textarea');
        inputs.forEach(input => input.removeAttribute('readonly'));
        editJobListingButton.style.display = 'none';
        applyChangesButton.style.display = 'block';
    }

    function applyJobListingChanges(userId) {
        const updatedData = {
            job_title: document.getElementById('job_title').value,
            job_level: document.getElementById('job_level').value,
            job_location: document.getElementById('job_location').value,
            job_type: document.getElementById('job_type').value,
            job_salary: document.getElementById('job_salary').value,
            job_responsibilities: document.getElementById('job_responsibilities').value,
            personal_qualifications: document.getElementById('personal_qualifications').value,
            company_name: document.getElementById('company_name').value,
            company_size: document.getElementById('company_size').value,
            company_industry: document.getElementById('company_industry').value,
            company_mission_and_values: document.getElementById('company_mission_and_values').value,
            education_background: document.getElementById('education_background').value,
            required_professional_experiences: document.getElementById('required_professional_experiences').value,
            nice_to_have_experiences: document.getElementById('nice_to_have_experiences').value,
            required_skill_sets: document.getElementById('required_skill_sets').value,
        };

        showStatusMessage('Changes being written to database');

        fetch(`/api/job-description-analysis/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updatedData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showStatusMessage('Error saving changes: ' + data.error);
            } else {
                showStatusMessage('Changes saved');
                editJobListingButton.style.display = 'block';
                applyChangesButton.style.display = 'none';
                const inputs = jobListingDataContainer.querySelectorAll('input, textarea');
                inputs.forEach(input => input.setAttribute('readonly', true));
            }
        })
        .catch(error => {
            console.error('Error saving changes:', error);
            showStatusMessage('Error saving changes: ' + error.message);
        });
    }

    function showStatusMessage(message) {
        statusMessage.textContent = message;
        statusMessage.style.display = 'block';
        setTimeout(() => {
            statusMessage.style.display = 'none';
        }, 5000);
    }

    function waitForProcessingCompletion(processType) {
        console.log(`Waiting for ${processType} processing completion...`);
        setTimeout(checkProcessingStatus, 5000); // Polling every 5 seconds
    }

    function checkProcessingStatus() {
        fetch(`/api/job-description-analysis/${userId}`)
        .then(response => response.json())
        .then(data => {
            if (data.length > 0) {
                showSuccessMessageAndReload();
            } else {
                setTimeout(checkProcessingStatus, 5000);
            }
        })
        .catch(error => {
            console.error('Error checking processing status:', error);
        });
    }

    function showSuccessMessageAndReload() {
        showStatusMessage('Your job listing has successfully been processed. Navigate to the “Edit Job Listing” to view and edit the results. Or, click the “Start Interview” button at the bottom of the page.');
        setTimeout(() => {
            location.reload();
        }, 5000);
    }
});
