let tooltipElement = null;

function createTooltip() {
    if (!tooltipElement) {
        tooltipElement = document.createElement('div');
        tooltipElement.className = 'custom-tooltip';
        document.body.appendChild(tooltipElement);
    }
    return tooltipElement;
}

function showTooltip(event, element) {
    const tooltip = createTooltip();
    const content = element.getAttribute('data-tooltip-content');
    
    tooltip.innerHTML = `<div class="tooltip-content">${content}</div>`;
    
    const rect = element.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltipRect.width / 2) + 'px';
    tooltip.style.top = rect.top - tooltipRect.height - 20 + 'px';
    tooltip.style.opacity = '1';
}

function hideTooltip() {
    if (tooltipElement) {
        tooltipElement.style.opacity = '0';
    }
}

// Clean up tooltip when clicking outside
document.addEventListener('click', function(e) {
    if (tooltipElement && !e.target.closest('[data-tooltip-content]')) {
        hideTooltip();
    }
});

// Reposition tooltip on scroll
document.addEventListener('scroll', function() {
    if (tooltipElement && tooltipElement.style.opacity === '1') {
        const element = document.querySelector('[data-tooltip-content]:hover');
        if (element) {
            const rect = element.getBoundingClientRect();
            const tooltipRect = tooltipElement.getBoundingClientRect();
            tooltipElement.style.left = rect.left + (rect.width / 2) - (tooltipRect.width / 2) + 'px';
            tooltipElement.style.top = rect.top - tooltipRect.height - 20 + 'px';
        }
    }
}); 