document.addEventListener('DOMContentLoaded', function () {
    const userId = new URLSearchParams(window.location.search).get('user_id');
    const username = new URLSearchParams(window.location.search).get('username');

    const homeLink = document.getElementById('home-link');
    const editResumeLink = document.getElementById('edit-resume-link');
    const editJobListingLink = document.getElementById('edit-job-listing-link');
    const profileLink = document.getElementById('profile-link');
    const plansLink = document.getElementById('plans-link');
    const interviewHistoryLink = document.getElementById('interview-history-link');
    const questionDataLink = document.getElementById('question-data-link');
    const resumeUploadForm = document.getElementById('resume-upload-form');
    const resumeStatus = document.getElementById('resume-status');
    const resumeDataContainer = document.getElementById('resume-data');
    const editResumeButton = document.getElementById('edit-resume-button');
    const applyResumeChangesButton = document.getElementById('apply-resume-changes-button');
    const statusMessage = document.getElementById('status-message');
    const deleteResumeButton = document.getElementById('delete-resume-btn');

    // Navigation bar buttons
    if (homeLink && userId && username) {
        homeLink.addEventListener('click', function () {
            window.location.href = `/?username=${username}&user_id=${userId}`;
        });
    }
    if (editResumeLink && userId && username) {
        editResumeLink.addEventListener('click', function () {
            window.location.href = `edit_resume.html?user_id=${userId}&username=${username}`;
        });
    }
    if (editJobListingLink && userId && username) {
        editJobListingLink.addEventListener('click', function () {
            window.location.href = `edit_job_listing.html?user_id=${userId}&username=${username}`;
        });
    }
    if (profileLink && userId && username) {
        profileLink.addEventListener('click', function () {
            window.location.href = `/profile.html?user_id=${userId}&username=${username}`;
        });
    }
    if (plansLink && userId && username) {
        plansLink.addEventListener('click', function () {
            window.location.href = `/plans.html?user_id=${userId}&username=${username}`;
        });
    }
    if (interviewHistoryLink && userId && username) {
        interviewHistoryLink.addEventListener('click', function () {
            window.location.href = `/interview_history.html?user_id=${userId}&username=${username}`;
        });
    }
    if (questionDataLink && userId && username) {
        questionDataLink.addEventListener('click', function () {
            window.location.href = `/question_data.html?user_id=${userId}&username=${username}`;
        });
    }

    // Fetch and display resume data
    function fetchResumeData(userId) {
        fetch(`/api/resume-data/${userId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    resumeStatus.textContent = "It looks like you haven’t uploaded a resume yet.";
                } else {
                    resumeStatus.innerHTML = `
                        <label>
                            <input type="radio" name="selected_resume" value="${data.id}">
                            Uploaded resume: ${data.file_uploaded}
                        </label>`;
                    deleteResumeButton.style.display = 'block';
                    populateResumeData(data);
                }
            })
            .catch(error => {
                showStatusMessage('Error fetching resume data: ' + error.message);
            });
    }

    // Populate resume data in the UI
    function populateResumeData(data) {
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

    // Make resume fields editable
    function makeResumeFieldsEditable() {
        const inputs = resumeDataContainer.querySelectorAll('input, textarea');
        inputs.forEach(input => input.removeAttribute('readonly'));
        editResumeButton.style.display = 'none';
        applyResumeChangesButton.style.display = 'block';
    }

    // Apply resume changes
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

    // Show status message
    function showStatusMessage(message) {
        statusMessage.textContent = message;
        statusMessage.style.display = 'block';
        setTimeout(() => {
            statusMessage.style.display = 'none';
        }, 5000);
    }

    // Handle resume upload form submission
    resumeUploadForm.addEventListener('submit', function (event) {
        event.preventDefault();

        const formData = new FormData(resumeUploadForm);
        fetch('/resume_upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                showStatusMessage(data.message);
                fetchResumeData(userId);
            } else if (data.error) {
                showStatusMessage('Error: ' + data.error);
            }
        })
        .catch(error => {
            showStatusMessage('Error uploading resume: ' + error.message);
        });
    });

    // Fetch resume data for the current user
    if (userId) {
        fetchResumeData(userId);
    }

    // Edit resume button event
    editResumeButton.addEventListener('click', makeResumeFieldsEditable);

    // Apply resume changes button event
    applyResumeChangesButton.addEventListener('click', function () {
        applyResumeChanges(userId);
    });

    // Delete resume button event
    deleteResumeButton.addEventListener('click', function () {
        const selectedResumeId = document.querySelector('input[name="selected_resume"]:checked').value;
        if (selectedResumeId) {
            fetch(`/api/resume-data/${selectedResumeId}`, {
                method: 'DELETE',
            })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    showStatusMessage(data.message);
                    fetchResumeData(userId);
                } else if (data.error) {
                    showStatusMessage('Error: ' + data.error);
                }
            })
            .catch(error => {
                showStatusMessage('Error deleting resume: ' + error.message);
            });
        } else {
            showStatusMessage('No resume selected for deletion');
        }
    });
});
