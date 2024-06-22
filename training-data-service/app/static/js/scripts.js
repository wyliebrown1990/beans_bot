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

    document.getElementById('file-upload-form').addEventListener('submit', function(event) {
        event.preventDefault();
        showStatusBlock(this);
        uploadFiles(new FormData(this));
    });

    document.getElementById('youtube-transcription-form').addEventListener('submit', function(event) {
        event.preventDefault();
        showStatusBlock(this);
        startYouTubeTranscription(new FormData(this));
    });

    document.getElementById('youtube-urls-transcription-form').addEventListener('submit', function(event) {
        event.preventDefault();
        showStatusBlock(this);
        startYouTubeURLsTranscription(new FormData(this));
    });

    document.getElementById('raw-text-submission-form').addEventListener('submit', function(event) {
        event.preventDefault();
        showStatusBlock(this);
        submitRawText(new FormData(this));
    });
});

function showStatusBlock(form) {
    const statusBlock = document.createElement('div');
    statusBlock.id = 'status-block';
    statusBlock.style.display = 'block';
    statusBlock.style.backgroundColor = '#CC5500';
    statusBlock.style.color = 'white';
    statusBlock.style.padding = '10px';
    statusBlock.style.textAlign = 'center';
    statusBlock.innerText = 'Upload being processed...';
    form.appendChild(statusBlock);
}

function fetchProcessedFiles() {
    const userId = "{{ user_id }}";
    console.log("Fetching files for user ID:", userId);
    fetch(`/api/training-data/${userId}`)
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
                noFilesMessage.textContent = "You don't currently have any training files. Please upload training data below.";
                filesListDiv.appendChild(noFilesMessage);
            } else {
                data.forEach(file => {
                    const label = document.createElement('label');
                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.name = 'selected_files';
                    checkbox.value = file.id;
                    label.appendChild(checkbox);
                    label.appendChild(document.createTextNode(file.processed_files));
                    filesListDiv.appendChild(label);
                    filesListDiv.appendChild(document.createElement('br'));
                });
            }
        })
        .catch(error => {
            console.error('Error fetching files:', error);
        });
}

function uploadFiles(formData) {
    fetch('/file_upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        setTimeout(() => {
            if (data.error) {
                alert(data.error);
            } else {
                fetchProcessedFiles();
                alert('Files uploaded successfully. You may need to refresh your page to see them in the browser.');
                location.reload();
            }
        }, 10000);
    })
    .catch(error => {
        console.error('Error uploading files:', error);
    });
}

function startYouTubeTranscription(formData) {
    fetch('/youtube_transcription', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        setTimeout(() => {
            if (data.error) {
                alert(data.error);
            } else {
                fetchProcessedFiles();
                alert('Transcription started successfully. Note that if you scraped long video files you will need to wait a few minutes and refresh your page routinely until you see them in your file management form.');
                location.reload();
            }
        }, 10000);
    })
    .catch(error => {
        console.error('Error starting transcription:', error);
    });
}

function startYouTubeURLsTranscription(formData) {
    fetch('/youtube_urls_transcription', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        setTimeout(() => {
            if (data.error) {
                alert(data.error);
            } else {
                fetchProcessedFiles();
                alert('YouTube URLs transcription started successfully. You may need to refresh your page to see them in the browser.');
                location.reload();
            }
        }, 10000);
    })
    .catch(error => {
        console.error('Error starting YouTube URLs transcription:', error);
    });
}

function submitRawText(formData) {
    fetch('/raw_text_submission', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        setTimeout(() => {
            if (data.error) {
                alert(data.error);
            } else {
                fetchProcessedFiles();
                alert('Raw text submission started successfully. You may need to refresh your page to see them in the browser.');
                location.reload();
            }
        }, 10000);
    })
    .catch(error => {
        console.error('Error submitting raw text:', error);
    });
}

function deleteSelectedFiles(event) {
    event.preventDefault();
    const selectedFiles = Array.from(document.querySelectorAll('input[name="selected_files"]:checked'))
        .map(checkbox => checkbox.value);
    if (selectedFiles.length > 0) {
        fetch(`/api/training-data/delete`, {
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
    fetch(`/api/training-data/delete-all/${userId}`, {
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
