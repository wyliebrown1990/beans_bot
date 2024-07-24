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
});
