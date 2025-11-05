/**
 * CSRF Token Utilities
 * Утиліти для роботи з CSRF токенами
 */

class CSRFUtils {
    constructor() {
        this.token = null;
        this.init();
    }

    init() {
        // Спробуємо отримати токен з cookies
        this.token = this.getCookie('csrftoken');
        
        // Якщо токен не знайдено, спробуємо отримати з API
        if (!this.token) {
            this.fetchTokenFromAPI();
        }
    }

    getCookie(name) {
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

    async fetchTokenFromAPI() {
        try {
            const response = await fetch('/api/csrf-token/', {
                method: 'GET',
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.token = data.csrfToken;
                console.log('CSRF token fetched from API');
            } else {
                console.warn('Failed to fetch CSRF token from API');
            }
        } catch (error) {
            console.error('Error fetching CSRF token:', error);
        }
    }

    getToken() {
        return this.token;
    }

    async makeRequest(url, options = {}) {
        // Якщо токен відсутній, спробуємо отримати його
        if (!this.token) {
            await this.fetchTokenFromAPI();
        }

        // Додаємо CSRF токен до заголовків
        const headers = {
            'X-CSRFToken': this.token,
            'X-Requested-With': 'XMLHttpRequest',
            ...options.headers
        };

        return fetch(url, {
            ...options,
            headers,
            credentials: 'same-origin'
        });
    }

    async post(url, data, options = {}) {
        return this.makeRequest(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            body: JSON.stringify(data),
            ...options
        });
    }

    async postForm(url, formData, options = {}) {
        return this.makeRequest(url, {
            method: 'POST',
            body: formData,
            ...options
        });
    }
}

// Створюємо глобальний екземпляр
window.csrfUtils = new CSRFUtils();

// Експортуємо для використання в інших модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CSRFUtils;
}






