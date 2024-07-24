document.addEventListener('DOMContentLoaded', function () {
    const userId = new URLSearchParams(window.location.search).get('user_id');
    const username = new URLSearchParams(window.location.search).get('username');

    const resumeDataContainer = document.getElementById('resume-data');
    const editResumeButton = document.getElementById('edit-resume-button');
    const applyResumeChangesButton = document.getElementById('apply-resume-changes-button');
    const statusMessage = document.getElementById('status-message');

    const homeLink = document.getElementById('home-link');
    const editJobListingLink = document.getElementById('edit-job-listing-link');
    const editResumeLink = document.getElementById('edit-resume-link');
    const profileLink = document.getElementById('profile-link');
    const plansLink = document.getElementById('plans-link');
    const interviewHistoryLink = document.getElementById('interview-history-link');
    const questionDataLink = document.getElementById('question-data-link');
    const jobResumeComparisonLink = document.getElementById('job-resume-comparison-link');

    if (homeLink && userId && username) {
        homeLink.addEventListener('click', function () {
            window.location.href = `/?username=${username}&user_id=${userId}`;
        });
    }

    if (editJobListingLink && userId && username) {
        editJobListingLink.href = `edit_job_listing.html?user_id=${userId}&username=${username}`;
    }

    if (editResumeLink && userId && username) {
        editResumeLink.href = `edit_resume.html?user_id=${userId}&username=${username}`;
    }

    if (profileLink && userId && username) {
        profileLink.href = `profile.html?user_id=${userId}&username=${username}`;
    }

    if (plansLink && userId && username) {
        plansLink.href = `plans.html?user_id=${userId}&username=${username}`;
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

    if (jobResumeComparisonLink && userId && username) {
        jobResumeComparisonLink.addEventListener('click', function () {
            window.location.href = `/job_resume_comparison.html?user_id=${userId}&username=${username}`;
        });
    }

    if (userId && username) {
        console.log(`Fetching resume data for user ID: ${userId}`);
        fetchResumeData(userId);
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
