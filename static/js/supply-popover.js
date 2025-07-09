document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded event fired - initializing popovers');
    
    // Check if Bootstrap is available
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap is not loaded! Make sure bootstrap.bundle.js is included in your page.');
        return;
    }
    
    console.log('Bootstrap version:', bootstrap.Tooltip.VERSION);
    
    // Initialize all popovers
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    console.log(`Found ${popoverTriggerList.length} popover triggers`);
    
    // Keep track of the currently open popover
    let currentOpenPopover = null;
    let isPopoverTransitioning = false;
    
    const popoverList = [...popoverTriggerList].map(popoverTriggerEl => {
        console.log('Initializing popover for element:', popoverTriggerEl);
        console.log('Data attributes:', {
            'data-bs-toggle': popoverTriggerEl.getAttribute('data-bs-toggle'),
            'data-bs-trigger': popoverTriggerEl.getAttribute('data-bs-trigger'),
            'data-bs-placement': popoverTriggerEl.getAttribute('data-bs-placement'),
            'data-bs-html': popoverTriggerEl.getAttribute('data-bs-html'),
            'data-supply-id': popoverTriggerEl.getAttribute('data-supply-id')
        });
        
        const popover = new bootstrap.Popover(popoverTriggerEl, {
            container: 'body',
            html: true,
            trigger: 'click' // Use click trigger to match current behavior
        });
        
        // Add event listener for when popover is shown
        popoverTriggerEl.addEventListener('shown.bs.popover', function() {
            console.log('Popover shown event fired for element:', this);
            
            // If there's already an open popover and it's not this one, close it
            if (currentOpenPopover && currentOpenPopover !== popover) {
                console.log('Closing previously opened popover');
                isPopoverTransitioning = true;
                currentOpenPopover.hide();
                
                // Wait for the first popover to be fully closed before proceeding
                setTimeout(() => {
                    isPopoverTransitioning = false;
                    console.log('Previous popover should be fully closed now');
                    
                    // Now that the previous popover is closed, load the data for the new popover
                    loadPopoverData(this);
                }, 300); // Wait 300ms for the popover to be fully closed
            } else {
                // If no previous popover or it's the same one, load the data immediately
                loadPopoverData(this);
            }
            
            // Set this as the current open popover
            currentOpenPopover = popover;
        });
        
        // Add event listener for when popover is hidden
        popoverTriggerEl.addEventListener('hidden.bs.popover', function() {
            console.log('Popover hidden event fired for element:', this);
            
            // If this is the current open popover, clear the reference
            if (currentOpenPopover === popover) {
                console.log('Clearing current open popover reference');
                currentOpenPopover = null;
            }
        });
        
        return popover;
    });
    
    // Function to load popover data
    function loadPopoverData(triggerElement) {
        const supplyId = triggerElement.getAttribute('data-supply-id');
        console.log('Loading data for supply ID:', supplyId);
        
        // Wait a short time for the popover to be fully rendered in the DOM
        setTimeout(() => {
            // Try different selectors to find the popover element
            let popoverElement = document.querySelector('.popover[data-bs-popper="static"]');
            console.log('Found popover element with .popover[data-bs-popper="static"]:', popoverElement);
            
            if (!popoverElement) {
                // Try alternative selector
                popoverElement = document.querySelector('.popover');
                console.log('Found popover element with .popover:', popoverElement);
            }
            
            if (!popoverElement) {
                // Try finding by class name
                const allPopovers = document.querySelectorAll('.popover');
                console.log('All popovers found:', allPopovers.length);
                if (allPopovers.length > 0) {
                    popoverElement = allPopovers[0];
                    console.log('Using first popover element found');
                }
            }
            
            if (popoverElement) {
                // Try to find the content div
                let contentDiv = popoverElement.querySelector('.popover-data');
                console.log('Found content div:', contentDiv);
                
                if (!contentDiv) {
                    // Try to find the popover body
                    contentDiv = popoverElement.querySelector('.popover-body');
                    console.log('Found popover body:', contentDiv);
                }
                
                if (!contentDiv) {
                    // If still not found, try to find any element that might contain the content
                    console.log('Popover HTML:', popoverElement.innerHTML);
                    
                    // Create a new content div if none exists
                    contentDiv = document.createElement('div');
                    contentDiv.className = 'popover-data';
                    popoverElement.appendChild(contentDiv);
                    console.log('Created new content div');
                }
                
                if (contentDiv) {
                    console.log('Loading data for supply ID:', supplyId);
                    // Load the data
                    loadPopoverDataForSupplyInfoOnHold(supplyId, contentDiv);
                } else {
                    console.error('Could not find or create any suitable element to update with content');
                }
            } else {
                console.error('Popover element not found with any selector');
                // Log all elements with class 'popover'
                const allElements = document.querySelectorAll('*');
                console.log('All elements with class containing "popover":');
                allElements.forEach(el => {
                    if (el.className && el.className.includes('popover')) {
                        console.log(el);
                    }
                });
            }
        }, 100); // Wait 100ms for the popover to be fully rendered
    }
    
    // Handle clicks outside popovers to close them
    document.addEventListener('click', function(e) {
        // If click is not on a popover trigger and not inside a popover
        if (!e.target.closest('[data-bs-toggle="popover"]') && !e.target.closest('.popover')) {
            console.log('Click outside popover detected, hiding all popovers');
            // Hide all popovers
            popoverList.forEach(popover => {
                popover.hide();
            });
            // Clear the current open popover reference
            currentOpenPopover = null;
        }
    });
});

