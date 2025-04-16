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

function loadPopoverDataForSupplyInfoOnHold(supplyId, popover) {
    const contentDiv = popover.querySelector('.popover-data');
    
    fetch(`/api/supply/${supplyId}/hold-info/`, {
        headers: {
            'X-CSRFToken': csrftoken
        }
    })
    .then(response => response.json())
    .then(data => {
        let html = `<div class="popover-content">`;
        
        // Pre-hold section
        if (data.total_pre_hold > 0) {
            html += `
                <div class="pre-hold-section">
                    <div class="d-flex justify-content-between align-items-center">
                        <strong>Попереднє:</strong>
                        <span class="badge bg-info">${data.total_pre_hold}</span>
                    </div>
                </div>`;
        }
        
        // Holds table
        if (data.holds && data.holds.length > 0) {
            html += `<div class="holds-table-container">`;
            
            // Regular orders
            const regularHolds = data.holds.filter(h => h.type === 'order');
            if (regularHolds.length > 0) {
                html += `
                    <div class="holds-section">
                        <div class="section-header">В замовленнях</div>
                        <table class="holds-table">
                            <tbody>`;
                
                regularHolds.forEach(hold => {
                    html += `
                        <tr>
                            <td>
                                <a href="/orders/${hold.order_id}/${hold.sup_in_order_id}?next=${encodeURIComponent(window.location.pathname)}" 
                                   class="fw-bold"><span class="d-flex align-items-center"><i class="bi bi-box-seam me-1"></i>${hold.order_id}</span></a>
                            </td>
                            <td class="place-name" title="${hold.place_name}">${hold.place_name}</td>
                            <td class="count">
                                <span class="px-2 rounded-2" style="background-color: orange; font-weight: 600;">${hold.count}</span>
                            </td>
                        </tr>`;
                });
                
                html += `</tbody></table></div>`;
            }
            
            // Booked holds
            const bookedHolds = data.holds.filter(h => h.type === 'booked');
            if (bookedHolds.length > 0) {
                html += `
                    <div class="holds-section">
                        <div class="section-header">В бронюваннях</div>
                        <table class="holds-table">
                            <tbody>`;
                
                bookedHolds.forEach(hold => {
                    html += `
                        <tr>
                            <td class="place-name" title="${hold.place_name}">${hold.place_name}</td>
                            <td class="count">
                            <span class="px-2 rounded-2" style="background-color: orange; font-weight: 600;">${hold.count}</span>
                            </td>
                        </tr>`;
                });
                
                html += `</tbody></table></div>`;
            }
            
            html += `</div>`;
        }
        
        html += `</div>`;
        
        contentDiv.innerHTML = html;

        // Add styles for the new elements
        const style = document.createElement('style');
        style.textContent = `
            .custom-popover-container {
                min-width: 280px;
                max-width: 350px;
                padding: 8px;
                font-size: 0.8rem;
            }
            .popover-content {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .pre-hold-section {
                padding: 8px;
                background: #f8f9fa;
                border-radius: 4px;
            }
            .holds-table-container {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .holds-section {
                background: #fff;
            }
            .section-header {
                padding: 4px 4px;
                background: #f1f1f1;
                font-weight: bold;
                border-radius: 4px 4px 0 0;
            }
            .holds-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.8rem;
            }
            .holds-table th {
                text-align: left;
                padding: 6px 8px;
                background: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
                font-weight: 600;
            }
            .holds-table td {
                padding: 6px 8px;
                border-bottom: 1px solid #eee;
            }
            .holds-table tr:last-child td {
                border-bottom: none;
            }
            .order-link {
                color: #495057;
                text-decoration: none;
                font-weight: 500;
            }
            .order-link:hover {
                text-decoration: underline;
            }
            .place-name {
                word-break: break-word;
                line-height: 1.2;
                text-align: left;
                vertical-align: top;
            }
            .count {
                text-align: right;
                white-space: nowrap;
            }
            .count.warning {
                color: #856404;
                background-color: #fff3cd;
                padding: 2px 6px;
                border-radius: 4px;
            }
        `;
        document.head.appendChild(style);
    })
    .catch(error => {
        contentDiv.innerHTML = `
            <div class="text-danger">
                Помилка завантаження даних
            </div>`;
        console.error('Error loading popover data:', error);
    });
}