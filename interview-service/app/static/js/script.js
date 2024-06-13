function toggleSidebar() {
    var sidebar = document.getElementById('sidebar');
    if (sidebar.style.transform === 'translateX(0px)') {
        sidebar.style.transform = 'translateX(-250px)';
    } else {
        sidebar.style.transform = 'translateX(0px)';
    }
}

function showMenu(li) {
    li.querySelector('.menu').style.display = 'block';
}

function hideMenu(li) {
    li.querySelector('.menu').style.display = 'none';
}

document.querySelectorAll('.chat-list li').forEach(li => {
    li.addEventListener('click', function() {
        this.querySelector('.options').style.display = (this.querySelector('.options').style.display === 'none' || this.querySelector('.options').style.display === '') ? 'block' : 'none';
    });
});

let mediaRecorder;
let audioChunks = [];
let recording = false;

let videoRecorder;
let videoChunks = [];
let videoRecording = false;

let timerInterval;
let timeLeft = 90;

let currentAudio = null;
let playButton = null;

function startTimer() {
    clearInterval(timerInterval);
    timeLeft = 90;
    const timerElement = document.getElementById('timer');
    timerElement.classList.remove('pulse');
    timerElement.innerText = timeLeft;
    timerInterval = setInterval(() => {
        timeLeft--;
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            timerElement.innerText = "Wrap up answer";
            timerElement.classList.add('pulse');
        } else {
            timerElement.innerText = timeLeft;
        }
    }, 1000);
}

document.addEventListener('DOMContentLoaded', (event) => {
    startTimer();
});

document.getElementById('generate_audio').addEventListener('change', function() {
    if (this.checked) {
        document.getElementById('voice-selection').style.display = 'block';
    } else {
        document.getElementById('voice-selection').style.display = 'none';
    }
});

document.getElementById('record-answer').addEventListener('click', function() {
    if (!recording) {
        startRecording();
    } else {
        stopRecording();
    }
});

function startRecording() {
    console.log("Starting recording...");
    $('#status-message').text("Recording...").fadeIn();
    $('#record-answer').text("Stop Recording");
    recording = true;

    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.start();

            mediaRecorder.ondataavailable = function(event) {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstart = function() {
                console.log("Recording started.");
            };

            mediaRecorder.onerror = function(event) {
                console.error("Recording error:", event.error);
            };
        })
        .catch(error => {
            console.error('Error accessing microphone:', error);
        });
}

function stopRecording() {
    console.log("Stopping recording...");
    $('#status-message').text("Transcribing answer. This can take a while... Sit tight.").fadeIn();
    $('#record-answer').text("Record Answer");
    recording = false;

    mediaRecorder.stop();
    mediaRecorder.onstop = function() {
        console.log("Recording stopped.");
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const formData = new FormData();
        formData.append('audio', audioBlob);

        console.log("Sending audio blob to server...");
        $.ajax({
            type: 'POST',
            url: "{{ url_for('transcribe_audio') }}",
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                console.log("Server response:", response);
                $('#status-message').fadeOut();
                $('#answer_1').val(response.transcription);
            },
            error: function(error) {
                console.error('Error:', error);
                $('#status-message').text("An error occurred during transcription. Please try again.").fadeIn().delay(3000).fadeOut();
            }
        });

        audioChunks = [];
    };
}

document.getElementById('record-video').addEventListener('click', function() {
    if (!videoRecording) {
        startVideoRecording();
    } else {
        stopVideoRecording();
    }
});

function startVideoRecording() {
    console.log("Starting video recording...");
    $('#status-message').text("Video recording...").fadeIn();
    $('#record-video').text("Press to Stop Video Recording");
    videoRecording = true;

    navigator.mediaDevices.getUserMedia({ video: true, audio: true })
        .then(stream => {
            videoRecorder = new MediaRecorder(stream);
            videoRecorder.start();

            videoRecorder.ondataavailable = function(event) {
                videoChunks.push(event.data);
            };

            videoRecorder.onstart = function() {
                console.log("Video recording started.");
            };

            videoRecorder.onerror = function(event) {
                console.error("Video recording error:", event.error);
            };
        })
        .catch(error => {
            console.error('Error accessing camera:', error);
        });
}

