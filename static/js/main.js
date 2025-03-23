document.addEventListener('DOMContentLoaded', () => {
    let stream = null;
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const photo = document.getElementById('photo');
    const startButton = document.getElementById('startCamera');
    const captureButton = document.getElementById('capturePhoto');
    const retakeButton = document.getElementById('retakePhoto');
    const analyzeButton = document.getElementById('analyzePhoto');
    const healthConditions = new Set();

    // Health conditions management
    const addConditionButton = document.getElementById('addCondition');
    const conditionInput = document.getElementById('conditionInput');
    const conditionsList = document.getElementById('conditionsList');

    // Debug element existence
    console.log('Elements found:', {
        addButton: addConditionButton,
        input: conditionInput,
        list: conditionsList
    });

    function addCondition(e) {
        e?.preventDefault(); // Prevent form submission if called from a form
        const condition = conditionInput.value.trim();
        if (condition) {
            healthConditions.add(condition);
            updateConditionsList();
            conditionInput.value = '';
            conditionInput.focus(); // Keep focus for multiple entries
        }
    }

    // Add button click handler
    if (addConditionButton) {
        addConditionButton.onclick = addCondition;
    }

    // Enter key handler
    if (conditionInput) {
        conditionInput.onkeypress = (e) => {
            if (e.key === 'Enter') {
                addCondition(e);
            }
        };
    }

    function updateConditionsList() {
        if (!conditionsList) return;
        
        conditionsList.innerHTML = '';
        healthConditions.forEach(condition => {
            const tag = document.createElement('span');
            tag.className = 'condition-tag';
            tag.innerHTML = `${condition}<span class="remove-condition">&times;</span>`;
            
            const removeButton = tag.querySelector('.remove-condition');
            removeButton.onclick = (e) => {
                e.preventDefault();
                healthConditions.delete(condition);
                updateConditionsList();
            };
            
            conditionsList.appendChild(tag);
        });
    }

    // Camera handling
    async function initializeCamera() {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Camera API is not supported in this browser');
            }

            // First try to access the environment-facing camera
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: { exact: "environment" } },
                    audio: false
                });
            } catch (envCameraError) {
                // Fall back to any available camera
                stream = await navigator.mediaDevices.getUserMedia({
                    video: true,
                    audio: false
                });
            }

            video.srcObject = stream;
            await video.play();
            
            video.style.display = 'block';
            startButton.style.display = 'none';
            captureButton.style.display = 'block';
            
        } catch (err) {
            let errorMessage = 'Error accessing camera. ';
            switch(err.name) {
                case 'NotAllowedError':
                    errorMessage += 'Please grant camera permissions in your browser settings.';
                    break;
                case 'NotFoundError':
                    errorMessage += 'No camera device was found.';
                    break;
                case 'NotReadableError':
                    errorMessage += 'Camera is already in use by another application.';
                    break;
                default:
                    errorMessage += err.message || 'Please ensure you have a working camera.';
            }
            alert(errorMessage);
        }
    }

    startButton.addEventListener('click', initializeCamera);

    captureButton.addEventListener('click', () => {
        try {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            
            const context = canvas.getContext('2d');
            context.drawImage(video, 0, 0);
            
            const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
            photo.src = dataUrl;
            photo.style.display = 'block';
            video.style.display = 'none';
            captureButton.style.display = 'none';
            retakeButton.style.display = 'block';
            analyzeButton.style.display = 'block';
            
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        } catch (err) {
            alert('Failed to capture photo: ' + err.message);
        }
    });

    retakeButton.addEventListener('click', () => {
        photo.style.display = 'none';
        retakeButton.style.display = 'none';
        analyzeButton.style.display = 'none';
        startButton.style.display = 'block';
        document.getElementById('resultsCard').style.display = 'none';
        photo.src = '';
    });

    function createListCard(title, items, cardClass = '') {
        const card = document.createElement('div');
        card.className = `card mb-3 ${cardClass}`;
        
        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';
        
        const cardTitle = document.createElement('h5');
        cardTitle.className = 'card-title';
        cardTitle.textContent = title;
        
        const list = document.createElement('ul');
        list.className = 'list-group list-group-flush';
        items.forEach(item => {
            const listItem = document.createElement('li');
            listItem.className = 'list-group-item';
            listItem.textContent = item;
            list.appendChild(listItem);
        });
        
        cardBody.appendChild(cardTitle);
        cardBody.appendChild(list);
        card.appendChild(cardBody);
        
        return card;
    }

    function displayAnalysisResults(analysis) {
        const resultsDiv = document.getElementById('resultsCard');
        resultsDiv.innerHTML = '';
        resultsDiv.style.display = 'block';

        // Ingredients Card
        resultsDiv.appendChild(createListCard(
            'Identified Ingredients',
            analysis.identified_ingredients
        ));

        // Health Benefits Card
        resultsDiv.appendChild(createListCard(
            'Health Benefits',
            analysis.health_benefits,
            'border-success'
        ));

        // Health Risks Card
        resultsDiv.appendChild(createListCard(
            'Health Risks',
            analysis.health_risks,
            'border-danger'
        ));

        // Diet Compatibility Card
        resultsDiv.appendChild(createListCard(
            'Diet & Allergy Compatibility',
            analysis.diet_compatibility.details,
            analysis.diet_compatibility.status === 'positive' ? 'border-success bg-success bg-opacity-10' : 'border-warning bg-warning bg-opacity-10'
        ));

        // Health Impact Card
        resultsDiv.appendChild(createListCard(
            'Impact on Health Conditions',
            analysis.health_impact.details,
            analysis.health_impact.status === 'positive' ? 'border-success bg-success bg-opacity-10' : 'border-warning bg-warning bg-opacity-10'
        ));
    }

    analyzeButton.addEventListener('click', async () => {
        if (!photo.src) {
            alert('Please capture a photo first');
            return;
        }

        const allergies = [];
        if (document.getElementById('nutAllergy').checked) allergies.push('nuts');
        if (document.getElementById('dairyAllergy').checked) allergies.push('dairy');
        if (document.getElementById('shellfishAllergy').checked) allergies.push('shellfish');

        const data = {
            image: photo.src,
            dietType: document.getElementById('dietType').value,
            allergies: allergies,
            healthConditions: Array.from(healthConditions)
        };

        analyzeButton.disabled = true;
        analyzeButton.textContent = 'Analyzing...';
        document.getElementById('resultsCard').style.display = 'none';

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `HTTP error! status: ${response.status}`);
            }
            
            if (result.success) {
                displayAnalysisResults(result.analysis);
            } else {
                throw new Error(result.error || 'Unknown error occurred');
            }
        } catch (error) {
            alert('Error analyzing ingredients: ' + error.message);
        } finally {
            analyzeButton.disabled = false;
            analyzeButton.textContent = 'Analyze Ingredients';
        }
    });
});
