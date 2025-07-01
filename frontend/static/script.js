document.addEventListener('DOMContentLoaded', () => {
    const ideaForm = document.getElementById('idea-form');
    const themeSwitch = document.getElementById('theme-switch');

    ideaForm.addEventListener('submit', handleFormSubmit);
    themeSwitch.addEventListener('change', toggleTheme);

    // Set initial theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    themeSwitch.checked = savedTheme === 'dark';

    var modal = document.getElementById('warning-modal');
    var closeButton = document.querySelector('.close-button');

    // Display the modal
    modal.style.display = 'block';

    // Close the modal when the close button is clicked
    closeButton.onclick = function() {
        modal.style.display = 'none';
    }

    // Close the modal when clicking outside of the modal content
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    }
});

async function handleFormSubmit(e) {
    e.preventDefault();
    const ideaText = document.getElementById('idea-text').value;
    if (!ideaText.trim()) {
        alert('Please enter an idea.');
        return;
    }

    const resultsContainer = document.getElementById('results-container');
    const resultsContent = document.getElementById('results-content');
    const submitButton = this.querySelector('button');

    resultsContainer.classList.remove('hidden');
    resultsContent.innerHTML = '<div class="spinner"></div>';
    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';

    try {
        const response = await fetch('/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ idea: ideaText }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }

        const data = await response.json();
        const finalSummary = data.summary;

        if (finalSummary) {
            resultsContent.innerHTML = parseResponse(finalSummary);
        } else {
            resultsContent.innerHTML = '<p>The agent did not produce a final summary.</p>';
        }

    } catch (error) {
        console.error('Error:', error);
        resultsContent.innerHTML = `<div class="error"><strong>Error:</strong> ${error.message}</div>`;
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = '<i class="fas fa-search"></i> Check If It Exists';
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

function getVerdictInfo(verdictText) {
    const text = verdictText.toLowerCase();
    
    if (text.includes('likely original') || text.includes('original')) {
        return {
            icon: 'fas fa-check-circle',
            class: 'verdict-original',
            title: 'Likely Original'
        };
    } else if (text.includes('already exists') || text.includes('exists')) {
        return {
            icon: 'fas fa-times-circle',
            class: 'verdict-exists',
            title: 'Already Exists'
        };
    } else {
        return {
            icon: 'fas fa-exclamation-triangle',
            class: 'verdict-overlapping',
            title: 'Possibly Overlapping'
        };
    }
}

function extractConfidence(text) {
    const confidenceMatch = text.match(/(\d+)%\s*(?:confidence|match|similarity)/i);
    return confidenceMatch ? parseInt(confidenceMatch[1]) : null;
}

function createConfidenceIndicator(confidence) {
    return `
        <div class="confidence-indicator">
            <div class="confidence-label">Confidence Level</div>
            <div class="confidence-bar">
                <div class="confidence-fill" style="width: ${confidence}%"></div>
            </div>
            <div class="confidence-text">${confidence}% match with existing inventions</div>
        </div>
    `;
}

function parseResponse(text) {
    // 1. Cleanup any markdown fences
    text = text.replace(/^```markdown\s*/, '').replace(/```\s*$/, '').trim();

    // 2. Extract confidence if present
    const confidence = extractConfidence(text);

    // 3. Process sections using regex
    let html = '';
    const verdictMatch = text.match(/\*\*Verdict:\*\*\s*([\s\S]*?)(?=\n\s*\*\*Summary:|\n\s*\*\*Top Findings:|$)/);
    const summaryMatch = text.match(/\*\*Summary:\*\*\s*([\s\S]*?)(?=\n\s*\*\*Top Findings:|$)/);
    const findingsMatch = text.match(/\*\*Top Findings:\*\*\s*([\s\S]*)/);

    // Verdict Section
    if (verdictMatch) {
        const verdictText = verdictMatch[1].trim();
        const verdictInfo = getVerdictInfo(verdictText);
        
        html += `
            <div class="verdict-section">
                <div class="verdict-header">
                    <i class="${verdictInfo.icon} verdict-icon ${verdictInfo.class}"></i>
                    <h2 class="verdict-title">Result: ${verdictInfo.title}</h2>
                </div>
            </div>
        `;
    }

    // Confidence Indicator
    if (confidence) {
        html += createConfidenceIndicator(confidence);
    }

    // Summary Section
    if (summaryMatch) {
        const summaryText = summaryMatch[1].trim();
        // Extract key insight (usually the first sentence)
        const sentences = summaryText.split('. ');
        const keyInsight = sentences[0] + (sentences.length > 1 ? '.' : '');
        const restOfSummary = sentences.slice(1).join('. ');
        
        html += `
            <div class="summary-card">
                <h3>Summary</h3>
                <p><span class="summary-insight">${keyInsight}</span>${restOfSummary ? ' ' + restOfSummary : ''}</p>
            </div>
        `;
    }

    // Top Findings Section
    if (findingsMatch) {
        html += '<div class="findings-section">';
        html += '<h3>Top Findings</h3>';
        html += '<ul class="findings-list">';
        
        // Split findings into individual items. Each starts with '- **'
        const findings = findingsMatch[1].trim().split(/\n\s*(?=-\s*\*\*)/);
        
        findings.forEach(finding => {
            if (!finding.trim()) return;

            // Remove the leading '- '
            finding = finding.trim().substring(2).trim();

            const titleMatch = finding.match(/\*\*(.*?)\*\*/);
            const title = titleMatch ? titleMatch[1] : 'Untitled Finding';
            
            const linkMatch = finding.match(/\[(.*?)\]\((.*?)\)/);
            const linkText = linkMatch ? linkMatch[1] : 'Read more';
            const linkUrl = linkMatch ? linkMatch[2] : '#';
            
            let snippet = finding.replace(/\*\*(.*?)\*\*/, '');
            if(linkMatch) snippet = snippet.replace(linkMatch[0], '');
            snippet = snippet.trim();

            // Clean up snippet
            if (snippet.length > 200) {
                snippet = snippet.substring(0, 200) + '...';
            }

            html += `
                <li class="finding-card">
                    <div class="finding-title">${title}</div>
                    <p class="finding-snippet">${snippet}</p>
                    <a href="${linkUrl}" target="_blank" rel="noopener noreferrer" class="finding-link">
                        ${linkText}
                    </a>
                </li>
            `;
        });
        html += '</ul>';
        html += '</div>';
    }

    // Fallback if no structured content found
    if (!html) {
        return `<div class="summary-card"><p>${text.replace(/\n/g, '<br>')}</p></div>`;
    }

    return html;
} 