// TaskOrchestrator Kanban Board

let currentVault = null;
let tasksCache = {}; // Map of task ID -> task data
let ws = null; // WebSocket connection

// Load tasks on page load
document.addEventListener('DOMContentLoaded', () => {
    loadVaults();
    setupEventListeners();
    connectWebSocket();
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

        // Cache tasks for quick lookup
        tasksCache = {};
        tasks.forEach(task => {
            tasksCache[task.id] = task;
        });

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

function extractJiraIssue(title) {
    // Detect Jira issue key pattern: PROJECT-NUMBER
    const jiraKeyPattern = /\b([A-Z]+)-(\d+)\b/;
    const match = title.match(jiraKeyPattern);

    if (!match) {
        return { title: title, issueKey: null, issueUrl: null };
    }

    const issueKey = match[0];
    const project = match[1];

    // Map project keys to Atlassian domains
    const projectDomains = {
        'BRO': 'seibertgroup.atlassian.net',
        'TRADE': 'borbe.atlassian.net'
    };

    const domain = projectDomains[project];
    const issueUrl = domain ? `https://${domain}/browse/${issueKey}` : null;

    // Remove issue key from title
    const cleanTitle = title.replace(jiraKeyPattern, '').trim();

    return { title: cleanTitle, issueKey, issueUrl };
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

    // Extract Jira issue info
    const { title, issueKey, issueUrl } = extractJiraIssue(task.title);

    // Show Resume button if session exists, otherwise Start
    const hasSession = task.claude_session_id;
    const buttonLabel = hasSession ? '▶ Resume' : '▶ Start';
    const buttonClass = hasSession ? 'resume-btn' : 'start-btn';
    const startButton = `<button class="${buttonClass}" onclick="runTask('${task.id}')">${buttonLabel}</button>`;

    const menuButton = '<button class="menu-btn" onclick="showTaskMenu(event, \'' + task.id + '\')">⋮</button>';

    // Jira issue badge (if present)
    const jiraBadge = issueKey && issueUrl
        ? `<a href="${issueUrl}" class="jira-badge" target="_blank" title="Open in Jira">
             <span class="jira-icon">🔖</span><span>${escapeHtml(issueKey)}</span>
           </a>`
        : '';

    // Assignee badge (if present)
    const assigneeBadge = task.assignee
        ? `<span class="assignee-badge" title="Assigned to ${escapeHtml(task.assignee)}">
             <span class="assignee-icon">👤</span><span>${escapeHtml(task.assignee)}</span>
           </span>`
        : '';

    card.innerHTML = `
        ${menuButton}
        <div class="card-content">
            <h3 class="task-title">
                <a href="${task.obsidian_url}" class="task-title-link" title="Open in Obsidian">
                    ${escapeHtml(title)}
                    <span class="obsidian-icon">↗</span>
                </a>
            </h3>
        </div>
        <div class="card-footer">
            <div class="card-footer-left">
                ${jiraBadge}
                ${assigneeBadge}
            </div>
            <div class="card-actions">
                ${startButton}
            </div>
        </div>
    `;

    return card;
}

async function runTask(taskId) {
    if (!currentVault) {
        alert('No vault selected');
        return;
    }

    // Look up task from cache
    const task = tasksCache[taskId];
    if (!task) {
        alert('Task not found in cache');
        return;
    }

    try {
        // Show loading state
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = '⏳ Loading...';
        button.disabled = true;

        // If task already has a session, show resume modal directly
        if (task.claude_session_id) {
            // Get vault config to build command
            const vaultsResponse = await fetch('/api/vaults');
            const vaults = await vaultsResponse.json();
            const vaultConfig = vaults.find(v => v.name === currentVault);

            if (!vaultConfig) {
                throw new Error('Vault not found');
            }

            const command = `${vaultConfig.claude_script} --resume ${task.claude_session_id}`;
            showModal(task.claude_session_id, command, vaultConfig.vault_path);

            // Restore button
            button.textContent = originalText;
            button.disabled = false;
            return;
        }

        // Create new Claude session
        button.textContent = '⏳ Starting...';
        const response = await fetch(`/api/tasks/${taskId}/run?vault=${encodeURIComponent(currentVault)}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(error);
        }

        const data = await response.json();

        // Update task cache with new session_id
        task.claude_session_id = data.session_id;

        // Show session modal with command
        showModal(data.session_id, data.command, data.working_dir);

        // Restore button and update to Resume
        button.textContent = '▶ Resume';
        button.className = 'resume-btn';
        button.disabled = false;

    } catch (error) {
        console.error('Failed to run task:', error);
        alert(`Failed to start session: ${error.message}`);

        // Restore button
        if (event && event.target) {
            event.target.textContent = '▶ Start';
            event.target.disabled = false;
        }
    }
}

function showModal(sessionId, command, workingDir, executedCommand = null, success = null, error = null) {
    document.getElementById('session-id').textContent = sessionId;
    document.getElementById('handoff-command').textContent = command;

    // Update executed command if provided
    if (executedCommand) {
        document.getElementById('executed-command').textContent = executedCommand;
    } else {
        document.getElementById('executed-command').textContent = '/work-on-task';
    }

    // Show success/failure status
    const statusMessage = document.getElementById('status-message');
    if (success === true) {
        statusMessage.textContent = '✓ Command completed successfully';
        statusMessage.style.backgroundColor = '#d4edda';
        statusMessage.style.color = '#155724';
        statusMessage.style.display = 'block';
    } else if (success === false) {
        statusMessage.textContent = '✗ Command failed' + (error ? ': ' + error : '');
        statusMessage.style.backgroundColor = '#f8d7da';
        statusMessage.style.color = '#721c24';
        statusMessage.style.display = 'block';
    } else {
        statusMessage.style.display = 'none';
    }

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

function formatPhase(phase) {
    const phaseNames = {
        'todo': 'Todo',
        'planning': 'Planning',
        'in_progress': 'In Progress',
        'ai_review': 'AI Review',
        'human_review': 'Human Review',
        'done': 'Done'
    };
    return phaseNames[phase] || phase;
}

function formatRelativeTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) {
        return 'just now';
    } else if (diffMins < 60) {
        return `${diffMins}m ago`;
    } else if (diffHours < 24) {
        return `${diffHours}h ago`;
    } else if (diffDays < 7) {
        return `${diffDays}d ago`;
    } else {
        return date.toLocaleDateString();
    }
}

function showTaskMenu(event, taskId) {
    event.stopPropagation();

    // Remove any existing menu
    const existingMenu = document.querySelector('.task-menu');
    if (existingMenu) {
        existingMenu.remove();
    }

    // Create menu
    const menu = document.createElement('div');
    menu.className = 'task-menu';

    // Get task from cache to check if it has a session
    const task = tasksCache[taskId];
    const hasSession = task && task.claude_session_id;

    const menuItems = [];

    // Add Clear Session option if task has a session
    if (hasSession) {
        menuItems.push({ label: 'Clear Session', action: 'clear_session', disabled: false });
    }

    // Add slash command actions
    menuItems.push({ label: 'Complete Task', action: 'complete_task', disabled: false });
    menuItems.push({ label: 'Defer Task', action: 'defer_task', disabled: false });

    // Add phase options
    menuItems.push({ label: 'Move to', action: 'move', disabled: false });
    menuItems.push({ label: 'Error', action: 'error', disabled: true });
    menuItems.push({ label: 'In Progress', action: 'in_progress', disabled: false });
    menuItems.push({ label: 'AI Review', action: 'ai_review', disabled: false });
    menuItems.push({ label: 'Human Review', action: 'human_review', disabled: false });
    menuItems.push({ label: 'Done', action: 'done', disabled: false });

    menuItems.forEach(item => {
        const menuItem = document.createElement('div');
        menuItem.className = 'task-menu-item';
        if (item.disabled) {
            menuItem.classList.add('disabled');
        }
        if (item.label === 'Move to') {
            menuItem.classList.add('header');
        }
        menuItem.textContent = item.label;

        if (!item.disabled && item.action !== 'move') {
            menuItem.addEventListener('click', () => handleMenuAction(taskId, item.action));
        }

        menu.appendChild(menuItem);
    });

    // Position menu
    const button = event.target;
    const rect = button.getBoundingClientRect();
    menu.style.position = 'fixed';
    menu.style.top = `${rect.bottom + 5}px`;
    menu.style.left = `${rect.left - 150}px`; // Menu width is ~160px

    document.body.appendChild(menu);

    // Close menu on click outside
    setTimeout(() => {
        document.addEventListener('click', closeMenu);
    }, 0);
}

function closeMenu() {
    const menu = document.querySelector('.task-menu');
    if (menu) {
        menu.remove();
    }
    document.removeEventListener('click', closeMenu);
}

async function handleMenuAction(taskId, action) {
    if (!currentVault) {
        alert('No vault selected');
        return;
    }

    closeMenu();

    if (action === 'clear_session') {
        await clearTaskSession(taskId);
    } else if (action === 'complete_task' || action === 'defer_task') {
        // Handle slash commands
        await executeSlashCommand(taskId, action);
    } else {
        // Move to phase
        try {
            const response = await fetch(`/api/tasks/${taskId}/phase?vault=${encodeURIComponent(currentVault)}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ phase: action }),
            });

            if (!response.ok) {
                const error = await response.text();
                throw new Error(error);
            }

            await loadTasks();
        } catch (error) {
            console.error('Failed to update task phase:', error);
            alert(`Failed to update task: ${error.message}`);
        }
    }
}

