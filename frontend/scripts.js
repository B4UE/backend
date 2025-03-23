// Constants
const API_BASE_URL = 'http://localhost:5002';

// DOM Elements
const objectivesList = document.getElementById('objectives-list');
const addObjectiveBtn = document.getElementById('add-objective-btn');
const objectiveModal = document.getElementById('objective-modal');
const closeModalBtn = document.querySelector('.close-btn');
const objectiveForm = document.getElementById('objective-form');
const chatMessages = document.getElementById('chat-messages');
const userMessageInput = document.getElementById('user-message');
const sendMessageBtn = document.getElementById('send-message-btn');
const foodImageInput = document.getElementById('food-image');
const scanFoodBtn = document.getElementById('scan-food-btn');
const scanResult = document.getElementById('scan-result');
const scanHistory = document.getElementById('scan-history');
const resetDataBtn = document.getElementById('reset-data-btn');

// Local Storage Keys
const OBJECTIVES_KEY = 'health_objectives';
const USER_PROFILE_KEY = 'user_profile';
const SCAN_HISTORY_KEY = 'scan_history';
const CONVERSATION_KEY = 'current_conversation';

// Initialize data from local storage
let objectives = JSON.parse(localStorage.getItem(OBJECTIVES_KEY)) || [];
let userProfile = JSON.parse(localStorage.getItem(USER_PROFILE_KEY)) || {};
let scanHistoryItems = JSON.parse(localStorage.getItem(SCAN_HISTORY_KEY)) || [];
let currentConversation = JSON.parse(localStorage.getItem(CONVERSATION_KEY)) || [];

// Function to reset all data
function resetAllData() {
    // Clear all localStorage items
    localStorage.removeItem(OBJECTIVES_KEY);
    localStorage.removeItem(USER_PROFILE_KEY);
    localStorage.removeItem(SCAN_HISTORY_KEY);
    localStorage.removeItem(CONVERSATION_KEY);
    
    // Reload the page
    window.location.reload();
}

// Conversation modes
const CONVERSATION_MODES = {
    GENERAL: 'general',
    DEFINE_OBJECTIVE: 'define_objective',
    COLLECT_METRICS: 'collect_metrics',
    SCAN_FOOD: 'scan_food'
};

// Current conversation mode
let currentMode = CONVERSATION_MODES.GENERAL;

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    renderObjectives();
    renderScanHistory();
    renderConversation();
    
    // Add objective button
    addObjectiveBtn.addEventListener('click', () => {
        startObjectiveDefinition();
    });
    
    // Close modal
    closeModalBtn.addEventListener('click', () => {
        objectiveModal.classList.add('hidden');
    });
    
    // Submit objective form
    objectiveForm.addEventListener('submit', handleObjectiveFormSubmit);
    
    // Send message
    sendMessageBtn.addEventListener('click', handleSendMessage);
    userMessageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    
    // Food image upload
    foodImageInput.addEventListener('change', () => {
        scanFoodBtn.disabled = !foodImageInput.files.length;
    });
    
    // Scan food
    scanFoodBtn.addEventListener('click', handleScanFood);
});

// Functions
function renderObjectives() {
    if (objectives.length === 0) {
        objectivesList.innerHTML = '<p class="empty-state">No objectives defined yet.</p>';
        return;
    }
    
    objectivesList.innerHTML = objectives.map((obj, index) => `
        <div class="objective-item">
            <p>${obj}</p>
            <button class="delete-btn" data-index="${index}">×</button>
        </div>
    `).join('');
    
    // Add delete event listeners
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = parseInt(e.target.dataset.index);
            deleteObjective(index);
        });
    });
}

function deleteObjective(index) {
    const objectiveToDelete = objectives[index];
    objectives.splice(index, 1);
    saveObjectives();
    
    // Clean up metrics that are exclusively used by this objective
    cleanupOrphanedMetrics(objectiveToDelete);
    
    renderObjectives();
}

function cleanupOrphanedMetrics(deletedObjective) {
    // Find metrics that are exclusively used by the deleted objective
    for (const key in userProfile) {
        if (userProfile[key] && userProfile[key].objectiveIds) {
            // Filter out the deleted objective
            userProfile[key].objectiveIds = userProfile[key].objectiveIds.filter(id => id !== deletedObjective);
            
            // If no objectives are left, remove the metric
            if (userProfile[key].objectiveIds.length === 0) {
                delete userProfile[key];
            }
        }
    }
    
    saveUserProfile();
}

function renderScanHistory() {
    if (scanHistoryItems.length === 0) {
        scanHistory.innerHTML = '<p class="empty-state">No scanned items yet.</p>';
        return;
    }
    
    scanHistory.innerHTML = scanHistoryItems.map(item => `
        <div class="history-item">
            <div class="status ${item.isAllowed ? 'good' : 'bad'}"></div>
            <div class="details">
                <h4>${item.foodItem}</h4>
                <p>${item.reason}</p>
                <p class="date">${new Date(item.timestamp).toLocaleString()}</p>
            </div>
        </div>
    `).join('');
}

