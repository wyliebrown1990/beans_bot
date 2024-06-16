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
 let answerTimerInterval;
 let answerTimeLeft = 90;
 let interviewTimerInterval;
 let interviewTimeLeft = 2700; // 45 minutes in seconds
 let currentAudio = null;
 let playButton = null;
 function startAnswerTimer() {
    clearInterval(answerTimerInterval);
    answerTimeLeft = 90;
    const timerElement = document.getElementById('answer-timer');
    timerElement.classList.remove('pulse');
    timerElement.innerText = answerTimeLeft;
    answerTimerInterval = setInterval(() => {
        answerTimeLeft--;
        if (answerTimeLeft <= 0) {
            clearInterval(answerTimerInterval);
            timerElement.innerText = "Wrap up answer";
            timerElement.classList.add('pulse');
        } else {
            timerElement.innerText = answerTimeLeft;
        }
    }, 1000);
 }
 function startInterviewTimer() {
    clearInterval(interviewTimerInterval);
    const timerElement = document.getElementById('interview-timer');
    timerElement.classList.remove('pulse');
    timerElement.innerText = formatTime(interviewTimeLeft);
    interviewTimerInterval = setInterval(() => {
        interviewTimeLeft--;
        if (interviewTimeLeft <= 0) {
            clearInterval(interviewTimerInterval);
            timerElement.innerText = "Interview Ending";
            timerElement.classList.add('pulse');
        } else {
            timerElement.innerText = formatTime(interviewTimeLeft);
        }
    }, 1000);
 }
 function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
 }
 document.addEventListener('DOMContentLoaded', (event) => {
    startAnswerTimer();
    startInterviewTimer();
 });
 document.getElementById('generate_audio').addEventListener('click', function() {
    const voiceSelection = document.getElementById('voice-selection');
    if (voiceSelection.style.display === 'none' || voiceSelection.style.display === '') {
        voiceSelection.style.display = 'block';
    } else {
        voiceSelection.style.display = 'none';
    }
    const generateAudioInput = document.createElement('input');
    generateAudioInput.type = 'hidden';
    generateAudioInput.name = 'generate_audio';
    generateAudioInput.value = 'true';
    document.getElementById('response-form').appendChild(generateAudioInput);

    const selectedVoice = document.getElementById('voice').value;
    if (selectedVoice === 'none') {
        generateAudioInput.value = 'false';
    }
    console.log("Selected voice:", selectedVoice); // Verify the selected value
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
    $('#record-answer').html("⏹");
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
    $('#record-answer').html("🎙");
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
            url: transcribeAudioUrl,
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
    const username = $('#responses').data('username'); // Get the username from data attribute
    console.log("User response:", userResponse);
    // Show status message
    $('#status-message').text("Processing your response...").fadeIn();
    $.ajax({
        type: 'POST',
        url: startInterviewUrl,
        data: form.serialize(),
        success: function(response) {
            console.log("Server response:", response);
            // Hide status message
            $('#status-message').fadeOut();
            $('#responses').append(`
                <div class="chat-block">
                    <img src="https://interview-bot-public-images.s3.amazonaws.com/user_logo_500.PNG" alt="User Image" class="chat-image">
                    <div class="speech-bubble">
                        <p>${username}: ${userResponse}</p>
                    </div>
                </div>
                <div class="chat-block">
                    <img src="https://interview-bot-public-images.s3.amazonaws.com/beans_bot_light_bg_500.png" alt="Beans Bot" class="chat-image">
                    <div class="speech-bubble">
                        <p>Beans-bot Feedback: ${response.feedback_response}</p>
                        <p>Beans-bot Score: ${response.score_response}</p>
                        <p>Beans-bot: ${response.next_question_response}</p>
                        ${response.next_question_audio ? `<button class="play-button" onclick="toggleAudio('${response.next_question_audio}', this)">Play Next Question</button>` : ''}
                    </div>
                </div>
            `);
            $('#answer_1').val('');
            startAnswerTimer();  // Reset the timer when a new question is received
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
        url: downloadTranscriptUrl,
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
        url: clearSessionUrl,
        success: function() {
            // Redirect to the same URL to start a new session
            window.location.href = `${startInterviewUrl}?job_title=${job_title}&company_name=${company_name}&industry=${industry}&username=${username}&user_id=${user_id}`;
        },
        error: function(error) {
            console.error('Error clearing session:', error);
        }
    });
 }
 document.getElementById('nav-toggle').addEventListener('click', function() {
    const navLinks = document.getElementById('nav-links');
    navLinks.classList.toggle('hidden');
 });
 
 document.getElementById('wrap-up-interview').addEventListener('click', function() {
    const form = document.getElementById('response-form');
    const sessionId = document.querySelector('input[name="session_id"]').value;
    const jobTitle = document.querySelector('input[name="job_title"]').value;
    const companyName = document.querySelector('input[name="company_name"]').value;
    const industry = document.querySelector('input[name="industry"]').value;
    const username = document.querySelector('input[name="username"]').value;
    const userId = document.querySelector('input[name="user_id"]').value;
    const userResponse = document.getElementById('answer_1').value;
    const generateAudio = document.getElementById('generate_audio').checked;
    const voiceId = document.querySelector('select[name="voice"]').value;

    // Show the processing message
    $('#status-message').text("Processing your response...").fadeIn();

    $.ajax({
        type: 'POST',
        url: wrapUpInterviewUrl,
        data: {
            session_id: sessionId,
            job_title: jobTitle,
            company_name: companyName,
            industry: industry,
            username: username,
            user_id: userId,
            answer_1: userResponse,  // Include the user's last answer
            generate_audio: generateAudio,
            voice: voiceId
        },
        success: function(response) {
            console.log("Server response:", response);
            $('#status-message').fadeOut();
            $('#responses').append(`
                <div class="chat-block">
                    <img src="https://interview-bot-public-images.s3.amazonaws.com/beans_bot_light_bg_500.png" alt="Beans Bot" class="chat-image">
                    <div class="speech-bubble">
                        <p>Beans-bot: ${response.next_question_response}</p>
                        ${response.next_question_audio ? `<button class="play-button" onclick="toggleAudio('${response.next_question_audio}', this)">Play Next Question</button>` : ''}
                    </div>
                </div>
            `);
        },
        error: function(error) {
            console.error('Error wrapping up interview:', error);
            $('#status-message').text("An error occurred. Please try again.").fadeIn().delay(3000).fadeOut();
        }
    });
});