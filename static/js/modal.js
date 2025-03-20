const showLoadingSpinner = (element, title) => {
    element.html(`
        <div class="loading-state">
            <div class="loading-container">
                <div class="text-center">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    ${title ? `<p class="text-muted mb-0">${title}</p>` : ''}
                </div>
            </div>
        </div>
    `);
};

const hideLoadingSpinner = (element) => {
    element.find('.loading-state').remove();
};

const handleFetchError = (error, contentElement) => {
    console.error('Error:', error);
    hideLoadingSpinner(contentElement);
    alert(error.message);
};

const fetchData = async (url, options = {}) => {
    const response = await fetch(url, options);
    if (!response.ok) {
        if (response.status === 403) {
            throw new Error('У вас немає прав для перегляду історії товару');
        }
        throw new Error('Помилка завантаження даних');
    }
    return response.text();
};

// Modal handling functions
const showModal = (modalId, contentElement, fetchUrl, title, onSuccess) => {
    const modal = $(modalId);
    const content = $(contentElement);
    
    showLoadingSpinner(content, title);
    modal.modal('show');
    
    fetchData(fetchUrl)
        .then(data => {
            hideLoadingSpinner(content);
            content.html(data);
            if (onSuccess) onSuccess(data);
        })
        .catch(error => handleFetchError(error, content));
};