function renderConversation() {
    // Clear chat messages
    chatMessages.innerHTML = '';
    
    // Render each message in the conversation
    currentConversation.forEach(message => {
        if (message.role === 'user') {
            addChatMessage(message.content, true);
        } else if (message.role === 'assistant') {
            addChatMessage(message.content, false);
        }
        // Skip system messages as they're not shown to the user
    });
}

function saveObjectives() {
    localStorage.setItem(OBJECTIVES_KEY, JSON.stringify(objectives));
}

function saveUserProfile() {
    localStorage.setItem(USER_PROFILE_KEY, JSON.stringify(userProfile));
}

function saveScanHistory() {
    localStorage.setItem(SCAN_HISTORY_KEY, JSON.stringify(scanHistoryItems));
}

function saveConversation() {
    localStorage.setItem(CONVERSATION_KEY, JSON.stringify(currentConversation));
}

function addChatMessage(message, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    messageDiv.classList.add(isUser ? 'user' : 'bot');
    messageDiv.innerHTML = `<p>${message}</p>`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function startObjectiveDefinition() {
    // Switch to objective definition mode
    currentMode = CONVERSATION_MODES.DEFINE_OBJECTIVE;
    
    // Clear the current conversation
    currentConversation = [];
    saveConversation();
    
    // Add initial system message
    currentConversation.push({
        role: 'system',
        content: 'Starting objective definition flow'
    });
    
    // Add initial assistant message
    currentConversation.push({
        role: 'assistant',
        content: 'Let\'s define your health objective. What is your goal? For example, do you want to lose weight, manage a medical condition, or follow a specific diet?'
    });
    
    // Render the conversation
    renderConversation();
}

function startHealthMetricsCollection(objective) {
    // Switch to health metrics collection mode
    currentMode = CONVERSATION_MODES.COLLECT_METRICS;
    
    // Clear the current conversation
    currentConversation = [];
    saveConversation();
    
    // Add initial system message
    currentConversation.push({
        role: 'system',
        content: 'Starting health metrics collection flow'
    });
    
    // Add initial assistant message
    currentConversation.push({
        role: 'assistant',
        content: `Now let's collect some health metrics related to your objective: "${objective}". What metrics would you like to track? For example, weight, blood pressure, etc.`
    });
    
    // Render the conversation
    renderConversation();
}

async function handleObjectiveFormSubmit(e) {
    e.preventDefault();
    
    const objectiveText = document.getElementById('objective-text').value.trim();
    if (!objectiveText) {
        alert('Please enter an objective');
        return;
    }
    
    // Close the modal
    objectiveModal.classList.add('hidden');
    
    // Start the objective definition flow in the chat
    startObjectiveDefinition();
    
    // Add the user's initial objective as a message
    await handleSendMessage(objectiveText);
}

async function handleSendMessage(manualMessage = null) {
    const message = manualMessage || userMessageInput.value.trim();
    if (!message) return;
    
    // Ensure message is a string
    const messageContent = typeof message === 'object' ? JSON.stringify(message) : String(message);
    
    // Add user message to conversation
    currentConversation.push({
        role: 'user',
        content: messageContent
    });
    saveConversation();
    
    // Add user message to chat UI
    addChatMessage(message, true);
    
    // Clear input if not a manual message
    if (!manualMessage) {
        userMessageInput.value = '';
    }
    
    try {
        let endpoint;
        let requestBody;
        
        // Map conversation mode to agent type
        let agentType;
        switch (currentMode) {
            case CONVERSATION_MODES.DEFINE_OBJECTIVE:
                agentType = 'defineObjective';
                break;
                
            case CONVERSATION_MODES.COLLECT_METRICS:
                agentType = 'collectHealthMetrics';
                break;
                
            case CONVERSATION_MODES.SCAN_FOOD:
                agentType = 'scanFood';
                break;
                
            case CONVERSATION_MODES.GENERAL:
            default:
                // For general conversation, detect agent type on the server
                agentType = null;
                break;
        }
        
        // Use the orchestration endpoint for all requests
        endpoint = '/api/orchestrate';
        requestBody = {
            conversation: currentConversation,
            userProfile: userProfile,
            objective: objectives.length > 0 ? objectives[objectives.length - 1] : '',
            agentType: agentType
        };
        
        // Call the API
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Update the conversation with the LLM's response
            currentConversation = data.updatedConversation;
            saveConversation();
            
            // Render the updated conversation
            renderConversation();
            
            // Handle specific responses based on mode
            if (currentMode === CONVERSATION_MODES.DEFINE_OBJECTIVE) {
                // If we have a finalized objective from the backend, add it to the objectives list
                if (data.objective) {
                    objectives.push(data.objective);
                    saveObjectives();
                    renderObjectives();
                    
                    // Update the user profile for this objective
                    await updateUserProfileForObjective(data.objective);
                    
                    // Switch to health metrics collection mode
                    startHealthMetricsCollection(data.objective);
                } 
                // If no objective was extracted but user mentioned type 2 diabetes
                else if (message.toLowerCase().includes('type 2 diabetes') || message.toLowerCase().includes('diabetes')) {
                    const diabetesObjective = "Manage type 2 diabetes through diet, exercise, and regular monitoring";
                    objectives.push(diabetesObjective);
                    saveObjectives();
                    renderObjectives();
                    
                    // Update the user profile for this objective
                    await updateUserProfileForObjective(diabetesObjective);
                    
                    // Switch to health metrics collection mode
                    startHealthMetricsCollection(diabetesObjective);
                }
            }
            
            if (currentMode === CONVERSATION_MODES.COLLECT_METRICS && data.updatedUserProfile) {
                // Update the user profile with the collected metrics
                userProfile = data.updatedUserProfile;
                saveUserProfile();
            }
            
            if (currentMode === CONVERSATION_MODES.SCAN_FOOD && data.result) {
                // Display the scan result
                displayScanResult(data.result);
                
                // Add to scan history
                addToScanHistory(data.result);
            }
        } else {
            addChatMessage('Sorry, I encountered an error processing your message.');
        }
    } catch (error) {
        console.error('Error:', error);
        addChatMessage('Sorry, there was an error connecting to the server.');
    }
}

