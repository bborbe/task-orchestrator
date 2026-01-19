// TaskOrchestrator Kanban Board

let currentVault = null;

// Load tasks on page load
document.addEventListener('DOMContentLoaded', () => {
    loadVaults();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('vault-selector').addEventListener('change', handleVaultChange);
    document.getElementById('refresh-btn').addEventListener('click', loadTasks);
    document.getElementById('copy-btn').addEventListener('click', copyCommand);
    document.getElementById('close-btn').addEventListener('click', closeModal);
    setupDragAndDrop();
}

async function loadVaults() {
    try {
        const response = await fetch('/api/vaults');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const vaults = await response.json();
        const selector = document.getElementById('vault-selector');

        // Clear existing options
        selector.innerHTML = '';

        // Add vault options
        vaults.forEach(vault => {
            const option = document.createElement('option');
            option.value = vault.name;
            option.textContent = vault.name;
            selector.appendChild(option);
        });

        // Load saved vault from localStorage or use first vault
        const savedVault = localStorage.getItem('selectedVault');
        if (savedVault && vaults.find(v => v.name === savedVault)) {
            selector.value = savedVault;
            currentVault = savedVault;
        } else if (vaults.length > 0) {
            currentVault = vaults[0].name;
        }

        // Load tasks for selected vault
        if (currentVault) {
            await loadTasks();
        }
    } catch (error) {
        console.error('Failed to load vaults:', error);
        alert(`Failed to load vaults: ${error.message}`);
    }
}

function handleVaultChange(e) {
    currentVault = e.target.value;
    localStorage.setItem('selectedVault', currentVault);
    loadTasks();
}

function setupDragAndDrop() {
    // Add drop handlers to all columns
    const columns = document.querySelectorAll('.cards');
    columns.forEach(column => {
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('drop', handleDrop);
        column.addEventListener('dragleave', handleDragLeave);
    });
}

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

async function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');

    if (!currentVault) {
        alert('No vault selected');
        return;
    }

    const taskId = e.dataTransfer.getData('text/plain');
    const newPhase = e.currentTarget.id.replace('cards-', '');

    try {
        const response = await fetch(`/api/tasks/${taskId}/phase?vault=${encodeURIComponent(currentVault)}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ phase: newPhase }),
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(error);
        }

        // Reload tasks to reflect changes
        await loadTasks();
    } catch (error) {
        console.error('Failed to update task phase:', error);
        alert(`Failed to update task: ${error.message}`);
    }
}

async function loadTasks() {
    if (!currentVault) {
        return;
    }

    try {
        // Fetch in_progress tasks with all phases
        const response = await fetch(`/api/tasks?vault=${encodeURIComponent(currentVault)}&status=in_progress&phase=todo,planning,in_progress,ai_review,human_review,done`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const tasks = await response.json();

        // Clear existing cards
        ['todo', 'planning', 'in_progress', 'ai_review', 'human_review', 'done'].forEach(phase => {
            const container = document.getElementById(`cards-${phase}`);
            if (container) {
                container.innerHTML = '';
            }
        });

        // Populate cards by phase
        const validPhases = ['todo', 'planning', 'in_progress', 'ai_review', 'human_review', 'done'];
        tasks.forEach(task => {
            // Default to todo if phase is missing or invalid
            const phase = task.phase && validPhases.includes(task.phase) ? task.phase : 'todo';
            const container = document.getElementById(`cards-${phase}`);
            if (container) {
                const card = createTaskCard(task);
                container.appendChild(card);
            }
        });

    } catch (error) {
        console.error('Failed to load tasks:', error);
        alert(`Failed to load tasks: ${error.message}`);
    }
}

function createTaskCard(task) {
    const card = document.createElement('div');
    card.className = 'task-card';
    card.draggable = true;
    card.dataset.taskId = task.id;

    // Drag handlers
    card.addEventListener('dragstart', (e) => {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', task.id);
        card.classList.add('dragging');
    });

    card.addEventListener('dragend', (e) => {
        card.classList.remove('dragging');
    });

    // Build card HTML
    const projectBadge = task.project_path
        ? `<div class="project-badge">${task.project_path}</div>`
        : '<div class="project-badge">No project</div>';

    const runButton = task.project_path
        ? `<button onclick="runTask('${task.id}')">▶ Run</button>`
        : '';

    card.innerHTML = `
        <div class="task-header">
            <h3>${escapeHtml(task.title)}</h3>
            <a href="${task.obsidian_url}" class="obsidian-link" title="Open in Obsidian">
                📝
            </a>
        </div>
        ${projectBadge}
        ${runButton}
    `;

    return card;
}

async function runTask(taskId) {
    if (!currentVault) {
        alert('No vault selected');
        return;
    }

    try {
        // Show loading state
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = '⏳ Starting...';
        button.disabled = true;

        // Start Claude session
        const response = await fetch(`/api/tasks/${taskId}/run?vault=${encodeURIComponent(currentVault)}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(error);
        }

        const data = await response.json();

        // Show session modal
        showModal(data.session_id, data.handoff_command);

        // Restore button
        button.textContent = originalText;
        button.disabled = false;

    } catch (error) {
        console.error('Failed to run task:', error);
        alert(`Failed to start session: ${error.message}`);

        // Restore button
        if (event && event.target) {
            event.target.textContent = '▶ Run';
            event.target.disabled = false;
        }
    }
}

function showModal(sessionId, command) {
    document.getElementById('session-id').textContent = sessionId;
    document.getElementById('handoff-command').textContent = command;
    document.getElementById('session-modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('session-modal').classList.add('hidden');
}

async function copyCommand() {
    const command = document.getElementById('handoff-command').textContent;

    try {
        await navigator.clipboard.writeText(command);

        // Show feedback
        const button = document.getElementById('copy-btn');
        const originalText = button.textContent;
        button.textContent = '✓ Copied!';

        setTimeout(() => {
            button.textContent = originalText;
        }, 2000);
    } catch (error) {
        console.error('Failed to copy:', error);
        alert('Failed to copy to clipboard');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
