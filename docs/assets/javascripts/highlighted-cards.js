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
    
    // Ensure header is properly aligned
    const header = card.querySelector('.server-card__header');
    if (header) {
      header.style.alignItems = 'center';
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
    }
    
    // Ensure description text wraps properly
    const description = card.querySelector('.server-card__description');
    if (description) {
      description.style.wordWrap = 'break-word';
      description.style.overflowWrap = 'break-word';
      description.style.maxHeight = 'none';
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
