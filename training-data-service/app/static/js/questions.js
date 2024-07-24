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
    const jobResumeComparisonLink = document.getElementById('job-resume-comparison-link');
    const questionsDataContainer = document.getElementById('questions-data');
    const statusMessage = document.getElementById('status-message');

    // Home link navigation
    if (homeLink && userId && username) {
        homeLink.addEventListener('click', function () {
            window.location.href = `/?username=${username}&user_id=${userId}`;
        });
    }

    // Edit Resume link navigation
    if (editResumeLink && userId && username) {
        editResumeLink.addEventListener('click', function () {
            window.location.href = `edit_resume.html?user_id=${userId}&username=${username}`;
        });
    }

    // Edit Job Listing link navigation
    if (editJobListingLink && userId && username) {
        editJobListingLink.addEventListener('click', function () {
            window.location.href = `edit_job_listing.html?user_id=${userId}&username=${username}`;
        });
    }

    // Profile link navigation
    if (profileLink && userId && username) {
        profileLink.addEventListener('click', function () {
            window.location.href = `/profile.html?user_id=${userId}&username=${username}`;
        });
    }

    // Plans link navigation
    if (plansLink && userId && username) {
        plansLink.addEventListener('click', function () {
            window.location.href = `/plans.html?user_id=${userId}&username=${username}`;
        });
    }

    // Interview History link navigation
    if (interviewHistoryLink && userId && username) {
        interviewHistoryLink.addEventListener('click', function () {
            window.location.href = `/interview_history.html?user_id=${userId}&username=${username}`;
        });
    }

    // Question Data link navigation
    if (questionDataLink && userId && username) {
        questionDataLink.addEventListener('click', function () {
            window.location.href = `/question_data.html?user_id=${userId}&username=${username}`;
        });
    }

    // Job / Resume Comparison link navigation
    if (jobResumeComparisonLink && userId && username) {
        jobResumeComparisonLink.addEventListener('click', function () {
            window.location.href = `/job_resume_comparison.html?user_id=${userId}&username=${username}`;
        });
    }

    if (questionsDataContainer) {
        fetchQuestionData();
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

    function showStatusMessage(message) {
        statusMessage.textContent = message;
        statusMessage.style.display = 'block';
        setTimeout(() => {
            statusMessage.style.display = 'none';
        }, 5000);
    }
});
