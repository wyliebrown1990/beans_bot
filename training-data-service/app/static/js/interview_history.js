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
    const sessionSelect = document.getElementById('session-select');
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
 
 
    if (sessionSelect) {
        sessionSelect.addEventListener('change', function () {
            const selectedSessionId = this.value;
            if (selectedSessionId) {
                fetchInterviewHistory(userId, selectedSessionId);
            }
        });
        fetchSessionDates(userId);
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
                <p><strong>Timer:</strong> ${item.timer}</p> <!-- Added Timer Display -->
            `;
            transcriptContainer.appendChild(group);
        });
    }
 
 
    function showStatusMessage(message) {
        statusMessage.textContent = message;
        statusMessage.style.display = 'block';
        setTimeout(() => {
            statusMessage.style.display = 'none';
        }, 5000);
    }
 });
 