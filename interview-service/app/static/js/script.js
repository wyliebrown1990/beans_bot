$(document).ready(function() {
    const urlParams = new URLSearchParams(window.location.search);
    const username = urlParams.get('username');
    const userId = urlParams.get('user_id');
    const interviewRound = urlParams.get('interview_round');
    let sessionId = urlParams.get('session_id');
    let lastQuestionServed = false;

    // Ensure the interview timer starts at 30 minutes
    $('#interview-timer').text('30:00');
    let interviewTimer = 30 * 60; // 30 minutes in seconds
    let answerTimer = 90; // 1 minute 30 seconds

    // Function to format time in minutes and seconds
    function formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${minutes}:${secs < 10 ? '0' : ''}${secs}`;
    }

    // Update timers every second
    setInterval(() => {
        if (interviewTimer > 0) {
            interviewTimer--;
            $('#interview-timer').text(formatTime(interviewTimer));
        } else if (interviewTimer === 0 && !lastQuestionServed) {
            endInterview();
            interviewTimer = -1;  // Prevent further actions once interview is ended
        }
        if (answerTimer > 0) {
            answerTimer--;
            $('#answer-timer').text(formatTime(answerTimer));
        }
    }, 1000);

    // Set hidden input values
    $('input[name="username"]').val(username);
    $('input[name="user_id"]').val(userId);
    $('input[name="interview_round"]').val(interviewRound);
    $('input[name="session_id"]').val(sessionId);

    // Update the header with the username
    $('h1').text(`First Round Interview for ${username}`);

    // Add event listener for Home button
    $('#home-button').on('click', function() {
        window.location.href = `http://localhost:5011/?username=${username}&user_id=${userId}`;
    });

    // Add event listener for Skip Question button
    $('#skip-question').on('click', function() {
        submitAnswer('skipped');
    });

    // Add event listener for Wrap-up Interview button
    $('#wrap-up-interview').on('click', function() {
        endInterview();
    });

    $('#response-form').on('submit', function(event) {
        event.preventDefault();
        const answer = $('#answer_1').val();
        submitAnswer(answer);
    });

    function submitAnswer(answer) {
        const formData = {
            session_id: $('input[name="session_id"]').val(),
            user_id: $('input[name="user_id"]').val(),
            question: $('input[name="question"]').val(),
            answer_1: answer,
            interview_round: $('input[name="interview_round"]').val(),
            question_id: $('input[name="question_id"]').val(),
            question_num: $('input[name="question_num"]').val(),
            current_time: $('#interview-timer').text() // Send the current interview timer time
        };

        const url = answer === 'skipped' ? Flask.url_for('first_round.skip_question') : Flask.url_for('first_round.submit_answer');

        console.log(`Submitting form to ${url} with data:`, formData);

        $.ajax({
            type: 'POST',
            url: url,
            data: formData,
            success: function(response) {
                console.log('Response received:', response);

                appendAnswer(answer);

                if (response.question) {
                    appendQuestion(response.question);

                    $('input[name="question"]').val(response.question);
                    $('input[name="question_id"]').val(response.question_id || '');
                    $('input[name="question_num"]').val(response.question_num);
                    $('#answer_1').val('');

                    sessionStorage.setItem('question_time', $('#interview-timer').text());
                } else if (response.summary) {
                    displaySummaryMessage(response.summary);
                } else {
                    alert('Interview complete');
                }
            },
            error: function(xhr, status, error) {
                console.error('Error occurred:', error);
            }
        });
    }

    function appendQuestion(question) {
        const questionHtml = `
            <div class="chat-block">
                <div class="chat-image">
                    <img src="https://interview-bot-public-images.s3.amazonaws.com/beans_bot_light_bg_500.png" alt="Beans Bot" class="chat-image" id="bot-image">
                </div>
                <div class="speech-bubble">
                    <p>Beans-bot: ${question}</p>
                </div>
            </div>
        `;
        $('#chat').append(questionHtml);
    }

    function appendAnswer(answer) {
        const answerHtml = `
            <div class="chat-block">
                <div class="chat-image">
                    <img src="https://interview-bot-public-images.s3.amazonaws.com/user_logo_500.PNG" alt="User" class="chat-image">
                </div>
                <div class="speech-bubble user-speech-bubble">
                    <p>${answer}</p>
                </div>
            </div>
        `;
        $('#chat').append(answerHtml);
    }

    function updateUrlParameter(url, param, paramVal) {
        let newAdditionalURL = "";
        let tempArray = url.split("?");
        const baseURL = tempArray[0];
        let additionalURL = tempArray[1];
        let temp = "";
        if (additionalURL) {
            tempArray = additionalURL.split("&");
            for (let i = 0; i < tempArray.length; i++) {
                if (tempArray[i].split('=')[0] != param) {
                    newAdditionalURL += temp + tempArray[i];
                    temp = "&";
                }
            }
        }
        const rows_txt = temp + "" + param + "=" + paramVal;
        return baseURL + "?" + newAdditionalURL + rows_txt;
    }

    function endInterview() {
        const formData = {
            session_id: $('input[name="session_id"]').val(),
            user_id: $('input[name="user_id"]').val(),
            question: $('input[name="question"]').val(),
            answer_1: 'skipped',
            interview_round: $('input[name="interview_round"]').val(),
            question_id: $('input[name="question_id"]').val(),
            question_num: $('input[name="question_num"]').val(),
            current_time: $('#interview-timer').text() // Send the current interview timer time
        };

        $.ajax({
            type: 'POST',
            url: Flask.url_for('first_round.end_interview'),
            data: formData,
            success: function(response) {
                console.log('Response received:', response);

                if (response.question) {
                    appendQuestion(response.question);
                    $('input[name="question"]').val(response.question);
                    $('input[name="question_id"]').val(response.question_id || '');
                    $('input[name="question_num"]').val('last');
                    $('#answer_1').val('');
                    lastQuestionServed = true;
                } else if (response.summary) {
                    displaySummaryMessage(response.summary);
                }
            },
            error: function(xhr, status, error) {
                console.error('Error occurred:', error);
            }
        });
    }

    function displaySummaryMessage(summaryMessage) {
        const summaryHtml = `
            <div class="chat-block">
                <div class="chat-image">
                    <img src="https://interview-bot-public-images.s3.amazonaws.com/beans_bot_light_bg_500.png" alt="Beans Bot" class="chat-image" id="bot-image">
                </div>
                <div class="speech-bubble">
                    <p>Beans-bot: ${summaryMessage}</p>
                </div>
            </div>
        `;
        $('#chat').append(summaryHtml);
        $('#response-form').remove();  // Remove the form to prevent further submissions
    }
});
