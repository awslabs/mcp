import React, { useState, useEffect } from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';
import serverCardsData from '@site/static/assets/server-cards.json';

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

  return (
    <a href={`/mcp/servers/${server.id}`} className={styles.serverCardLink}>
      <div className={clsx(styles.serverCard)} data-id={server.id}>
        <div className={styles.serverCardHeader}>
          <div className={styles.serverCardIcon}>
            <span role="img" aria-label={server.category}>
              {server.icon}
            </span>
          </div>
          <div className={styles.serverCardTitleSection}>
            <h3 className={styles.serverCardTitle}>{server.name || 'Unknown Server'}</h3>
            <span 
              className={clsx(
                styles.serverCardCategory, 
                styles[`serverCardCategory${categoryId}`]
              )} 
              data-category={server.category || ''}
            >
              {server.category || 'Uncategorized'}
            </span>
          </div>
        </div>

        <div className={styles.serverCardContent}>
          <p className={styles.serverCardDescription}>
            {server.description || 'No description available'}
          </p>
        </div>

        <div className={styles.serverCardFooter}>
          <div className={styles.serverCardWorkflows}>
            {server.workflows?.map((workflow, index) => {
              const workflowData = serverCardsData.workflows.find(w => w.id === workflow);
              return (
                <span key={index} className={styles.serverCardWorkflow} data-workflow={workflow}>
                  <span className={styles.serverCardWorkflowIcon}>
                    {workflowData?.icon}
                  </span>
                  {workflowData?.name || workflow}
                </span>
              );
            })}
          </div>
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
