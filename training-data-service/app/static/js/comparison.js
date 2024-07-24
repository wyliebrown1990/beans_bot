document.addEventListener('DOMContentLoaded', function () {
    const userId = new URLSearchParams(window.location.search).get('user_id');

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
