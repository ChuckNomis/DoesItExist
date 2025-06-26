document.getElementById('idea-form').addEventListener('submit', async function (e) {
    e.preventDefault();
    const ideaText = document.getElementById('idea-text').value;
    if (!ideaText) {
        alert('Please enter an idea.');
        return;
    }

    const resultsContainer = document.getElementById('results-container');
    const resultsContent = document.getElementById('results-content');
    const submitButton = this.querySelector('button');

    resultsContainer.classList.remove('hidden');
    resultsContent.innerHTML = '<p>The agent is thinking...</p>';
    submitButton.disabled = true;
    submitButton.textContent = 'Checking...';

    try {
        const response = await fetch('/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ idea: ideaText }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // The final result is in the 'summary' key
        const finalSummary = data.summary;
        
        if (finalSummary) {
            resultsContent.innerHTML = finalSummary.replace(/\n/g, '<br>');
        } else {
            resultsContent.innerHTML = '<p>The agent did not produce a final summary.</p>';
        }

    } catch (error) {
        console.error('Error:', error);
        resultsContent.innerHTML = `<p style="color: red;">An error occurred: ${error.message}</p>`;
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Check Idea';
    }
}); 