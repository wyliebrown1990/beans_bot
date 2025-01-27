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
    const interviewTypeDropdown = document.getElementById('interview-type-dropdown');
    const secondaryDropdownContainer = document.getElementById('secondary-dropdown-container');
    const jobRoleDropdown = document.getElementById('job-role-dropdown');
    const newJobTitleContainer = document.getElementById('new-job-title-container');
    const newJobTitleInput = document.getElementById('new-job-title');
    const submitNewJobTitleButton = document.getElementById('submit-new-job-title');
    const interviewDetailsContent = document.getElementById('interview-details-content');
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

    // Fetch job description data
    function fetchJobDescription(userId) {
        return fetch(`/api/job-description-analysis/${userId}`)
            .then(response => response.json())
            .then(data => {
                if (data.length > 0) {
                    return data[0];
                }
                return null;
            })
            .catch(error => {
                console.error('Error fetching job description:', error);
                return null;
            });
    }

    // Fetch resume data
    function fetchResumeData(userId) {
        return fetch(`/api/resume-data/${userId}`)
            .then(response => response.json())
            .then(data => {
                if (!data.error) {
                    return data;
                }
                return null;
            })
            .catch(error => {
                console.error('Error fetching resume data:', error);
                return null;
            });
    }

    // Fetch job titles for Job Role Specific Interview Round
    function fetchJobTitles() {
        return fetch('/api/job_titles')
            .then(response => response.json())
            .then(data => data.job_titles || [])
            .catch(error => {
                console.error('Error fetching job titles:', error);
                return [];
            });
    }

    // Dropdown change event
    interviewTypeDropdown.addEventListener('change', function () {
        const selectedValue = interviewTypeDropdown.value;
        let interviewDetails = '';

        if (selectedValue === 'job_role_round') {
            fetchJobTitles().then(jobTitles => {
                jobTitles.sort((a, b) => a.localeCompare(b)); // Sort job titles alphabetically
                jobRoleDropdown.innerHTML = '<option value="">Click here</option>';
                jobTitles.forEach(jobTitle => {
                    jobRoleDropdown.innerHTML += `<option value="${jobTitle}">${jobTitle}</option>`;
                });
                jobRoleDropdown.innerHTML += '<option value="add_new_role">Add New Role</option>';
                secondaryDropdownContainer.style.display = 'block';
            });
        } else {
            secondaryDropdownContainer.style.display = 'none';
            newJobTitleContainer.style.display = 'none';
            switch (selectedValue) {
                case 'first_round':
                    interviewDetails = `
                        <h3>First Round Interview</h3>
                        <h4>Description:</h4>
                        <p>This interview is designed to simulate the first interview you will have with a company. Sometimes this is with an HR person, other times it will be with your hiring manager.</p>
                        <h4>Question Types:</h4>
                        <p>Resume Related, Job Listing Related, Behavioral, Situational, Personality, Motivational, Competency and Ethical.</p>
                        <h4>User Input Required:</h4>
                        <p>You must have already uploaded a job listing and resume.</p>
                        <h4>Interview Length:</h4>
                        <p>30 minutes.</p>
                        <button id="start-interview-button" class="start-interview-button">Start Interview</button>
                    `;
                    break;
                case 'behavioral_round':
                    interviewDetails = `
                        <h3>Behavioral Round Interview</h3>
                        <h4>Description:</h4>
                        <p>This interview is designed to put you through the most commonly asked behavioral questions that come up in interviews. Behavioral interview questions are designed to assess a candidate's past behavior and experiences to predict their future performance in similar situations. They often start with phrases like "Tell me about a time when..." and focus on specific examples of skills, problem-solving, teamwork, and adaptability.</p>
                        <h4>Question Types:</h4>
                        <p>Behavioral.</p>
                        <h4>Interview Length:</h4>
                        <p>20 minutes.</p>
                        <h4>User Input Required:</h4>
                        <p>Any user can practice behavioral questions without having uploaded a resume or job listing.</p>
                        <button id="start-interview-button" class="start-interview-button">Start Interview</button>
                    `;
                    break;
                case 'personality_round':
                    interviewDetails = `
                        <h3>Personality Round Interview</h3>
                        <h4>Description:</h4>
                        <p>This interview is designed to put you through the most commonly asked behavioral questions that come up in interviews. Personality job interview questions aim to understand a candidate's traits, attitudes, and interpersonal skills to determine their cultural fit and how they may interact with the team. These questions explore aspects like work style, motivation, and how the candidate handles various work situations.</p>
                        <h4>Question Types:</h4>
                        <p>Personality.</p>
                        <h4>Interview Length:</h4>
                        <p>20 minutes.</p>
                        <h4>User Input Required:</h4>
                        <p>Any user can practice personality questions without having uploaded a resume or job listing.</p>
                        <button id="start-interview-button" class="start-interview-button">Start Interview</button>
                    `;
                    break;
                case 'situational_round':
                    interviewDetails = `
                        <h3>Situational Round Interview</h3>
                        <h4>Description:</h4>
                        <p>This interview is designed to put you through the most commonly asked situational questions that come up in interviews. Situational job interview questions present hypothetical scenarios to candidates, asking them to describe how they would handle specific challenges or situations in the workplace. These questions aim to gauge problem-solving skills, decision-making abilities, and how candidates apply their knowledge and experience to potential job-related scenarios.</p>
                        <h4>Question Types:</h4>
                        <p>Situational.</p>
                        <h4>Interview Length:</h4>
                        <p>20 minutes.</p>
                        <h4>User Input Required:</h4>
                        <p>Any user can practice situational questions without having uploaded a resume or job listing.</p>
                        <button id="start-interview-button" class="start-interview-button">Start Interview</button>
                    `;
                    break;
                case 'motivational_round':
                    interviewDetails = `
                        <h3>Motivational Round Interview</h3>
                        <h4>Description:</h4>
                        <p>This interview is designed to put you through the most commonly asked motivational questions that come up in interviews. Motivational job interview questions aim to understand what drives and inspires a candidate, including their goals, values, and reasons for pursuing the job. These questions help assess whether the candidate's motivations align with the role and the organization's culture.</p>
                        <h4>Question Types:</h4>
                        <p>Motivational.</p>
                        <h4>Interview Length:</h4>
                        <p>20 minutes.</p>
                        <h4>User Input Required:</h4>
                        <p>Any user can practice motivational questions without having uploaded a resume or job listing.</p>
                        <button id="start-interview-button" class="start-interview-button">Start Interview</button>
                    `;
                    break;
                case 'competency_round':
                    interviewDetails = `
                        <h3>Competency Round Interview</h3>
                        <h4>Description:</h4>
                        <p>This interview is designed to put you through the most commonly asked competency based questions that come up in interviews. Competency-based job interview questions focus on assessing a candidate's specific skills and abilities required for the role by asking for examples of past experiences where they demonstrated these competencies. These questions are designed to evaluate how effectively a candidate can perform essential job functions based on their prior achievements and actions.</p>
                        <h4>Question Types:</h4>
                        <p>Competency.</p>
                        <h4>Interview Length:</h4>
                        <p>20 minutes.</p>
                        <h4>User Input Required:</h4>
                        <p>Any user can practice competency based questions without having uploaded a resume or job listing.</p>
                        <button id="start-interview-button" class="start-interview-button">Start Interview</button>
                    `;
                    break;
                case 'ethical_round':
                    interviewDetails = `
                        <h3>Ethical Round Interview</h3>
                        <h4>Description:</h4>
                        <p>This interview is designed to put you through the most commonly asked ethical questions that come up in interviews. Ethical job interview questions aim to evaluate a candidate's integrity, moral principles, and decision-making processes by exploring how they have handled or would handle ethical dilemmas in the workplace. These questions help determine whether the candidate's values align with the organization's ethical standards and culture.</p>
                        <h4>Question Types:</h4>
                        <p>Ethical.</p>
                        <h4>Interview Length:</h4>
                        <p>20 minutes.</p>
                        <h4>User Input Required:</h4>
                        <p>Any user can practice ethical questions without having uploaded a resume or job listing.</p>
                        <button id="start-interview-button" class="start-interview-button">Start Interview</button>
                    `;
                    break;
                default:
                    interviewDetails = '';
                    break;
            }

            interviewDetailsContent.innerHTML = interviewDetails;

            if (interviewDetailsContent.querySelector('#start-interview-button')) {
                const startInterviewButton = interviewDetailsContent.querySelector('#start-interview-button');
                startInterviewButton.addEventListener('click', function () {
                    let interviewRound = selectedValue;
                    if (interviewRound === 'first_round') {
                        fetchJobDescription(userId).then(jobDescription => {
                            fetchResumeData(userId).then(resumeData => {
                                if (resumeData && jobDescription) {
                                    const jobTitle = jobDescription.job_title;
                                    const companyName = jobDescription.company_name;
                                    const companyIndustry = jobDescription.company_industry;

                                    window.location.href = `http://localhost:5013/${interviewRound}/?username=${username}&user_id=${userId}&interview_round=${interviewRound}&job_title=${jobTitle}&company_name=${companyName}&company_industry=${companyIndustry}&session_id=`;
                                } else if (resumeData && !jobDescription) {
                                    statusMessage.innerHTML = "It looks like you’re missing a job description. Please upload a job description to enter this interview.";
                                    statusMessage.style.display = 'block';
                                } else if (!resumeData && jobDescription) {
                                    statusMessage.innerHTML = "It looks like you’re missing resume data. Please upload your resume to enter this interview.";
                                    statusMessage.style.display = 'block';
                                } else {
                                    statusMessage.innerHTML = "It looks like you’re missing resume and job description data. Please upload this data to enter this interview.";
                                    statusMessage.style.display = 'block';
                                }
                            });
                        });
                    } else {
                        window.location.href = `http://localhost:5013/${interviewRound}/?username=${username}&user_id=${userId}&interview_round=${interviewRound}&session_id=`;
                    }
                });
            }
        }
    });

    // Secondary dropdown change event
    jobRoleDropdown.addEventListener('change', function () {
        const selectedJobTitle = jobRoleDropdown.value;
        if (selectedJobTitle === 'add_new_role') {
            newJobTitleContainer.style.display = 'block';
        } else {
            newJobTitleContainer.style.display = 'none';
            if (selectedJobTitle) {
                loadJobRoleInterviewDetails(selectedJobTitle);
            }
        }
    });

    // Submit new job title event
    submitNewJobTitleButton.addEventListener('click', function () {
        const newJobTitle = newJobTitleInput.value.trim();
        if (newJobTitle) {
            checkAndAddNewJobTitle(newJobTitle.toLowerCase());
        }
    });

    // Check and add new job title
    function checkAndAddNewJobTitle(jobTitle) {
        fetch('/api/check_job_title_exists', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ job_title: jobTitle })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.exists) {
                statusMessage.innerHTML = `${jobTitle} already exists within my database. Please search for and select it from the “Select Job Role” dropdown.`;
                statusMessage.style.display = 'block';
            } else {
                statusMessage.innerHTML = `I’m processing your request to add ${jobTitle} to my repository. Please hold tight and I will let you know when the job is complete.`;
                statusMessage.style.display = 'block';
                addNewJobTitle(jobTitle);
            }
        })
        .catch(error => {
            console.error('Error checking job title:', error);
            statusMessage.innerHTML = 'An error occurred while checking the job title. Please try again.';
            statusMessage.style.display = 'block';
        });
    }
    

    // Add new job title
    function addNewJobTitle(jobTitle) {
        fetch('/api/add_new_job_title', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ job_title: jobTitle })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                statusMessage.innerHTML = `${jobTitle} successfully added to my repository. Please feel free to select and conduct this interview round.`;
                statusMessage.style.display = 'block';
                updateJobRoleDropdown();
            } else {
                throw new Error(data.error || 'An error occurred while adding the job title.');
            }
        })
        .catch(error => {
            console.error('Error adding job title:', error);
            statusMessage.innerHTML = `An error occurred while adding the job title: ${error.message}`;
            statusMessage.style.display = 'block';
        });
    }
    
    // Update job role dropdown
    function updateJobRoleDropdown() {
        fetchJobTitles().then(jobTitles => {
            jobTitles.sort((a, b) => a.localeCompare(b)); // Sort job titles alphabetically
            jobRoleDropdown.innerHTML = '<option value="">Click here</option>';
            jobTitles.forEach(jobTitle => {
                jobRoleDropdown.innerHTML += `<option value="${jobTitle}">${jobTitle}</option>`;
            });
            jobRoleDropdown.innerHTML += '<option value="add_new_role">Add New Role</option>';
        });
    }

    // Display status message
    function displayStatusMessage(message, type) {
        statusMessage.innerHTML = message;
        statusMessage.style.display = 'block';
        statusMessage.style.backgroundColor = type === 'error' ? 'red' : type === 'success' ? 'green' : 'burntorange';
    }

    function loadJobRoleInterviewDetails(jobTitle) {
        const details = `
            <h3>Job Role Specific Interview: ${jobTitle}</h3>
            <h4>Description:</h4>
            <p>This interview is designed to put you through the most commonly asked questions for the ${jobTitle} job role. This is a great exercise for candidates new to a specific job role or transitioning careers. For more specific questions about your experience within a job role or required experience for a job role at a specific job listing please select First Round, or similar Interview Round.</p>
            <h4>Question Types:</h4>
            <p>${jobTitle} Job Role Specific.</p>
            <h4>Interview Length:</h4>
            <p>30 minutes.</p>
            <h4>User Input Required:</h4>
            <p>Any user can practice job role specific questions without having uploaded a resume or job listing.</p>
            <button id="start-interview-button" class="start-interview-button">Start Interview</button>
        `;

        interviewDetailsContent.innerHTML = details;
        const startInterviewButton = document.getElementById('start-interview-button');
        if (startInterviewButton) {
            startInterviewButton.addEventListener('click', function () {
                window.location.href = `http://localhost:5013/job_role_round/?username=${username}&user_id=${userId}&interview_round=job_role_round&session_id=&job_title=${jobTitle}`;
            });
        }
    }
});
