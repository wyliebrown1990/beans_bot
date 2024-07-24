document.addEventListener('DOMContentLoaded', function () {
    const userId = new URLSearchParams(window.location.search).get('user_id');
    const username = new URLSearchParams(window.location.search).get('username');

    const navigate = (path) => {
        if (userId && username) {
            window.location.href = `${path}?user_id=${userId}&username=${username}`;
        }
    };

    document.getElementById('home-link').addEventListener('click', function() {
        navigate('/');
    });

    document.getElementById('edit-resume-link').addEventListener('click', function() {
        navigate('/edit_resume.html');
    });

    document.getElementById('edit-job-listing-link').addEventListener('click', function() {
        navigate('/edit_job_listing.html');
    });

    document.getElementById('profile-link').addEventListener('click', function() {
        navigate('/profile.html');
    });

    document.getElementById('plans-link').addEventListener('click', function() {
        navigate('/plans.html');
    });

    document.getElementById('interview-history-link').addEventListener('click', function() {
        navigate('/interview_history.html');
    });

    document.getElementById('question-data-link').addEventListener('click', function() {
        navigate('/question_data.html');
    });

    document.getElementById('job-resume-comparison-link').addEventListener('click', function() {
        navigate('/job_resume_comparison.html');
    });

    if (userId) {
        fetch(`/api/job_resume_comparison/${userId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('comparison-content').innerHTML = `
                        <p>${data.error}</p>
                        <a href="${data.link}">Upload Now</a>
                    `;
                } else {
                    document.getElementById('comparison-content').innerHTML = `
                        <table>
                            <thead>
                                <tr>
                                    <th>Resume Skill Sets</th>
                                    <th>Job Listing Keywords</th>
                                    <th>Possible Resume Updates Before Applying</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>${data.resume_skills.join(', ')}</td>
                                    <td>${data.job_keywords.join(', ')}</td>
                                    <td>${data.missing_skills.join(', ')}</td>
                                </tr>
                            </tbody>
                        </table>
                    `;
                }
            })
            .catch(error => {
                console.error('Error fetching comparison data:', error);
                document.getElementById('comparison-content').innerHTML = '<p>Error fetching comparison data.</p>';
            });
    }
});
