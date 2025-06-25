/**
 * AWS MCP Server Card Grid - Simplified Implementation
 * Beautiful two-column grid of cards with filtering and sorting
 * Direct DOM manipulation without List.js dependency
 */

(function() {
  'use strict';

  // ==========================================================================
  // State Management
  // ==========================================================================

  const CardGridState = {
    search: '',
    filters: {
      category: '',
      workflow: '',
      subcategory: ''
    },
    sort: { field: 'name', direction: 'asc' },
    data: null,
    allCards: []
  };

  // ==========================================================================
  // Utility Functions
  // ==========================================================================

  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  function slugify(text) {
    return text.toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/[\s_-]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  function getCategoryId(category) {
    const categoryMap = {
      'Documentation': 'documentation',
      'Infrastructure & Deployment': 'infrastructure-deployment',
      'AI & Machine Learning': 'ai-ml',
      'Data & Analytics': 'data-analytics',
      'Developer Tools & Support': 'developer-tools',
      'Integration & Messaging': 'integration-messaging',
      'Cost & Operations': 'cost-operations',
      'Core': 'core'
    };
    return categoryMap[category] || slugify(category);
  }

  function getCategoryIcon(category) {
    const iconMap = {
      'Documentation': 'book-open',
      'Infrastructure & Deployment': 'server',
      'AI & Machine Learning': 'cpu',
      'Data & Analytics': 'database',
      'Developer Tools & Support': 'tool',
      'Integration & Messaging': 'share-2',
      'Cost & Operations': 'dollar-sign',
      'Core': 'zap'
    };
    return iconMap[category] || 'help-circle';
  }

  function getWorkflowIcon(workflowId) {
    const iconMap = {
      'vibe-coding': 'code',
      'conversational': 'message-circle',
      'autonomous': 'cpu'
    };
    return iconMap[workflowId] || 'zap';
  }

  // ==========================================================================
  // URL State Management
  // ==========================================================================

  function getStateFromURL() {
    const params = new URLSearchParams(window.location.search);
    return {
      search: params.get('search') || '',
      filters: {
        category: params.get('category') || '',
        workflow: params.get('workflow') || '',
        subcategory: params.get('subcategory') || ''
      },
      sort: {
        field: params.get('sortField') || 'name',
        direction: params.get('sortDir') || 'asc'
      }
    };
  }

  function updateURL(state) {
    const params = new URLSearchParams();

    if (state.search) params.set('search', state.search);
    if (state.filters.category) params.set('category', state.filters.category);
    if (state.filters.workflow) params.set('workflow', state.filters.workflow);
    if (state.filters.subcategory) params.set('subcategory', state.filters.subcategory);
    if (state.sort.field !== 'name') params.set('sortField', state.sort.field);
    if (state.sort.direction !== 'asc') params.set('sortDir', state.sort.direction);

    const newURL = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
    window.history.replaceState({}, '', newURL);
  }

  const debouncedUpdateURL = debounce(updateURL, 500);

  // ==========================================================================
  // Template Generation
  // ==========================================================================

  function createCardHTML(server) {
    try {
      logDebug(`Creating card HTML for server: ${server.id}`);

      const categoryId = getCategoryId(server.category);
      const categoryIcon = getCategoryIcon(server.category);

      // Safely get workflow tags
      let workflowTags = '';
      try {
        if (server.workflows && Array.isArray(server.workflows)) {
          workflowTags = server.workflows.map(workflow => {
            try {
              // Safe workflow name lookup
              const workflowName = CardGridState.data?.workflows?.find?.(w => w.id === workflow)?.name || workflow;
              const workflowIconName = getWorkflowIcon(workflow);
              return `
                <span class="server-card__workflow" data-workflow="${workflow}">
                  <span class="server-card__workflow-icon">
                    <i data-feather="${workflowIconName}" width="12" height="12"></i>
                  </span>
                  ${workflowName}
                </span>
              `;
            } catch (e) {
              logDebug(`Error creating workflow tag for ${workflow}`, e);
              return '';
            }
          }).join('');
        }
      } catch (e) {
        logDebug('Error creating workflow tags', e);
      }

      // Safely get tags (we're hiding these now)
      let tagsHtml = '';
      try {
        if (server.tags && Array.isArray(server.tags)) {
          tagsHtml = server.tags.slice(0, 6).map(tag =>
            `<span class="server-card__tag" data-tag="${tag}">${tag}</span>`
          ).join('');
        }
      } catch (e) {
        logDebug('Error creating tags', e);
      }

      // Create HTML structure with aligned text and reduced padding
      return `
        <a href="servers/${server.id}" class="server-card-link" style="text-decoration: none; color: inherit; display: block; width: 100%;">
        <div class="server-card" data-id="${server.id}" style="cursor: pointer; width: 100%; height: 200px; box-shadow: none; padding: 0.8rem 0.4rem 0.3rem 0.5rem;">
          <div class="server-card__header" style="align-items: center; gap: 0.3rem; margin-bottom: 0.2rem; min-height: 2rem; padding: 0.1rem 0;">
            <div class="server-card__icon" style="display: flex; align-items: center;">
              <i data-feather="${categoryIcon}" width="22" height="22"></i>
            </div>
            <div class="server-card__title-section" style="display: flex; flex-direction: column; justify-content: center;">
              <h3 class="server-card__title name" style="white-space: normal; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; margin: 0.05rem 0; padding: 0.05rem 0;">${server.name || 'Unknown Server'}</h3>
              <span class="server-card__category server-card__category--${categoryId} category" data-category="${server.category || ''}" style="margin-top: 0.1rem; padding: 0.15rem 0.2rem;">
                ${server.category || 'Uncategorized'}
              </span>
            </div>
          </div>

          <div class="server-card__content">
            <p class="server-card__description description" style="word-wrap: break-word; overflow-wrap: break-word; margin-top: 0.2rem; margin-bottom: 0.3rem; padding: 0.5rem 0.4rem 0.3rem 0.5rem;">${server.description || 'No description available'}</p>
          </div>

          <div class="server-card__footer" style="padding-top: 0.15rem;">
            <div class="server-card__workflows">
              ${workflowTags}
            </div>
          </div>

          <!-- Hidden fields for search -->
          <div style="display: none;">
            <span class="tags">${Array.isArray(server.tags) ? server.tags.join(' ') : ''}</span>
            <span class="workflows">${Array.isArray(server.workflows) ? server.workflows.join(' ') : ''}</span>
            <span class="subcategory" data-subcategory="${server.subcategory || ''}">${server.subcategory || ''}</span>
          </div>
        </div>
        </a>
      `;
    } catch (error) {
      logDebug(`Error creating card HTML for server: ${server?.id || 'unknown'}`, error);
      return `
        <div class="server-card server-card--error">
          <div class="server-card__header">
            <h3 class="server-card__title">Error Rendering Card</h3>
          </div>
          <div class="server-card__content">
            <p>There was a problem displaying this server. Please refresh the page.</p>
          </div>
        </div>
      `;
    }
  }

  // ==========================================================================
  // Data Loading and Processing
  // ==========================================================================

  // Debug function
  function logDebug(message, data) {
    console.log(`[CardGrid] ${message}`, data || '');
  }

  // Try to load data from the document first (in case it's embedded)
  function getEmbeddedData() {
    try {
      const dataScript = document.getElementById('server-cards-data');
      if (dataScript) {
        logDebug('Found embedded data');
        return JSON.parse(dataScript.textContent);
      }
    } catch (e) {
      logDebug('Error parsing embedded data', e);
    }
    return null;
  }

  async function loadServerData() {
    try {
      // Check for embedded data first
      const embeddedData = getEmbeddedData();
      if (embeddedData) {
        logDebug('Using embedded data');
        return embeddedData;
      }

      // Use the known working path directly
      logDebug('No embedded data, fetching from file...');
      const path = '/mcp/assets/server-cards.json';

      logDebug(`Loading server data from: ${path}`);
      const response = await fetch(path);

      if (!response.ok) {
        throw new Error(`Failed to load server data from ${path}: ${response.status} ${response.statusText}`);
      }

      logDebug('Server data loaded successfully');
      const data = await response.json();
      CardGridState.data = data;
      return data;
    } catch (error) {
      console.error('Failed to load server data:', error);
      showError('Failed to load server data. Please refresh the page.');
      return null;
    }
  }

  // ==========================================================================
  // UI Components
  // ==========================================================================

  function createControlsHTML(data) {
    const categories = ['', ...data.categories.map(c => c.name)];
    const workflows = ['', ...data.workflows.map(w => w.name)];

    const categoryOptions = categories.map(cat =>
      `<option value="${cat}">${cat || 'All Categories'}</option>`
    ).join('');

    const workflowOptions = workflows.map(workflow =>
      `<option value="${workflow}">${workflow || 'All Workflows'}</option>`
    ).join('');

    return `
      <div class="card-controls">
        <div class="card-controls__search">
          <input type="text"
                 class="search-input"
                 placeholder="Search servers by name, description, or tags..."
                 autocomplete="off"
                 aria-label="Search servers">
        </div>

        <div class="card-controls__filters" style="display: flex; flex-direction: row; justify-content: space-between; margin-top: 1rem;">
          <div class="card-controls__filter-group" style="width: 30%;">
            <select id="category-filter" class="card-controls__select category-filter">
              ${categoryOptions}
            </select>
          </div>

          <div class="card-controls__filter-group" style="width: 30%;">
            <select id="workflow-filter" class="card-controls__select workflow-filter">
              ${workflowOptions}
            </select>
          </div>

          <div class="card-controls__filter-group" style="width: 30%;">
            <select id="sort-select" class="card-controls__select sort-select">
              <option value="name-asc">Sort by Name (A-Z)</option>
              <option value="name-desc">Sort by Name (Z-A)</option>
              <option value="category-asc">Sort by Category (A-Z)</option>
              <option value="category-desc">Sort by Category (Z-A)</option>
            </select>
          </div>
        </div>
      </div>
    `;
  }

  function createStatsHTML() {
    return `
      <div class="card-stats">
        Showing <span class="card-stats__count">0</span> of <span class="card-stats__total">0</span> servers
      </div>
    `;
  }

  function showError(message) {
    const container = document.getElementById('server-cards-container');
    if (container) {
      container.innerHTML = `
        <div class="card-grid__empty">
          <div class="card-grid__empty-title">Error</div>
          <div class="card-grid__empty-message">${message}</div>
        </div>
      `;
    }
  }

  function showLoading() {
    const gridElement = document.querySelector('.card-grid');
    if (gridElement) {
      gridElement.classList.add('card-grid--loading');
      gridElement.innerHTML = `
        <div class="card-grid__loading">
          Loading servers...
        </div>
      `;
    }
  }

  // ==========================================================================
  // List.js Integration
  // ==========================================================================

  function initializeGrid(data) {
    try {
      logDebug('Starting to initialize grid');
      const container = document.getElementById('server-cards-container');
      if (!container) {
        logDebug('Container not found!');
        return null;
      }

      logDebug('Creating HTML structure');
      // First, create the controls and stats containers
      container.innerHTML = `
        ${createControlsHTML(data)}
        ${createStatsHTML()}
        <div class="card-grid list"></div>
      `;

      // Get reference to the list container
      const listContainer = container.querySelector('.card-grid');
      if (!listContainer) {
        logDebug('List container not found!');
        return null;
      }

      logDebug('Creating direct DOM manipulation for cards');

      try {
        // Render all cards directly
        const cardGrid = container.querySelector('.card-grid');
        if (!cardGrid) {
          logDebug('Card grid container not found');
          return null;
        }

        // Render each server card
        data.servers.forEach(server => {
          const cardHtml = createCardHTML(server);
          const tempDiv = document.createElement('div');
          tempDiv.innerHTML = cardHtml;
          const cardElement = tempDiv.firstElementChild;
          cardGrid.appendChild(cardElement);
        });

        logDebug('Cards created successfully');

        // Store the original card elements for filtering
        const allCards = Array.from(cardGrid.querySelectorAll('.server-card'));
        CardGridState.allCards = allCards;

        return true;
      } catch (error) {
        logDebug('Error creating card grid', error);
        showError('Failed to initialize card grid. Please refresh the page.');
        return null;
      }
    } catch (error) {
      logDebug('Error initializing grid', error);
      showError('Failed to initialize card grid. Please refresh the page.');
      return null;
    }
  }

  // ==========================================================================
  // Event Handlers
  // ==========================================================================

  function setupEventListeners() {
    const container = document.getElementById('server-cards-container');
    if (!container) return;

    // Search input
    const searchInput = container.querySelector('.search-input');
    if (searchInput) {
      searchInput.addEventListener('input', handleSearch);
    }

    // Filter selects
    const categoryFilter = container.querySelector('.category-filter');
    const workflowFilter = container.querySelector('.workflow-filter');
    const sortSelect = container.querySelector('.sort-select');

    if (categoryFilter) {
      categoryFilter.addEventListener('change', handleCategoryFilter);
    }

    if (workflowFilter) {
      workflowFilter.addEventListener('change', handleWorkflowFilter);
    }

    if (sortSelect) {
      sortSelect.addEventListener('change', handleSort);
    }

    // Initial update of stats
    updateStats();
  }

  function handleSearch(event) {
    const query = event.target.value.trim();
    CardGridState.search = query;

    // Direct filtering without using List.js
    filterCards(query, CardGridState.filters.category, CardGridState.filters.workflow);
    debouncedUpdateURL(CardGridState);
  }

  function handleCategoryFilter(event) {
    const category = event.target.value;
    CardGridState.filters.category = category;
    applyFilters();
    debouncedUpdateURL(CardGridState);
  }

  function handleWorkflowFilter(event) {
    const workflowName = event.target.value;
    CardGridState.filters.workflow = workflowName;
    applyFilters();
    debouncedUpdateURL(CardGridState);
  }

  // Sort cards by field and direction
  function sortCards(field, direction) {
    if (!CardGridState.allCards || !CardGridState.allCards.length) return;

    const cardGrid = document.querySelector('.card-grid');
    if (!cardGrid) return;

    // Convert NodeList to array for sorting
    const sortedCards = Array.from(CardGridState.allCards);

  // Sort cards based on field and direction
  sortedCards.sort((a, b) => {
    let aValue, bValue;

    // Handle different field types correctly
    if (field === 'name') {
      aValue = a.querySelector('.server-card__title')?.textContent.trim().toLowerCase() || '';
      bValue = b.querySelector('.server-card__title')?.textContent.trim().toLowerCase() || '';
    } else if (field === 'category') {
      aValue = a.querySelector('.server-card__category')?.textContent.trim().toLowerCase() || '';
      bValue = b.querySelector('.server-card__category')?.textContent.trim().toLowerCase() || '';
    } else {
      // Fallback for other fields
      aValue = a.querySelector(`.${field}`)?.textContent.trim().toLowerCase() || '';
      bValue = b.querySelector(`.${field}`)?.textContent.trim().toLowerCase() || '';
    }

    if (direction === 'asc') {
      return aValue.localeCompare(bValue);
    } else {
      return bValue.localeCompare(aValue);
    }
  });

  // Clear the grid first
  while (cardGrid.firstChild) {
    cardGrid.removeChild(cardGrid.firstChild);
  }

  // Re-append sorted cards to the grid
  sortedCards.forEach(card => {
    // Check if the card is a direct child or wrapped in an anchor
    const parent = card.parentElement;
    if (parent && parent.classList.contains('server-card-link')) {
      // If wrapped in an anchor, append the anchor
      cardGrid.appendChild(parent);
    } else {
      // Otherwise append the card directly
      cardGrid.appendChild(card);
    }
  });
  }

  function handleSort(event) {
    const [field, direction] = event.target.value.split('-');
    CardGridState.sort = { field, direction };

    sortCards(field, direction);
    debouncedUpdateURL(CardGridState);
  }

  // Filter cards based on search query and selected filters
  function filterCards(searchQuery, categoryFilter, workflowFilter) {
    if (!CardGridState.allCards) return;

    const lowercaseQuery = searchQuery.toLowerCase();
    const cardGrid = document.querySelector('.card-grid');
    if (!cardGrid) return;

    // First, determine which cards match the filters
    const visibleCards = [];
    const hiddenCards = [];

    CardGridState.allCards.forEach(card => {
      // Check if card matches search query
      const name = card.querySelector('.name')?.textContent || '';
      const description = card.querySelector('.description')?.textContent || '';
      const tags = card.querySelector('.tags')?.textContent || '';

      const matchesSearch = !searchQuery ||
        name.toLowerCase().includes(lowercaseQuery) ||
        description.toLowerCase().includes(lowercaseQuery) ||
        tags.toLowerCase().includes(lowercaseQuery);

      // Check if card matches category filter
      const category = card.querySelector('.category')?.textContent.trim() || '';
      const matchesCategory = !categoryFilter || category === categoryFilter;

      // Check if card matches workflow filter
      const workflows = card.querySelector('.workflows')?.textContent || '';

      // Find the workflow ID that corresponds to the selected workflow name
      let workflowId = '';
      if (workflowFilter && CardGridState.data && CardGridState.data.workflows) {
        const workflow = CardGridState.data.workflows.find(w => w.name === workflowFilter);
        if (workflow) {
          workflowId = workflow.id;
        }
      }

      const matchesWorkflow = !workflowFilter || workflows.includes(workflowId);

      // Add to appropriate array based on filter matches
      if (matchesSearch && matchesCategory && matchesWorkflow) {
        visibleCards.push(card);
      } else {
        hiddenCards.push(card);
      }
    });

    // Clear the grid
    while (cardGrid.firstChild) {
      cardGrid.removeChild(cardGrid.firstChild);
    }

    // Add visible cards back to the grid
    visibleCards.forEach(card => {
      // Check if the card is a direct child or wrapped in an anchor
      const parent = card.parentElement;
      if (parent && parent.classList.contains('server-card-link')) {
        // If wrapped in an anchor, append the anchor
        cardGrid.appendChild(parent);
      } else {
        // Otherwise append the card directly
        cardGrid.appendChild(card);
      }
    });

    // Update stats
    updateStats();
  }

  // Apply filters helper function
  function applyFilters() {
    filterCards(CardGridState.search, CardGridState.filters.category, CardGridState.filters.workflow);
  }

  function updateStats() {
    const statsElement = document.querySelector('.card-stats__count');
    const totalElement = document.querySelector('.card-stats__total');

    if (statsElement && totalElement && CardGridState.allCards) {
      const visibleCount = CardGridState.allCards.filter(card =>
        card.style.display !== 'none'
      ).length;
      const totalCount = CardGridState.allCards.length;

      statsElement.textContent = visibleCount;
      totalElement.textContent = totalCount;
    }
  }

  // ==========================================================================
  // State Restoration
  // ==========================================================================

  function restoreState() {
    const urlState = getStateFromURL();
    Object.assign(CardGridState, urlState);

    // Restore search
    const searchInput = document.querySelector('.search-input');
    if (searchInput && CardGridState.search) {
      searchInput.value = CardGridState.search;
      filterCards(CardGridState.search, CardGridState.filters.category, CardGridState.filters.workflow);
    }

    // Restore filters
    const categoryFilter = document.querySelector('.category-filter');
    const workflowFilter = document.querySelector('.workflow-filter');
    const sortSelect = document.querySelector('.sort-select');

    if (categoryFilter && CardGridState.filters.category) {
      categoryFilter.value = CardGridState.filters.category;
    }

    if (workflowFilter && CardGridState.filters.workflow) {
      workflowFilter.value = CardGridState.filters.workflow;
    }

    if (sortSelect) {
      const sortValue = `${CardGridState.sort.field}-${CardGridState.sort.direction}`;
      sortSelect.value = sortValue;
    }

    // Apply filters and sort
    applyFilters();
    if (CardGridState.sort.field !== 'name') {
      sortCards(CardGridState.sort.field, CardGridState.sort.direction);
    }
  }

  // ==========================================================================
  // Main Initialization
  // ==========================================================================

  async function initializeCardGrid() {
    // Clean up any existing instances
    if (window.cardGridCleanup) {
      window.cardGridCleanup.forEach(fn => fn());
    }
    window.cardGridCleanup = [];

    const container = document.getElementById('server-cards-container');
    if (!container) return;

    showLoading();

    try {
      // Load data
      const data = await loadServerData();
      if (!data) return;

      // Initialize Grid
      if (!initializeGrid(data)) return;

      // Setup event listeners
      setupEventListeners();

      // Restore state from URL
      restoreState();

      // Initial stats update
      updateStats();

      console.log('Card grid initialized successfully');

    } catch (error) {
      console.error('Failed to initialize card grid:', error);
      showError('Failed to initialize card grid. Please refresh the page.');
    }
  }

  // ==========================================================================
  // MkDocs Material Integration
  // ==========================================================================

  // Safe initialization for MkDocs Material instant loading
  if (typeof document$ !== 'undefined') {
    document$.subscribe(function() {
      // Wait for DOM to be ready
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeCardGrid);
      } else {
        initializeCardGrid();
      }
    });
  } else {
    // Fallback for environments without document$ observable
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initializeCardGrid);
    } else {
      initializeCardGrid();
    }
  }

  // Export for debugging (development only)
  if (typeof window !== 'undefined') {
    window.CardGrid = {
      state: CardGridState,
      reinitialize: initializeCardGrid
    };
  }

})();
