document.addEventListener("DOMContentLoaded", function() {
    const infoButton = document.getElementById("info-button");
    const infoPopup = document.getElementById("info-popup");
    const closeButton = document.getElementById("close-button");

    infoButton.addEventListener("click", function() {
        infoPopup.style.display = "block";
    });

    closeButton.addEventListener("click", function() {
        infoPopup.style.display = "none";
    });

    const message = `{{ message|safe }}`;
    const text = document.createElement("textarea");
    text.innerHTML = message;
    const decodedMessage = text.value;

    let i = 0;
    function typeWriter() {
        if (i < decodedMessage.length) {
            document.getElementById("message-text").innerHTML += decodedMessage.charAt(i);
            i++;
            setTimeout(typeWriter, 20);
        } else {
            checkMessageAndAddButton(decodedMessage);
        }
    }
    if (message) {
        typeWriter();
    }

    fetchProcessedFiles();
    fetchJobDescriptionData();

    document.getElementById('file-upload-form').addEventListener('submit', function(event) {
        event.preventDefault();
        showStatusMessage('Upload being processed...');
        uploadFiles(new FormData(this));
    });

    document.getElementById('raw-text-submission-form').addEventListener('submit', function(event) {
        event.preventDefault();
        showStatusMessage('We\'re processing your submission...');
        submitRawText(new FormData(this));
    });
});

function showStatusMessage(message) {
    const statusMessageDiv = document.getElementById('status-message');
    statusMessageDiv.innerText = message;
    statusMessageDiv.style.display = 'block';
}

function fetchProcessedFiles() {
    const userId = "{{ user_id }}";
    console.log("Fetching files for user ID:", userId);
    fetch(`/api/job-description-analysis/${userId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch');
            }
            return response.json();
        })
        .then(data => {
            console.log("Data received:", data);
            const filesListDiv = document.getElementById('files-list');
            filesListDiv.innerHTML = '';
            if (data.length === 0) {
                const noFilesMessage = document.createElement('p');
                noFilesMessage.textContent = "You don't currently have any job listings. Please upload data below.";
                filesListDiv.appendChild(noFilesMessage);
            } else {
                data.forEach(file => {
                    const label = document.createElement('label');
                    const radio = document.createElement('input');
                    radio.type = 'radio';
                    radio.name = 'listing';
                    radio.value = `${file.job_title}_${file.company_name}`;
                    label.appendChild(radio);
                    label.appendChild(document.createTextNode(`${file.job_title} at ${file.company_name}`));
                    filesListDiv.appendChild(label);
                    filesListDiv.appendChild(document.createElement('br'));
                });
            }
        })
        .catch(error => {
            console.error('Error fetching files:', error);
        });
}

function fetchJobDescriptionData() {
    const userId = "{{ user_id }}";
    console.log("Fetching job description data for user ID:", userId);
    fetch(`/api/job-description/${userId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch job description data');
            }
            return response.json();
        })
        .then(data => {
            console.log("Job description data received:", data);
            document.getElementById('job_title').value = data.job_title || '';
            document.getElementById('company_name').value = data.company_name || '';
            document.getElementById('industry').value = data.industry || '';
        })
        .catch(error => {
            console.error('Error fetching job description data:', error);
        });
}

function uploadFiles(formData) {
    fetch('/file_upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
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
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
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

function waitForProcessingCompletion(endpoint) {
    const userId = "{{ user_id }}";
    const intervalId = setInterval(() => {
        fetch(`/api/status/${userId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === "Processing complete" || data.status.startsWith("Processing error")) {
                    showStatusMessage(data.status);
                    clearInterval(intervalId);
                } else {
                    showStatusMessage(data.status);
                }
            })
            .catch(error => {
                console.error('Error checking status:', error);
                showStatusMessage('Error checking status: ' + error.message);
                clearInterval(intervalId);
            });
    }, 5000);
}

function deleteSelectedFiles(event) {
    event.preventDefault();
    const selectedFiles = Array.from(document.querySelectorAll('input[name="selected_files"]:checked'))
        .map(checkbox => checkbox.value);
    if (selectedFiles.length > 0) {
        fetch(`/api/job-description-analysis/delete`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ids: selectedFiles })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Selected files deleted successfully');
                fetchProcessedFiles();
            } else {
                alert('Error deleting files: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error deleting files:', error);
        });
    } else {
        alert('No files selected');
    }
}

function deleteAllFiles(event) {
    event.preventDefault();
    const userId = "{{ user_id }}";
    fetch(`/api/job-description-analysis/delete-all/${userId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('All files deleted successfully');
            fetchProcessedFiles();
        } else {
            alert('Error deleting files: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error deleting files:', error);
    });
}

function checkMessageAndAddButton(message) {
    if (message.includes("Looks like I have some data you uploaded in a previous session.")) {
        const buttonContainer = document.createElement('div');
        buttonContainer.id = 'buttonContainer';

        const startInterviewButton = document.createElement('button');
        startInterviewButton.innerText = 'Start Interview!';
        startInterviewButton.classList.add('actionButton');
        startInterviewButton.onclick = function() {
            const jobTitle = "{{ job_title }}".toLowerCase();
            const companyName = "{{ company_name }}".toLowerCase();
            const industry = "{{ industry }}".toLowerCase();
            const username = "{{ username }}".toLowerCase();
            const userId = "{{ user_id }}";
            window.location.href = `http://localhost:5013/start_interview?job_title=${jobTitle}&company_name=${companyName}&industry=${industry}&username=${username}&user_id=${userId}`;
        };

        buttonContainer.appendChild(startInterviewButton);
        document.getElementById('file-list-container').insertBefore(buttonContainer, document.querySelector('h2'));
    }
}

function startInterview() {
    const jobTitle = "{{ job_title }}".toLowerCase();
    const companyName = "{{ company_name }}".toLowerCase();
    const industry = "{{ industry }}".toLowerCase();
    const username = "{{ username }}".toLowerCase();
    const userId = "{{ user_id }}";
    window.location.href = `http://localhost:5013/start_interview?job_title=${jobTitle}&company_name=${companyName}&industry=${industry}&username=${username}&user_id=${userId}`;
}
