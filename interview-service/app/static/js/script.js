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
let interviewTimeLeft = 1800; // 30 minutes in seconds
let currentAudio = null;
let playButton = null;
let store_questions_asked = [];
let store_answers = [];

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
        if (interviewTimeLeft <= 300) { // 5 minutes remaining
            clearInterval(interviewTimerInterval);
            getLastQuestion();
        } else {
            timerElement.innerText = formatTime(interviewTimeLeft);
        }
    }, 1000);
}

document.getElementById('wrap-up-interview').addEventListener('click', function() {
    getLastQuestion();
});

function getLastQuestion() {
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('user_id');
    const sessionId = urlParams.get('session_id');

    $.ajax({
        type: 'GET',
        url: '/first_round/get_last_question',
        data: {
            user_id: userId,
            session_id: sessionId
        },
        success: function(response) {
            // Append the last question to the responses div
            $('#responses').append(`
                <div class="chat-block">
                    <img src="https://interview-bot-public-images.s3.amazonaws.com/beans_bot_light_bg_500.png" alt="Beans Bot" class="chat-image">
                    <div class="speech-bubble">
                        <p>Beans-bot: ${response.next_question_response}</p>
                        ${response.next_question_audio ? `<button class="play-button" onclick="toggleAudio('${response.next_question_audio}', this)">Play Next Question</button>` : ''}
                    </div>
                </div>
            `);

            // Store the new question in store_questions_asked
            store_questions_asked.push(response.next_question_response);
            console.log("Stored questions:", store_questions_asked);

            // Clear the answer input field
            $('#answer_1').val('');
            startAnswerTimer();  // Reset the timer when a new question is received

            // Set the session flag for last question
            sessionStorage.setItem('last_question', 'true');
        },
        error: function(error) {
            console.log('Error:', error);
            // Show error message
            $('#status-message').text("An error occurred. Please try again.").fadeIn().delay(3000).fadeOut();
        }
    });
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds < 10 ? '0' : ''}${remainingSeconds}`;
}

document.addEventListener('DOMContentLoaded', (event) => {
    startAnswerTimer();
    startInterviewTimer();

    // Add the initial question to store_questions_asked
    const initialQuestion = document.querySelector('.speech-bubble p').textContent;
    store_questions_asked.push(initialQuestion);
    console.log("Initial question stored:", initialQuestion);

    // Include session_id in URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');

    if (sessionId) {
        // Set hidden input value for session_id
        const sessionInput = document.createElement('input');
        sessionInput.type = 'hidden';
        sessionInput.name = 'session_id';
        sessionInput.value = sessionId;
        document.getElementById('response-form').appendChild(sessionInput);
    }
});

document.getElementById('generate_audio').addEventListener('click', function() {
    const voiceSelection = document.getElementById('voice-selection');
    if (voiceSelection.style.display === 'none' || voiceSelection.style.display === '') {
        voiceSelection.style.display = 'block';
        this.innerHTML = '🤫';
    } else {
        voiceSelection.style.display = 'none';
        this.innerHTML = '💬';
    }
});

document.getElementById('response-form').addEventListener('submit', function(event) {
    const selectedVoice = document.getElementById('voice').value;
    const generateAudioInput = document.createElement('input');
    generateAudioInput.type = 'hidden';
    generateAudioInput.name = 'generate_audio';
    generateAudioInput.value = 'true';
    document.getElementById('response-form').appendChild(generateAudioInput);

    const voiceIdInput = document.createElement('input');
    voiceIdInput.type = 'hidden';
    voiceIdInput.name = 'voice_id';
    voiceIdInput.value = selectedVoice;
    document.getElementById('response-form').appendChild(voiceIdInput);

    console.log("Selected voice:", selectedVoice); // Verify the selected value
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
        formData.append('audio', audioBlob, 'recording.wav');
        console.log("Sending audio blob to server...");
        $.ajax({
            type: 'POST',
            url: '/first_round/transcribe_audio',
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

function scrollToBottom() {
    const chatContainer = document.getElementById('content-wrap');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function addHighlightEffect(element) {
    element.classList.add('highlight');
    setTimeout(() => {
        element.classList.remove('highlight');
    }, 2000);
}


$('#response-form').on('submit', function(event) {
    event.preventDefault();
    const form = $(this);
    const userResponse = $('#answer_1').val();
    const username = $('#responses').data('username'); 
    const sessionId = $('input[name="session_id"]').val(); 

    console.log("User response:", userResponse);
    $('#status-message').text("Processing your response...").fadeIn();

    $.ajax({
        type: 'POST',
        url: '/first_round/submit_answer',
        data: form.serialize() + `&session_id=${sessionId}`,
        success: function(response) {
            console.log("Server response:", response);
            $('#status-message').fadeOut();

            let userChatBlock, botChatBlock;

            if (response.final_message) {
                botChatBlock = $(`
                    <div class="chat-block">
                        <img src="https://interview-bot-public-images.s3.amazonaws.com/beans_bot_light_bg_500.png" alt="Beans Bot" class="chat-image">
                        <div class="speech-bubble">
                            <p>Beans-bot: ${response.final_message}</p>
                        </div>
                    </div>
                `).appendTo('#responses');
            } else if (response.next_question_response) {
                userChatBlock = $(`
                    <div class="chat-block">
                        <img src="https://interview-bot-public-images.s3.amazonaws.com/user_logo_500.PNG" alt="User" class="chat-image">
                        <div class="speech-bubble">
                            <p>You: ${userResponse}</p>
                        </div>
                    </div>
                `).appendTo('#responses');

                botChatBlock = $(`
                    <div class="chat-block">
                        <img src="https://interview-bot-public-images.s3.amazonaws.com/beans_bot_light_bg_500.png" alt="Beans Bot" class="chat-image">
                        <div class="speech-bubble">
                            <p>Beans-bot: ${response.next_question_response}</p>
                            ${response.next_question_audio ? `<button class="play-button" onclick="toggleAudio('${response.next_question_audio}', this)">Play Next Question</button>` : ''}
                        </div>
                    </div>
                `).appendTo('#responses');

                store_questions_asked.push(response.next_question_response);
                console.log("Stored questions:", store_questions_asked);

                $('#answer_1').val('');
                startAnswerTimer();  
            } else {
                console.error("No next_question_response or final_message found in the server response.");
                $('#status-message').text("An error occurred. Please try again.").fadeIn().delay(3000).fadeOut();
            }

            // Apply highlight effect to new chat blocks
            if (userChatBlock) addHighlightEffect(userChatBlock[0]);
            if (botChatBlock) addHighlightEffect(botChatBlock[0]);

            // Scroll to bottom after new message
            scrollToBottom();
        },
        error: function(error) {
            console.log('Error:', error);
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
    const urlParams = new URLSearchParams(window.location.search);
    const session_id = urlParams.get('session_id');

    if (!session_id) {
        console.error('session_id is missing from the URL');
        return;
    }

    $.ajax({
        type: 'GET',
        url: '/first_round/download_transcript',
        data: { session_id: session_id },
        success: function(response) {
            const blob = new Blob([response], { type: 'text/csv;charset=utf-8;' });
            const downloadUrl = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = downloadUrl;
            a.download = `interview_transcript_${session_id}.csv`;
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
    const session_id = generateSessionId(); // Function to generate session ID

    // Clear Flask session data on the server
    $.ajax({
        type: 'POST',
        url: '/first_round/clear_session',
        success: function() {
            // Redirect to the same URL to start a new session with session_id
            window.location.href = `${window.location.pathname}?job_title=${job_title}&company_name=${company_name}&industry=${industry}&username=${username}&user_id=${user_id}&session_id=${session_id}`;
        },
        error: function(error) {
            console.error('Error clearing session:', error);
        }
    });
}


function generateSessionId() {
    return Math.floor(Math.random() * 1000000000); // Generate a simple session ID
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
        url: '/first_round/wrap_up_early',
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

            if (response.final_message) {
                $('#responses').append(`
                    <div class="chat-block">
                        <img src="https://interview-bot-public-images.s3.amazonaws.com/beans_bot_light_bg_500.png" alt="Beans Bot" class="chat-image">
                        <div class="speech-bubble">
                            <p>Beans-bot: ${response.final_message}</p>
                        </div>
                    </div>
                `);
            } else if (response.next_question_response) {
                $('#responses').append(`
                    <div class="chat-block">
                        <img src="https://interview-bot-public-images.s3.amazonaws.com/beans_bot_light_bg_500.png" alt="Beans Bot" class="chat-image">
                        <div class="speech-bubble">
                            <p>Beans-bot: ${response.next_question_response}</p>
                            ${response.next_question_audio ? `<button class="play-button" onclick="toggleAudio('${response.next_question_audio}', this)">Play Next Question</button>` : ''}
                        </div>
                    </div>
                `);
            } else {
                console.error("No final_message or next_question_response found in the server response.");
                $('#status-message').text("An error occurred. Please try again.").fadeIn().delay(3000).fadeOut();
            }
        },
        error: function(error) {
            console.error('Error wrapping up interview:', error);
            $('#status-message').text("An error occurred. Please try again.").fadeIn().delay(3000).fadeOut();
        }
    });
});
