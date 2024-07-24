document.addEventListener('DOMContentLoaded', function () {
    const userId = new URLSearchParams(window.location.search).get('user_id');
    const username = new URLSearchParams(window.location.search).get('username');
    const jobListingDataContainer = document.getElementById('job-listing-data');
    const editJobListingButton = document.getElementById('edit-job-listing-button');
    const applyChangesButton = document.getElementById('apply-changes-button');
    const statusMessage = document.getElementById('status-message');

    const jobTitleSelect = document.getElementById('job_title');
    const companyNameSelect = document.getElementById('company_name');
    const industrySelect = document.getElementById('industry');

    const deleteJobListingForm = document.getElementById('delete-job-listing-form');
    const deleteJobListingButton = document.getElementById('delete-job-listing-button');
    const jobListingsMessage = document.getElementById('job-listings-message');
    const filesListContainer = document.getElementById('files-list');
    const fileUploadForm = document.getElementById('file-upload-form');
    const rawTextForm = document.getElementById('raw-text-submission-form');
    
     // Add navigation event listeners
     const homeLink = document.getElementById('home-link');
     const editResumeLink = document.getElementById('edit-resume-link');
     const editJobListingLink = document.getElementById('edit-job-listing-link');
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

    if (editResumeLink) {
        editResumeLink.addEventListener('click', function() {
            window.location.href = `edit_resume.html?user_id=${userId}&username=${username}`;
        });
    }

    if (editJobListingLink) {
        editJobListingLink.addEventListener('click', function() {
            window.location.href = `edit_job_listing.html?user_id=${userId}&username=${username}`;
        });
    }

    if (profileLink) {
        profileLink.addEventListener('click', function() {
            window.location.href = `profile.html?user_id=${userId}&username=${username}`;
        });
    }

    if (plansLink) {
        plansLink.addEventListener('click', function() {
            window.location.href = `plans.html?user_id=${userId}&username=${username}`;
        });
    }

    if (interviewHistoryLink) {
        interviewHistoryLink.addEventListener('click', function() {
            window.location.href = `interview_history.html?user_id=${userId}&username=${username}`;
        });
    }

    if (questionDataLink) {
        questionDataLink.addEventListener('click', function() {
            window.location.href = `question_data.html?user_id=${userId}&username=${username}`;
        });
    }

    if (jobResumeComparisonLink) {
        jobResumeComparisonLink.addEventListener('click', function() {
            window.location.href = `job_resume_comparison.html?user_id=${userId}&username=${username}`;
        });
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

    function fetchJobListings(userId, username) {
        fetch(`/api/job-description-analysis/${userId}`)
        .then(response => response.json())
        .then(data => {
            console.debug('Fetched job listings:', data);
            if (filesListContainer) {
                if (data.error) {
                    filesListContainer.innerHTML = 'Error fetching job listings: ' + data.error;
                    if (jobListingsMessage) {
                        jobListingsMessage.innerHTML = `Hey ${username}! It looks like you haven't uploaded a job description yet. To do so, please use the file or text uploading forms below. Once submitted, you may need to refresh the page to see your job listing in the Job Listings Manager.`;
                    }
                } else if (data.length === 0) {
                    filesListContainer.innerHTML = 'No job listings found. Below here you can upload a file or submit the text from the job listing you wish to interview for.';
                    if (deleteJobListingButton) {
                        deleteJobListingButton.style.display = 'none';
                    }
                    if (jobListingsMessage) {
                        jobListingsMessage.innerHTML = `Hey ${username}! It looks like you haven't uploaded a job description yet. To do so, please use the file or text uploading forms below. Once submitted, you may need to refresh the page to see your job listing in the Job Listings Manager.`;
                    }
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
                    if (deleteJobListingButton) {
                        deleteJobListingButton.style.display = 'block';
                    }
                    if (jobListingsMessage) {
                        jobListingsMessage.innerHTML = `Hey ${username}! It looks like you’ve already uploaded a job listing. I currently allow users to store 1 job listing at a time. Review the listing below and feel free to move forward with our interview or if you would like, delete the existing listing and upload a new one.`;
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error fetching job listings:', error);
            if (filesListContainer) {
                filesListContainer.innerHTML = 'Error fetching job listings: ' + error.message;
            }
            if (jobListingsMessage) {
                jobListingsMessage.innerHTML = `Hey ${username}! It looks like you haven't uploaded a job description yet. To do so, please use the file or text uploading forms below. Once submitted, you may need to refresh the page to see your job listing in the Job Listings Manager.`;
            }
            if (deleteJobListingButton) {
                deleteJobListingButton.style.display = 'none';
            }
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