function stopVideoRecording() {
    console.log("Stopping video recording...");
    $('#status-message').text("Processing video...").fadeIn();
    $('#record-video').text("Record Video of This Session");
    videoRecording = false;

    videoRecorder.stop();
    videoRecorder.onstop = function() {
        console.log("Video recording stopped.");
        const videoBlob = new Blob(videoChunks, { type: 'video/webm' });
        const videoUrl = URL.createObjectURL(videoBlob);
        const a = document.createElement("a");
        a.style.display = 'none';
        a.href = videoUrl;
        a.download = 'interview_recording.webm';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        $('#status-message').text("Download of recording complete").fadeIn().delay(3000).fadeOut();

        videoChunks = [];
    };
}

$('#response-form').on('submit', function(event) {
    event.preventDefault();
    const form = $(this);
    const userResponse = $('#answer_1').val();
    console.log("User response:", userResponse);

    // Show status message
    $('#status-message').text("Processing your response...").fadeIn();

    $.ajax({
        type: 'POST',
        url: "{{ url_for('start_interview') }}",
        data: form.serialize(),
        success: function(response) {
            console.log("Server response:", response);

            // Hide status message
            $('#status-message').fadeOut();

            $('#responses').append(`
                <div class="message user-message">
                    <p>{{ username }}: ${userResponse}</p>
                </div>
                <div class="message bot-message">
                    <img src="https://interview-bot-public-images.s3.amazonaws.com/beans_bot_light_bg_500.png" alt="Beans Bot" class="avatar">
                    <p>Beans-bot Feedback: ${response.feedback_response}</p>
                    <p>Beans-bot Score: ${response.score_response}</p>
                    <p>Beans-bot: ${response.next_question_response}</p>
                    ${response.next_question_audio ? `<button class="play-button" onclick="toggleAudio('${response.next_question_audio}', this)">Play Next Question</button>` : ''}
                </div>
            `);

            $('#answer_1').val('');
            startTimer();  // Reset the timer when a new question is received
        },
        error: function(error) {
            console.log('Error:', error);

            // Show error message
            $('#status-message').text("An error occurred. Please try again.").fadeIn().delay(3000).fadeOut();
        }
    });
});

function toggleAudio(audioPath, button) {
    if (currentAudio && !currentAudio.paused) {
        currentAudio.pause();
        button.style.backgroundColor = '';
        button.innerText = 'Play Next Question';
        return;
    }

    currentAudio = new Audio(audioPath);
    currentAudio.play();
    button.style.backgroundColor = 'burnt orange';
    button.innerText = 'Stop Audio';

    currentAudio.onended = () => {
        button.style.backgroundColor = '';
        button.innerText = 'Play Next Question';
    };
}

document.getElementById('download-transcript').addEventListener('click', function() {
    $.ajax({
        type: 'GET',
        url: "{{ url_for('download_transcript', session_id=session_id) }}",
        success: function(response) {
            const blob = new Blob([response], { type: 'text/csv;charset=utf-8;' });
            const downloadUrl = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = downloadUrl;
            a.download = "interview_transcript.csv";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        },
        error: function(error) {
            console.error('Error downloading transcript:', error);
        }
    });
});

function startNewInterviewSession() {
    const urlParams = new URLSearchParams(window.location.search);
    const job_title = urlParams.get('job_title');
    const company_name = urlParams.get('company_name');
    const industry = urlParams.get('industry');
    const username = urlParams.get('username');
    const user_id = urlParams.get('user_id');

    // Clear Flask session data on the server
    $.ajax({
        type: 'POST',
        url: "{{ url_for('clear_session') }}",
        success: function() {
            // Redirect to the same URL to start a new session
            window.location.href = `{{ url_for('start_interview') }}?job_title=${job_title}&company_name=${company_name}&industry=${industry}&username=${username}&user_id=${user_id}`;
        },
        error: function(error) {
            console.error('Error clearing session:', error);
        }
    });
}