async function executeSlashCommand(taskId, commandType) {
    // Show loading modal
    const loadingModal = document.getElementById('loading-modal');
    loadingModal.classList.remove('hidden');

    // Setup close button handler
    const closeBtn = document.getElementById('close-loading-btn');
    const closeHandler = () => {
        loadingModal.classList.add('hidden');
        closeBtn.removeEventListener('click', closeHandler);
    };
    closeBtn.addEventListener('click', closeHandler);

    try {
        // Map action to slash command
        const commandMap = {
            'complete_task': 'complete-task',
            'defer_task': 'defer-task'
        };
        const slashCommand = commandMap[commandType];

        // Call backend endpoint
        const response = await fetch(
            `/api/tasks/${encodeURIComponent(taskId)}/execute-command?vault=${encodeURIComponent(currentVault)}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: slashCommand }),
            }
        );

        if (!response.ok) {
            throw new Error('Failed to execute command');
        }

        const data = await response.json();

        // Cleanup
        closeBtn.removeEventListener('click', closeHandler);

        // Hide loading modal
        loadingModal.classList.add('hidden');

        // Show modal with resume command and success/error status
        showModal(data.session_id, data.command, data.working_dir, data.executed_command, data.success, data.error);

    } catch (error) {
        // Cleanup
        closeBtn.removeEventListener('click', closeHandler);

        // Hide loading modal
        loadingModal.classList.add('hidden');

        console.error('Error executing slash command:', error);
        alert(`Failed to execute command: ${error.message}`);
    }
}

async function clearTaskSession(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}/session?vault=${encodeURIComponent(currentVault)}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(error);
        }

        // Update cache
        if (tasksCache[taskId]) {
            tasksCache[taskId].claude_session_id = null;
        }

        // Reload tasks to update UI
        await loadTasks();
    } catch (error) {
        console.error('Failed to clear session:', error);
        alert(`Failed to clear session: ${error.message}`);
    }
}

// WebSocket functions for real-time updates
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionStatus(true);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('WebSocket message received:', data);
        handleTaskUpdate(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus(false);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting in 3s...');
        updateConnectionStatus(false);
        setTimeout(connectWebSocket, 3000);  // Auto-reconnect
    };
}

function handleTaskUpdate(data) {
    const { type, task_id, vault } = data;

    // Ignore updates for other vaults
    if (vault !== currentVault) {
        console.log(`Ignoring update for vault ${vault} (current: ${currentVault})`);
        return;
    }

    console.log(`Handling ${type} event for task ${task_id}`);

    switch (type) {
        case 'modified':
        case 'created':
            // Reload all tasks to get updated data
            loadTasks();
            break;
        case 'deleted':
            // Remove task card from UI
            removeTaskCard(task_id);
            break;
        case 'moved':
            // Reload tasks (task renamed)
            loadTasks();
            break;
        default:
            console.warn(`Unknown event type: ${type}`);
    }
}

function removeTaskCard(taskId) {
    // Find and remove the task card from DOM
    const card = document.querySelector(`[data-task-id="${taskId}"]`);
    if (card) {
        card.remove();
        console.log(`Removed task card: ${taskId}`);
    }

    // Remove from cache
    if (tasksCache[taskId]) {
        delete tasksCache[taskId];
    }
}

function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('ws-status');
    if (statusEl) {
        if (connected) {
            statusEl.classList.remove('disconnected');
            statusEl.title = 'WebSocket connected';
        } else {
            statusEl.classList.add('disconnected');
            statusEl.title = 'WebSocket disconnected';
        }
    }
}