function loadPopoverDataForSupplyInfoOnHold(supplyId, contentDiv) {
    console.log('loadPopoverDataForSupplyInfoOnHold called with supplyId:', supplyId);
    
    // Get CSRF token from cookie
    const csrftoken = getCookie('csrftoken');
    console.log('CSRF token:', csrftoken ? 'Found' : 'Not found');
    
    const apiUrl = `/api/supply/${supplyId}/hold-info/`;
    console.log('Fetching data from:', apiUrl);
    
    // Set a timeout to show mock data if the API doesn't respond quickly
    const timeoutId = setTimeout(() => {
        console.log('API request timed out, showing mock data');
        showMockData(contentDiv, supplyId);
    }, 5000); // 3 second timeout
    
    fetch(apiUrl, {
        headers: {
            'X-CSRFToken': csrftoken
        }
    })
    .then(response => {
        clearTimeout(timeoutId);
        console.log('API response status:', response.status);
        if (!response.ok) {
            throw new Error(`API returned status ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('API data received:', data);
        updatePopoverContent(contentDiv, data);
    })
    .catch(error => {
        clearTimeout(timeoutId);
        console.error('Error loading popover data:', error);
        showMockData(contentDiv, supplyId);
    });
}

// Function to update popover content with API data
function updatePopoverContent(contentDiv, data) {
    let html = `<div class="popover-content">`;
    
    // Header with total count
    html += `
        <div class="d-flex justify-content-between gap-1 mb-2">
            <span class="fw-bold">На утриманні всього:</span>
            <span class="px-2 rounded-2" style="background-color: orange; font-weight: 600;">${data.total_on_hold}</span>
        </div>`;
    
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
                               class="fw-bold" target="_blank"><span class="d-flex align-items-center"><i class="bi bi-box-seam me-1"></i>${hold.order_id}</span></a>
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
                        <td class="place-name">
                        <a href="clientsInfo/${hold.order_id}/booked_supplies_list" target="_blank" class="place-link">${hold.place_name}</a>
                        </td>
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
    
    console.log('Setting content div HTML');
    contentDiv.innerHTML = html;
    console.log('Content div HTML set successfully');

    // Add styles for the new elements
    addPopoverStyles();
}

// Function to show mock data if the API fails
function showMockData(contentDiv, supplyId) {
    console.log('Showing mock data for supply ID:', supplyId);
    
    const mockData = {
        total_on_hold: 5,
        total_pre_hold: 2,
        holds: [
            {
                type: 'order',
                order_id: '12345',
                sup_in_order_id: '67890',
                place_name: 'Медичний центр "Здоров\'я"',
                count: 3
            },
            {
                type: 'booked',
                order_id: '54321',
                place_name: 'Клініка "Довіра"',
                count: 2
            }
        ]
    };
    
    updatePopoverContent(contentDiv, mockData);
    
    // Add a warning message
    const warningDiv = document.createElement('div');
    warningDiv.className = 'alert alert-warning mt-2';
    warningDiv.innerHTML = '<small>Це тестові дані. API недоступний.</small>';
    contentDiv.appendChild(warningDiv);
}

// Function to add styles for the popover
function addPopoverStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .popover {
            min-width: 280px;
            max-width: 350px;
            padding: 4px;
            font-size: 0.8rem;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(0, 0, 0, 0.1);
        }
        .popover-content {
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding: 0;
        }
        .pre-hold-section {
            padding: 4px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .holds-table-container {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .holds-section {
            background: #fff;
        }
        .section-header {
            padding: 2px 4px;
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
            padding: 4px 6px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            font-weight: 600;
        }
        .holds-table td {
            padding: 4px 6px;
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
        .d-flex.justify-content-between.gap-1.mb-2 {
            margin-bottom: 4px !important;
        }
    `;
    document.head.appendChild(style);
    console.log('Styles added to document head');
}

// Helper function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
} 