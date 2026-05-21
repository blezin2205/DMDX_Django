(function (window) {
    'use strict';

    var DEFAULTS = { edit: true, cart: true, precart: true, smn: true };
    var SETTINGS_PANEL_WIDTH = 252;
    var toggleUrl = null;

    function getToggleUrl() {
        if (toggleUrl !== null) {
            return toggleUrl;
        }
        var scope = getScope();
        toggleUrl = (scope && scope.dataset.homeTableDisplayToggleUrl)
            ? scope.dataset.homeTableDisplayToggleUrl
            : '/home_table_display/toggle/';
        return toggleUrl;
    }

    function getCsrfToken() {
        if (typeof csrftoken !== 'undefined' && csrftoken) {
            return csrftoken;
        }
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function normalizeSettings(parsed) {
        return {
            edit: parsed.edit !== false,
            cart: parsed.cart !== false,
            precart: parsed.precart !== false,
            smn: parsed.smn !== false,
        };
    }

    function readSettings() {
        var el = document.getElementById('home-table-display-data');
        if (!el) {
            return Object.assign({}, DEFAULTS);
        }
        try {
            return normalizeSettings(JSON.parse(el.textContent));
        } catch (e) {
            return Object.assign({}, DEFAULTS);
        }
    }

    /** Поточний стан з чекбоксів меню (не з початкового JSON). */
    function readSettingsFromInputs() {
        var settings = readSettings();
        document.querySelectorAll('input[data-home-display]').forEach(function (input) {
            var key = input.getAttribute('data-home-display');
            if (key) {
                settings[key] = input.checked;
            }
        });
        return settings;
    }

    function writeSettingsToDataScript(settings) {
        var el = document.getElementById('home-table-display-data');
        if (el) {
            el.textContent = JSON.stringify(settings);
        }
    }

    function saveSetting(key, value) {
        var body = new URLSearchParams();
        body.set('field', key);
        body.set('value', value ? 'true' : 'false');
        return fetch(getToggleUrl(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken(),
            },
            body: body.toString(),
            credentials: 'same-origin',
        });
    }

    function getScope() {
        return document.querySelector('.home-supply-list-scope');
    }

    function getPageFeatures() {
        var scope = getScope();
        if (!scope) {
            return { edit: true, cart: true, precart: true, smn: true };
        }
        return {
            edit: scope.getAttribute('data-home-feature-edit') !== '0',
            cart: scope.getAttribute('data-home-feature-cart') !== '0',
            precart: scope.getAttribute('data-home-feature-precart') !== '0',
            smn: scope.getAttribute('data-home-feature-smn') !== '0',
        };
    }

    function getRoots() {
        var scope = getScope();
        var roots = [document.documentElement, document.body];
        if (scope) roots.push(scope);
        return roots;
    }

    function syncMenuOptions(features) {
        document.querySelectorAll('[data-home-display-option]').forEach(function (row) {
            var key = row.getAttribute('data-home-display-option');
            var enabled = features[key];
            row.classList.toggle('is-unavailable', !enabled);
            var input = row.querySelector('input[data-home-display]');
            if (input) input.disabled = !enabled;
        });
    }

    function applySettings(settings) {
        var features = getPageFeatures();

        getRoots().forEach(function (root) {
            root.classList.toggle('home-hide-edit', features.edit && !settings.edit);
            root.classList.toggle('home-hide-cart', features.cart && !settings.cart);
            root.classList.toggle('home-hide-precart', features.precart && !settings.precart);
            root.classList.toggle('home-hide-smn', features.smn && !settings.smn);
        });

        document.querySelectorAll('input[data-home-display]').forEach(function (input) {
            var key = input.getAttribute('data-home-display');
            if (key in settings) input.checked = settings[key];
        });

        syncMenuOptions(features);
    }

    function resetPanelStyle(panel) {
        panel.style.position = '';
        panel.style.right = '';
        panel.style.top = '';
        panel.style.left = '';
        panel.style.bottom = '';
        panel.style.margin = '';
        panel.style.zIndex = '';
        panel.style.width = '';
        panel.style.minWidth = '';
        panel.style.maxWidth = '';
    }

    function positionContextPanel(btn, panel, fixedWidth) {
        var pad = 8;
        var gap = 4;
        var rect = btn.getBoundingClientRect();
        var pw = fixedWidth || panel.offsetWidth || SETTINGS_PANEL_WIDTH;
        var ph = panel.offsetHeight;

        panel.style.position = 'fixed';
        panel.style.margin = '0';
        panel.style.right = 'auto';
        panel.style.bottom = 'auto';
        panel.style.zIndex = '1080';
        panel.style.width = pw + 'px';
        panel.style.minWidth = pw + 'px';
        panel.style.maxWidth = pw + 'px';

        var left = rect.right - pw;
        if (left < pad) {
            left = rect.left;
        }
        if (left + pw > window.innerWidth - pad) {
            left = Math.max(pad, window.innerWidth - pw - pad);
        }

        var top = rect.bottom + gap;
        if (ph && top + ph > window.innerHeight - pad && rect.top - ph - gap > pad) {
            top = rect.top - ph - gap;
        }

        panel.style.left = left + 'px';
        panel.style.top = top + 'px';
    }

    function mountSettingsPanel(panel, dropdown) {
        if (panel.parentNode === document.body) {
            return;
        }
        panel._dmdxMount = {
            parent: dropdown,
            next: panel.nextSibling,
        };
        document.body.appendChild(panel);
    }

    function unmountSettingsPanel(panel) {
        var mount = panel._dmdxMount;
        if (!mount || !mount.parent) {
            return;
        }
        if (mount.next && mount.next.parentNode === mount.parent) {
            mount.parent.insertBefore(panel, mount.next);
        } else {
            mount.parent.appendChild(panel);
        }
        panel._dmdxMount = null;
    }

    function getSettingsPanel(dropdown) {
        if (dropdown._dmdxPanel) {
            return dropdown._dmdxPanel;
        }
        var panel = dropdown.querySelector('.home-table-display-panel');
        if (panel) {
            dropdown._dmdxPanel = panel;
        }
        return panel;
    }

    function getPanelTriggerBtn(panel) {
        if (panel._dmdxTriggerBtn) {
            return panel._dmdxTriggerBtn;
        }
        var dropdown = panel.closest('.supply-row-dropdown');
        if (!dropdown) {
            return null;
        }
        return dropdown.querySelector('.supply-row-menu-btn, .home-table-display-menu-btn');
    }

    function closePanel(panel, btn) {
        if (!btn) {
            btn = getPanelTriggerBtn(panel);
        }
        if (panel.classList.contains('home-table-display-panel')) {
            unmountSettingsPanel(panel);
            panel._dmdxTriggerBtn = null;
        }
        resetPanelStyle(panel);
        panel.classList.remove('is-open');
        panel.setAttribute('hidden', '');
        if (btn) btn.setAttribute('aria-expanded', 'false');
    }

    function closeAllContextMenus(exceptPanel) {
        document.querySelectorAll('.supply-row-actions-panel.is-open, .home-table-display-panel.is-open').forEach(function (panel) {
            if (exceptPanel && panel === exceptPanel) return;
            closePanel(panel, getPanelTriggerBtn(panel));
        });
    }

    function openSettingsMenu(btn) {
        var dropdown = btn.closest('.home-table-display-dropdown');
        if (!dropdown) return;
        var panel = getSettingsPanel(dropdown);
        if (!panel) return;

        var willOpen = !panel.classList.contains('is-open');
        closeAllContextMenus(willOpen ? panel : null);

        if (willOpen) {
            applySettings(readSettings());
            mountSettingsPanel(panel, dropdown);
            panel._dmdxTriggerBtn = btn;
            panel.removeAttribute('hidden');
            panel.classList.add('is-open');
            window.requestAnimationFrame(function () {
                positionContextPanel(btn, panel, SETTINGS_PANEL_WIDTH);
            });
            btn.setAttribute('aria-expanded', 'true');
        } else {
            closePanel(panel, btn);
        }
    }

    function onDisplayToggle(input) {
        var key = input.getAttribute('data-home-display');
        if (!key) return;
        var settings = readSettingsFromInputs();
        applySettings(settings);
        saveSetting(key, settings[key]).then(function () {
            writeSettingsToDataScript(settings);
        }).catch(function () {
            input.checked = !input.checked;
            settings = readSettingsFromInputs();
            applySettings(settings);
        });
    }

    function bindEvents() {
        document.addEventListener('change', function (e) {
            if (!e.target.matches('input[data-home-display]')) return;
            onDisplayToggle(e.target);
        });

        document.addEventListener('click', function (e) {
            if (e.target.closest('.home-table-display-panel.is-open')) {
                e.stopPropagation();
            }
        }, true);

        document.addEventListener('click', function (e) {
            var settingsBtn = e.target.closest('.home-table-display-menu-btn');
            if (settingsBtn) {
                e.preventDefault();
                e.stopPropagation();
                openSettingsMenu(settingsBtn);
                return;
            }

            if (e.target.closest('.home-table-display-panel, .home-table-display-dropdown')) {
                return;
            }

            if (!e.target.closest('.supply-row-dropdown')) {
                closeAllContextMenus();
            }
        });

        window.addEventListener('scroll', function () { closeAllContextMenus(); }, true);
        window.addEventListener('resize', function () { closeAllContextMenus(); });
        document.querySelectorAll('.table-responsive').forEach(function (el) {
            el.addEventListener('scroll', function () { closeAllContextMenus(); });
        });
    }

    window.DmdxPositionContextPanel = positionContextPanel;

    window.DmdxHomeTableDisplay = {
        apply: function () { applySettings(readSettings()); },
        closeMenus: closeAllContextMenus,
        positionPanel: positionContextPanel,
    };

    bindEvents();
    applySettings(readSettings());
})(window);
