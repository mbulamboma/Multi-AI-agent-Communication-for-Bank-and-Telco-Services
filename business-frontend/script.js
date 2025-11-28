// Configuration
const API_ENDPOINT = 'https://w3kd6p93v8.execute-api.us-east-1.amazonaws.com/'; // Update with your actual endpoint
let sessionId = generateSessionId();
let isLoading = false;

/**
 * Generate a unique session ID
 */
function generateSessionId() {
    return 'session-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now();
}

/**
 * Initialize the chat on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const sessionIdDisplay = document.getElementById('sessionId');
    
    // Set session ID display
    sessionIdDisplay.textContent = `Session: ${sessionId}`;
    
    // Send message on Enter key
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !isLoading) {
            sendMessage();
        }
    });
    
    // Send message on button click
    sendBtn.addEventListener('click', sendMessage);
    
    // Auto-focus input
    userInput.focus();
});

/**
 * Send user message to the agent
 */
async function sendMessage() {
    const userInput = document.getElementById('userInput');
    const message = userInput.value.trim();
    
    if (!message || isLoading) return;
    
    const phoneNumber = document.getElementById('phoneInput').value.trim() || null;
    
    // Add user message to chat
    addMessage(message, 'user');
    userInput.value = '';
    
    // Show loading indicator
    isLoading = true;
    addLoadingIndicator();
    
    try {
        // Call the Lambda API
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: message,
                sessionId: sessionId,
                phoneNumber: phoneNumber
            })
        });
        
        const data = await response.json();
        
        // Remove loading indicator
        removeLoadingIndicator();
        isLoading = false;
        
        if (response.ok && data.status === 'success') {
            // Add agent response
            addMessage(data.message, 'assistant');
            
            // Update session ID if provided
            if (data.sessionId) {
                sessionId = data.sessionId;
                document.getElementById('sessionId').textContent = `Session: ${sessionId}`;
            }
        } else {
            const errorMsg = data.message || 'Failed to get response from agent';
            addMessage(`❌ Error: ${errorMsg}`, 'assistant');
        }
    } catch (error) {
        console.error('Error:', error);
        removeLoadingIndicator();
        isLoading = false;
        addMessage(`❌ Network error: ${error.message}`, 'assistant');
    }
}

/**
 * Add a message to the chat
 * @param {string} message - The message text
 * @param {string} sender - 'user' or 'assistant'
 */
function addMessage(message, sender) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const p = document.createElement('p');
    // Use innerText to preserve line breaks and whitespace
    p.innerText = message;
    messageDiv.appendChild(p);
    
    chatMessages.appendChild(messageDiv);
    
    // Auto-scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Add loading indicator
 */
function addLoadingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant-message';
    loadingDiv.id = 'loading-indicator';
    loadingDiv.innerHTML = '<div class="loading"><span></span><span></span><span></span></div>';
    
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Remove loading indicator
 */
function removeLoadingIndicator() {
    const loadingDiv = document.getElementById('loading-indicator');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

/**
 * Quick action button click handler
 * @param {string} action - The action to perform
 */
function quickAction(action) {
    document.getElementById('userInput').value = action;
    document.getElementById('userInput').focus();
}

/**
 * Clear chat history
 */
function clearChat() {
    if (confirm('Are you sure you want to clear the chat history?')) {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = `
            <div class="message assistant-message">
                <p>Hello! 👋 I'm your Telco Assistant. How can I help you today?
                <small>I can help you activate subscriptions, check balance, transfer money, and get recommendations.</small>
                </p>
                
            </div>
        `;
        sessionId = generateSessionId();
        document.getElementById('sessionId').textContent = `Session: ${sessionId}`;
        document.getElementById('userInput').focus();
    }
}

/**
 * Handle API errors gracefully
 * @param {Error} error - The error object
 */
function handleError(error) {
    console.error('Error details:', error);
    return error.message || 'An unexpected error occurred';
}