async function updateUserProfileForObjective(objective) {
    try {
        // Call the API to update the user profile based on the objective
        const response = await fetch(`${API_BASE_URL}/api/define-health-profile`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                objective: objective,
                userProfile: userProfile
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Update the user profile
            userProfile = data.updatedUserProfile;
            saveUserProfile();
        }
    } catch (error) {
        console.error('Error updating user profile:', error);
    }
}

async function handleScanFood() {
    if (!foodImageInput.files.length) {
        alert('Please select an image first');
        return;
    }
    
    // Switch to food scanning mode
    currentMode = CONVERSATION_MODES.SCAN_FOOD;
    
    // Clear the current conversation
    currentConversation = [];
    saveConversation();
    
    // Add initial system message
    currentConversation.push({
        role: 'system',
        content: 'Starting food scanning flow'
    });
    
    // Add initial user message
    currentConversation.push({
        role: 'user',
        content: 'Can you scan this food item for me?'
    });
    saveConversation();
    
    // Render the conversation
    renderConversation();
    
    try {
        // Show loading state
        scanFoodBtn.textContent = 'Scanning...';
        scanFoodBtn.disabled = true;
        
        // Prepare the image for upload
        const file = foodImageInput.files[0];
        const reader = new FileReader();
        
        reader.onload = async function(event) {
            const imageData = event.target.result.split(',')[1]; // Get base64 data
            
            // Call the orchestration API
            const response = await fetch(`${API_BASE_URL}/api/orchestrate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    conversation: currentConversation,
                    imageData: imageData,
                    userProfile: userProfile,
                    agentType: 'scanFood',
                    objective: objectives.length > 0 ? objectives[objectives.length - 1] : ''
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Update the conversation
                currentConversation = data.updatedConversation;
                saveConversation();
                
                // Render the updated conversation
                renderConversation();
                
                // If there's a result, display it and add to history
                if (data.result) {
                    displayScanResult(data.result);
                    addToScanHistory(data.result);
                }
            } else {
                addChatMessage('Sorry, I encountered an error scanning the food item.');
            }
        };
        
        reader.readAsDataURL(file);
    } catch (error) {
        console.error('Error:', error);
        addChatMessage('Sorry, there was an error connecting to the server.');
    } finally {
        // Reset button
        scanFoodBtn.textContent = 'Scan Food';
        scanFoodBtn.disabled = false;
        
        // Reset file input
        foodImageInput.value = '';
    }
}

function displayScanResult(result) {
    // Display result
    scanResult.classList.remove('hidden');
    scanResult.classList.remove('allowed', 'not-allowed');
    scanResult.classList.add(result.isAllowed ? 'allowed' : 'not-allowed');
    
    scanResult.innerHTML = `
        <h3>${result.isAllowed ? 'Good Choice!' : 'Not Recommended'}</h3>
        <p><strong>Food Item:</strong> ${result.foodItem}</p>
        <p><strong>Reason:</strong> ${result.reason}</p>
    `;
    
    // Play sound based on result
    const sound = new Audio(result.isAllowed ? 
        'https://www.soundjay.com/buttons/sounds/button-09.mp3' : 
        'https://www.soundjay.com/buttons/sounds/button-10.mp3');
    sound.play().catch(e => console.log('Sound playback failed:', e));
}

function addToScanHistory(result) {
    // Add to scan history
    const historyItem = {
        foodItem: result.foodItem,
        isAllowed: result.isAllowed,
        reason: result.reason,
        timestamp: new Date().toISOString()
    };
    
    scanHistoryItems.unshift(historyItem);
    if (scanHistoryItems.length > 10) {
        scanHistoryItems.pop(); // Keep only the 10 most recent items
    }
    
    saveScanHistory();
    renderScanHistory();
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize event listener for reset button
    resetDataBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to reset all data? This will clear all your objectives, health profile, and conversation history.')) {
            resetAllData();
        }
    });
});
