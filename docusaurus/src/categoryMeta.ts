/**
 * Shared category metadata for the server catalog.
 *
 * `id` values match the derived category ids in server-cards.json
 * (lowercase name, non-word chars stripped, spaces -> hyphens).
 * Each `color` is chosen to clear 4.5:1 contrast on white so it can be
 * used directly as chip/label text; light tints are derived at render
 * time with color-mix().
 */

export type CategoryId =
  | 'essential-setup'
  | 'core'
  | 'documentation'
  | 'infrastructure-deployment'
  | 'ai-machine-learning'
  | 'data-analytics'
  | 'developer-tools-support'
  | 'integration-messaging'
  | 'cost-operations'
  | 'healthcare-lifesciences';

export type CategoryMeta = {
  /** Accent color, safe as text on white. */
  color: string;
  /** Feather icon file (in /static/assets/icons). */
  icon: string;
};

export const CATEGORY_META: Record<string, CategoryMeta> = {
  'essential-setup': { color: '#C2410C', icon: 'key' },
  core: { color: '#B7791F', icon: 'zap' },
  documentation: { color: '#0972D3', icon: 'book-open' },
  'infrastructure-deployment': { color: '#6D28D9', icon: 'server' },
  'ai-machine-learning': { color: '#0E7490', icon: 'cpu' },
  'data-analytics': { color: '#9333EA', icon: 'database' },
  'developer-tools-support': { color: '#0F766E', icon: 'tool' },
  'integration-messaging': { color: '#BE185D', icon: 'share-2' },
  'cost-operations': { color: '#15803D', icon: 'dollar-sign' },
  'healthcare-lifesciences': { color: '#BE123C', icon: 'activity' },
};

const FALLBACK: CategoryMeta = { color: '#5F6B7A', icon: 'help-circle' };

/** Turn a human category name into the derived id used across the site. */
export function toCategoryId(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export function metaForCategory(name: string): CategoryMeta {
  return CATEGORY_META[toCategoryId(name)] ?? FALLBACK;
}

/** Absolute (baseUrl-aware) path to a category icon. */
export function iconPath(icon: string): string {
  return `/mcp/assets/icons/${icon}.svg`;
}
