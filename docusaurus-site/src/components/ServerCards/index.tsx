import React, { useState, useEffect, useRef } from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';
import serverCardsData from '@site/static/assets/server-cards.json';

// Add TypeScript declaration for Feather
declare global {
  interface Window {
    feather?: {
      replace: () => void;
    };
  }
}

type ServerCardProps = {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  subcategory?: string;
  tags?: string[];
  workflows?: string[];
};

type CategoryProps = {
  id: string;
  name: string;
  description: string;
  icon: string;
};

type WorkflowProps = {
  id: string;
  name: string;
  description: string;
  icon: string;
};

const ServerCard: React.FC<{ server: ServerCardProps }> = ({ server }) => {
  const categoryId = server.category.toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');

  // Map category to Feather icon name
  const getCategoryIcon = (category: string) => {
    const iconMap: Record<string, string> = {
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
  };

  const categoryIconName = getCategoryIcon(server.category);

  return (
    <a href={`/mcp/servers/${server.id}`} className={styles.serverCardLink}>
      <div className={clsx(styles.serverCard)} data-id={server.id}>
        <div className={styles.serverCardHeader}>
          <div className={styles.serverCardIcon}>
            <i data-feather={categoryIconName} style={{ width: '22px', height: '22px' }}></i>
          </div>
          <div className={styles.serverCardTitleSection}>
            <h3 className={styles.serverCardTitle}>{server.name || 'Unknown Server'}</h3>
            <div className={styles.serverCardTags}>
              <span
                className={clsx(
                  styles.serverCardCategory,
                  styles[`serverCardCategory${categoryId}`]
                )}
                data-category={server.category || ''}
              >
                {server.category || 'Uncategorized'}
              </span>
              {server.workflows?.map((workflow, index) => {
                const workflowData = serverCardsData.workflows.find(w => w.id === workflow);
                // Map workflow IDs to Feather icon names
                const getWorkflowIcon = (workflowId) => {
                  const iconMap = {
                    'vibe-coding': 'code',
                    'conversational': 'message-circle',
                    'autonomous': 'cpu'
                  };
                  return iconMap[workflowId] || 'zap';
                };

                const workflowIconName = getWorkflowIcon(workflow);

                return (
                  <span key={index} className={styles.serverCardWorkflow} data-workflow={workflow}>
                    {workflowData?.name || workflow}
                  </span>
                );
              })}
            </div>
          </div>
        </div>

        <div className={styles.serverCardContent}>
          <p className={styles.serverCardDescription}>
            {server.description || 'No description available'}
          </p>
        </div>
      </div>
    </a>
  );
};

export default function ServerCards(): React.ReactNode {
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [workflowFilter, setWorkflowFilter] = useState('');
  const [sortOption, setSortOption] = useState('name-asc');
  const [filteredServers, setFilteredServers] = useState(serverCardsData.servers);
  const featherInitialized = useRef(false);

  // Initialize Feather icons after component mounts and whenever filtered servers change
  useEffect(() => {
    // Check if feather is available in the global scope
    if (typeof window !== 'undefined' && window.feather) {
      // Replace all feather icons
      window.feather.replace();
      featherInitialized.current = true;
    } else if (!featherInitialized.current) {
      // If feather is not available, try to load it dynamically
      const script = document.createElement('script');
      script.src = 'https://unpkg.com/feather-icons';
      script.async = true;
      script.onload = () => {
        if (window.feather) {
          window.feather.replace();
          featherInitialized.current = true;
        }
      };
      document.body.appendChild(script);
    }
  }, [filteredServers]);

  useEffect(() => {
    // Filter servers based on search query and filters
    const filtered = serverCardsData.servers.filter(server => {
      const matchesSearch = !searchQuery ||
        server.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        server.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (server.tags && server.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase())));

      const matchesCategory = !categoryFilter || server.category === categoryFilter;

      const matchesWorkflow = !workflowFilter ||
        (server.workflows && server.workflows.some(workflow => {
          const workflowData = serverCardsData.workflows.find(w => w.id === workflow);
          return workflowData?.name === workflowFilter;
        }));

      return matchesSearch && matchesCategory && matchesWorkflow;
    });

    // Sort filtered servers
    const [sortField, sortDirection] = sortOption.split('-');
    const sorted = [...filtered].sort((a, b) => {
      let aValue, bValue;

      if (sortField === 'name') {
        aValue = a.name.toLowerCase();
        bValue = b.name.toLowerCase();
      } else if (sortField === 'category') {
        aValue = a.category.toLowerCase();
        bValue = b.category.toLowerCase();
      } else {
        aValue = a[sortField as keyof ServerCardProps] as string || '';
        bValue = b[sortField as keyof ServerCardProps] as string || '';
      }

      return sortDirection === 'asc'
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    });

    setFilteredServers(sorted);
  }, [searchQuery, categoryFilter, workflowFilter, sortOption]);

  return (
    <div className={styles.serverCardsContainer} id="server-cards-container">
      <div className={styles.cardControls}>
        <div className={styles.cardControlsSearch}>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search servers by name, description, or tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search servers"
          />
        </div>

        <div className={styles.cardControlsFilters}>
          <div className={styles.cardControlsFilterGroup}>
            <select
              id="category-filter"
              className={styles.cardControlsSelect}
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="">All Categories</option>
              {serverCardsData.categories.map((category: CategoryProps) => (
                <option key={category.id} value={category.name}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.cardControlsFilterGroup}>
            <select
              id="workflow-filter"
              className={styles.cardControlsSelect}
              value={workflowFilter}
              onChange={(e) => setWorkflowFilter(e.target.value)}
            >
              <option value="">All Workflows</option>
              {serverCardsData.workflows.map((workflow: WorkflowProps) => (
                <option key={workflow.id} value={workflow.name}>
                  {workflow.name}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.cardControlsFilterGroup}>
            <select
              id="sort-select"
              className={styles.cardControlsSelect}
              value={sortOption}
              onChange={(e) => setSortOption(e.target.value)}
            >
              <option value="name-asc">Sort by Name (A-Z)</option>
              <option value="name-desc">Sort by Name (Z-A)</option>
              <option value="category-asc">Sort by Category (A-Z)</option>
              <option value="category-desc">Sort by Category (Z-A)</option>
            </select>
          </div>
        </div>
      </div>

      <div className={styles.cardStats}>
        Showing <span className={styles.cardStatsCount}>{filteredServers.length}</span> of <span className={styles.cardStatsTotal}>{serverCardsData.servers.length}</span> servers
      </div>

      <div className={styles.cardGrid}>
        {filteredServers.length > 0 ? (
          filteredServers.map((server: ServerCardProps) => (
            <ServerCard key={server.id} server={server} />
          ))
        ) : (
          <div className={styles.cardGridEmpty}>
            <div className={styles.cardGridEmptyTitle}>No servers found</div>
            <div className={styles.cardGridEmptyMessage}>Try adjusting your search or filters</div>
          </div>
        )}
      </div>
    </div>
  );
}
