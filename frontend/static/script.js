document.addEventListener('DOMContentLoaded', () => {
    const ideaForm = document.getElementById('idea-form');
    const themeSwitch = document.getElementById('theme-switch');

    ideaForm.addEventListener('submit', handleFormSubmit);
    themeSwitch.addEventListener('change', toggleTheme);

    // Set initial theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    themeSwitch.checked = savedTheme === 'dark';
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
        resultsContent.innerHTML = `<p class="error">An error occurred: ${error.message}</p>`;
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Check Idea';
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

function parseResponse(text) {
    // 1. Cleanup any markdown fences
    text = text.replace(/^```markdown\s*/, '').replace(/```\s*$/, '').trim();

    // 2. Process sections using regex
    let html = '';
    const verdictMatch = text.match(/\*\*Verdict:\*\*\s*([\s\S]*?)(?=\n\s*\*\*Summary:|\n\s*\*\*Top Findings:|$)/);
    const summaryMatch = text.match(/\*\*Summary:\*\*\s*([\s\S]*?)(?=\n\s*\*\*Top Findings:|$)/);
    const findingsMatch = text.match(/\*\*Top Findings:\*\*\s*([\s\S]*)/);

    if (verdictMatch) {
        html += `<h2>${verdictMatch[1].trim()}</h2>`;
    }

    if (summaryMatch) {
        html += `<h3>Summary</h3><p>${summaryMatch[1].trim()}</p>`;
    }

    if (findingsMatch) {
        html += '<h3>Top Findings</h3>';
        html += '<ul>';
        // Split findings into individual items. Each starts with '- **'
        const findings = findingsMatch[1].trim().split(/\n\s*(?=-\s*\*\*)/);
        
        findings.forEach(finding => {
            if (!finding.trim()) return;

            // Remove the leading '- '
            finding = finding.trim().substring(2).trim();

            const titleMatch = finding.match(/\*\*(.*?)\*\*/);
            const title = titleMatch ? titleMatch[1] : 'No Title';
            
            const linkMatch = finding.match(/\[(.*?)\]\((.*?)\)/);
            const linkText = linkMatch ? linkMatch[1] : 'Read more';
            const linkUrl = linkMatch ? linkMatch[2] : '#';
            
            let snippet = finding.replace(/\*\*(.*?)\*\*/, '');
            if(linkMatch) snippet = snippet.replace(linkMatch[0], '');
            snippet = snippet.trim();

            html += `
                <li>
                    <div class="finding-title">${title}</div>
                    <p class="finding-snippet">${snippet}</p>
                    <a href="${linkUrl}" target="_blank" rel="noopener noreferrer" class="finding-link">${linkText}</a>
                </li>
            `;
        });
        html += '</ul>';
    }

    if (!html) {
        return `<p>${text.replace(/\n/g, '<br>')}</p>`;
    }

    return html;
} 