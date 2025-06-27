# Docusaurus Template Modification Guide

## Method 1: CSS-only Padding (Already Implemented)
The `src/css/doc-override.css` file contains padding rules for:
- Document columns (.docItemCol_VOVn)
- Content areas (.theme-doc-item .col)
- Container wrappers (.theme-doc-item .container)
- Article content (.theme-doc-item article)
- Markdown content (.markdown)
- Responsive padding for mobile devices

## Method 2: Component Swizzling

### Step 1: List available components to swizzle
```bash
npm run swizzle @docusaurus/theme-classic -- --list
```

### Step 2: Swizzle the DocItem Layout component
```bash
npm run swizzle @docusaurus/theme-classic DocItem/Layout
```

This creates `src/theme/DocItem/Layout/index.tsx` where you can:
- Add custom padding/margin classes
- Modify the HTML structure
- Add custom wrapper elements

### Step 3: Example customized layout
```tsx
import React from 'react';
import clsx from 'clsx';
import {useWindowSize} from '@docusaurus/theme-common';
import {useDoc} from '@docusaurus/theme-common/internal';
import DocItemPaginator from '@theme/DocItem/Paginator';
import DocVersionBanner from '@theme/DocVersionBanner';
import DocVersionBadge from '@theme/DocVersionBadge';
import DocItemFooter from '@theme/DocItem/Footer';
import DocItemTOC from '@theme/DocItem/TOC';
import DocItemContent from '@theme/DocItem/Content';
import DocBreadcrumbs from '@theme/DocBreadcrumbs';
import type {Props} from '@theme/DocItem/Layout';

import styles from './styles.module.css';

export default function DocItemLayout({children}: Props): JSX.Element {
  const docTOC = useDoc().toc;
  const windowSize = useWindowSize();
  const canRenderTOC = !!(docTOC.length > 0);
  const renderTocDesktop = canRenderTOC && (windowSize === 'desktop' || windowSize === 'ssr');

  return (
    <div className="row">
      <div className={clsx('col', !renderTocDesktop && 'col--12')}>
        <DocVersionBanner />
        <div className={clsx(styles.docItemContainer, 'custom-doc-padding')}>
          <article>
            <DocBreadcrumbs />
            <DocVersionBadge />
            {renderTocDesktop && (
              <div className="col col--3">
                <DocItemTOC />
              </div>
            )}
            <div className={clsx('col', renderTocDesktop && 'col--7')}>
              <DocItemContent>{children}</DocItemContent>
              <DocItemFooter />
            </div>
          </article>
          <DocItemPaginator />
        </div>
      </div>
    </div>
  );
}
```

### Step 4: Create accompanying CSS module
Create `src/theme/DocItem/Layout/styles.module.css`:
```css
.docItemContainer {
  max-width: 720px;
  margin: 0 auto;
  padding: 20px;
}

.customDocPadding {
  padding: 20px;
}

@media (max-width: 768px) {
  .docItemContainer {
    padding: 15px;
  }
}
```

## Method 3: Custom CSS Classes

Add custom classes to your CSS files and use them globally:

```css
/* In custom.css or doc-override.css */
.custom-doc-container {
  max-width: 720px !important;
  margin: 0 auto !important;
  padding: 20px !important;
}

.custom-content-padding {
  padding: 20px !important;
}

.custom-responsive-padding {
  padding: 20px;
}

@media (max-width: 768px) {
  .custom-responsive-padding {
    padding: 15px;
  }
}
```

## Method 4: Using CSS Custom Properties

Define custom properties in `:root` and use them throughout:

```css
:root {
  --doc-content-padding: 20px;
  --doc-content-padding-mobile: 15px;
  --doc-max-width: 720px;
}

.theme-doc-item {
  --ifm-spacing-horizontal: var(--doc-content-padding);
}

@media (max-width: 768px) {
  .theme-doc-item {
    --ifm-spacing-horizontal: var(--doc-content-padding-mobile);
  }
}
```

## Method 5: Plugin-based Approach

Create a custom plugin to inject CSS or modify the theme:

```javascript
// In docusaurus.config.js
module.exports = {
  plugins: [
    function customPaddingPlugin(context, options) {
      return {
        name: 'custom-padding-plugin',
        injectHtmlTags() {
          return {
            headTags: [
              {
                tagName: 'style',
                innerHTML: `
                  .theme-doc-item .col { padding: 20px !important; }
                  @media (max-width: 768px) {
                    .theme-doc-item .col { padding: 15px !important; }
                  }
                `,
              },
            ],
          };
        },
      };
    },
  ],
};
```

## Recommended Approach

1. **Start with CSS-only** (already implemented in your project)
2. **Use component swizzling** if you need structural changes
3. **Create custom CSS classes** for reusable styling
4. **Use CSS custom properties** for consistent theming

The CSS-only approach I've implemented should handle most padding needs. If you need more control over the layout structure, component swizzling is the way to go.
