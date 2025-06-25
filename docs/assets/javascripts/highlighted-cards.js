/**
 * Make highlighted cards clickable and ensure proper styling
 */
document.addEventListener('DOMContentLoaded', function() {
  // Find all highlighted cards
  const coreCard = document.querySelector('.server-card[data-id="core-mcp-server"]');
  const sampleCard = document.querySelector('.server-card[data-id="sample"]');

  // Apply consistent styling to all highlighted cards
  const highlightedCards = document.querySelectorAll('.highlighted-cards .server-card');
  highlightedCards.forEach(card => {
    card.style.width = '100%';
    card.style.height = 'auto';
    card.style.maxHeight = 'none';
    card.style.padding = '0.5rem 0.4rem 0.3rem 0.4rem';

    // Ensure header is properly aligned
    const header = card.querySelector('.server-card__header');
    if (header) {
      header.style.alignItems = 'center';
      header.style.gap = '0.3rem';
      header.style.marginBottom = '0.2rem';
      header.style.minHeight = '2rem';
      header.style.padding = '0.1rem 0';
    }

    // Ensure icon is properly aligned
    const icon = card.querySelector('.server-card__icon');
    if (icon) {
      icon.style.display = 'flex';
      icon.style.alignItems = 'center';
    }

    // Ensure title text wraps properly
    const title = card.querySelector('.server-card__title');
    if (title) {
      title.style.fontSize = '0.85rem';
      title.style.lineHeight = '1.2';
      title.style.whiteSpace = 'normal';
      title.style.display = '-webkit-box';
      title.style.webkitLineClamp = '2';
      title.style.webkitBoxOrient = 'vertical';
      title.style.maxHeight = '2.4rem';
      title.style.margin = '0.05rem 0';
      title.style.padding = '0.05rem 0';
    }

    // Ensure category has proper padding
    const category = card.querySelector('.server-card__category');
    if (category) {
      category.style.marginTop = '0.1rem';
      category.style.padding = '0.15rem 0.2rem';
    }

    // Ensure description text wraps properly
    const description = card.querySelector('.server-card__description');
    if (description) {
      description.style.wordWrap = 'break-word';
      description.style.overflowWrap = 'break-word';
      description.style.maxHeight = 'none';
      description.style.marginTop = '0.2rem';
      description.style.marginBottom = '0.3rem';
    }

    // Ensure footer has proper padding
    const footer = card.querySelector('.server-card__footer');
    if (footer) {
      footer.style.paddingTop = '0.15rem';
    }
  });

  // Add click event to Core MCP Server card
  if (coreCard) {
    coreCard.style.cursor = 'pointer';
    coreCard.addEventListener('click', function(event) {
      // Don't trigger if they clicked on the existing "Learn More" link
      if (event.target.tagName === 'A' || event.target.parentElement.tagName === 'A') {
        return;
      }
      window.location.href = 'servers/core-mcp-server';
    });
  }

  // Add click event to Sample card
  if (sampleCard) {
    sampleCard.style.cursor = 'pointer';
    sampleCard.addEventListener('click', function(event) {
      // Don't trigger if they clicked on the existing "Learn More" link
      if (event.target.tagName === 'A' || event.target.parentElement.tagName === 'A') {
        return;
      }
      window.location.href = 'samples/mcp-integration-with-kb';
    });
  }
});
