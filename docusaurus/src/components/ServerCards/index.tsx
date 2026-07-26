import React, { useState, useEffect } from 'react';
import clsx from 'clsx';
import styles from './styles.module.css';
import serverCardsData from '@site/static/assets/server-cards.json';
import { metaForCategory, iconPath, toCategoryId } from '@site/src/categoryMeta';

type ServerCardProps = {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  subcategory?: string;
  tags?: string[];
  workflows?: string[];
  source_path?: string;
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
  const meta = metaForCategory(server.category);
  const categoryId = toCategoryId(server.category);

  // Use external URL if source_path is a full URL, otherwise use local path
  const linkHref = server.source_path && (server.source_path.startsWith('http://') || server.source_path.startsWith('https://'))
    ? server.source_path
    : `/mcp/servers/${server.id}`;

  return (
    <a
      href={linkHref}
      className={styles.serverCardLink}
      style={{ ['--cat' as string]: meta.color }}
    >
      <div className={clsx(styles.serverCard)} data-id={server.id}>
        <div className={styles.serverCardHeader}>
          <div className={styles.serverCardIcon}>
            <span
              className={styles.serverCardIconGlyph}
              style={{
                maskImage: `url(${iconPath(meta.icon)})`,
                WebkitMaskImage: `url(${iconPath(meta.icon)})`,
              }}
              aria-hidden="true"
            />
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

// Read an initial filter value from the URL query string (client-side only).
function initialParam(key: string): string {
  if (typeof window === 'undefined') return '';
  const value = new URLSearchParams(window.location.search).get(key);
  return value ? decodeURIComponent(value) : '';
}

export default function ServerCards(): React.ReactNode {
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [workflowFilter, setWorkflowFilter] = useState('');
  const [sortOption, setSortOption] = useState('name-asc');
  const [filteredServers, setFilteredServers] = useState(serverCardsData.servers);

  // Hydrate filters from URL params (e.g. /servers?category=Data%20%26%20Analytics)
  // so links can deep-link into a pre-filtered view.
  useEffect(() => {
    const cat = initialParam('category');
    const wf = initialParam('workflow');
    if (cat) setCategoryFilter(cat);
    if (wf) setWorkflowFilter(wf);
  }, []);

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

  const hasActiveFilters = Boolean(searchQuery || categoryFilter || workflowFilter);

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
              aria-label="Filter by category"
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
              aria-label="Filter by workflow"
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
              aria-label="Sort servers"
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
        <span>
          Showing <span className={styles.cardStatsCount}>{filteredServers.length}</span> of <span className={styles.cardStatsTotal}>{serverCardsData.servers.length}</span> servers
        </span>
        {hasActiveFilters && (
          <button
            type="button"
            className={styles.cardStatsClear}
            onClick={() => {
              setSearchQuery('');
              setCategoryFilter('');
              setWorkflowFilter('');
            }}
          >
            Clear filters
          </button>
        )}
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
