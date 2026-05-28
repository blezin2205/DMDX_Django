(function () {
    var collapseEl = document.getElementById('preordersAnalyticsBody');
    if (!collapseEl || typeof Chart === 'undefined') return;

    var loadingEl = document.getElementById('poAnalyticsLoading');
    var contentEl = document.getElementById('poAnalyticsContent');
    var errorEl = document.getElementById('poAnalyticsError');
    var filterForm = document.getElementById('preorders-filter-form');
    var charts = [];
    var resizeObservers = [];
    var loadedFingerprint = null;
    var fetchInFlight = false;
    var topProductsData = null;
    var topProductCategories = null;
    var productsResizeObserver = null;

    var pal = { green: '#198754', blue: '#0d6efd', slate: '#6c757d', teal: '#0dcaf0', orange: '#fd7e14', purple: '#6f42c1' };

    function setVisible(el, show) {
        if (el) el.classList.toggle('d-none', !show);
    }

    function destroyCharts() {
        charts.forEach(function (ch) { try { ch.destroy(); } catch (e) {} });
        charts = [];
        resizeObservers.forEach(function (ro) { try { ro.disconnect(); } catch (e) {} });
        resizeObservers = [];
        productsResizeObserver = null;
        topProductsData = null;
        topProductCategories = null;
    }

    function poBadgeTextColor(hex) {
        if (!hex) return '#fff';
        var h = String(hex).toLowerCase();
        if (h === '#ffc107' || h === '#fd7e14') return '#212529';
        return '#fff';
    }

    function filterFingerprint() {
        var method = (collapseEl.getAttribute('data-analytics-method') || 'POST').toUpperCase();
        if (method === 'GET') return window.location.search || '';
        if (!filterForm) return '';
        var skip = /^(csrfmiddlewaretoken|get_archive_preorders|xls_preorder|print_|mark_|set_is_)/;
        var parts = [];
        new FormData(filterForm).forEach(function (value, key) {
            if (skip.test(key)) return;
            parts.push(key + '=' + value);
        });
        parts.sort();
        return parts.join('&');
    }

    function rebuildProductsChart() {
        var tp = topProductsData;
        if (!tp || !tp.labels || !tp.labels.length) return;
        var canvasProd = document.getElementById('poChartProducts');
        var selCat = document.getElementById('poProdCat');
        var selLim = document.getElementById('poProdLimit');
        var prodSizer = document.getElementById('poProductsChartSizer');
        var prodScroll = prodSizer ? prodSizer.closest('.oa-chart-scroll-y') : null;
        if (!canvasProd) return;

        var catVal = selCat ? selCat.value : '';
        var lim = selLim ? parseInt(selLim.value, 10) : 50;
        if (!lim || lim < 1) lim = 50;
        var labelsOut = [];
        var valuesOut = [];
        for (var i = 0; i < tp.labels.length; i++) {
            if (catVal && topProductCategories[i] !== catVal) continue;
            labelsOut.push(tp.labels[i]);
            valuesOut.push(tp.quantities[i]);
            if (labelsOut.length >= lim) break;
        }

        var existing = Chart.getChart(canvasProd);
        if (existing) existing.destroy();

        if (!labelsOut.length) {
            if (prodSizer) prodSizer.style.minHeight = '120px';
            return;
        }
        var nPr = labelsOut.length;
        if (prodSizer) prodSizer.style.minHeight = Math.max(200, nPr * 24 + 56) + 'px';
        var chartProd = new Chart(canvasProd, {
            type: 'bar',
            data: {
                labels: labelsOut,
                datasets: [{ label: 'Одиниць у передзамовленнях', data: valuesOut, backgroundColor: pal.teal }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { precision: 0 } },
                    y: { ticks: { font: { size: nPr > 35 ? 8 : 9 }, maxRotation: 0 } }
                }
            }
        });
        charts.push(chartProd);
        if (prodScroll && typeof ResizeObserver !== 'undefined' && !productsResizeObserver) {
            productsResizeObserver = new ResizeObserver(function () {
                try { chartProd.resize(); } catch (e) {}
            });
            productsResizeObserver.observe(prodScroll);
            resizeObservers.push(productsResizeObserver);
        }
    }

    function renderPreordersAnalytics(data) {
        destroyCharts();
        if (!data) return;

        ['poTopPlacesWrap', 'poTopProductsWrap'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.setAttribute('hidden', 'hidden');
        });
        var leg = document.getElementById('poStatusLegend');
        if (leg) leg.innerHTML = '';

        function setText(id, v) {
            var n = document.getElementById(id);
            if (n) n.textContent = v;
        }
        setText('po-total', String(data.total));
        setText('po-not-archived', String(data.not_archived != null ? data.not_archived : 0));
        setText('po-in-archive', String(data.in_archive != null ? data.in_archive : 0));
        setText('po-completed', String(data.completed));
        setText('po-pending', String(data.pending));
        setText('po-created-by-clients', String(data.created_by_clients != null ? data.created_by_clients : 0));
        setText('po-unique-client-creators', String(data.unique_client_creators != null ? data.unique_client_creators : 0));
        setText('po-with-orders', String(data.with_orders != null ? data.with_orders : 0));
        setText('po-avg-lines', String(data.avg_line_positions));
        var cBM = data.created_by_me != null ? data.created_by_me : 0;
        var dSM = data.date_sent_by_me != null ? data.date_sent_by_me : 0;
        setText('po-created-datesent-me', String(cBM) + '/' + String(dSM));
        setText('po-with-date-sent', String(data.with_date_sent != null ? data.with_date_sent : 0));

        var note = document.getElementById('po-extra-note');
        if (note) note.textContent = data.pinned > 0 ? ('Закріплених у вибірці: ' + data.pinned + '.') : '';

        if (data.status_breakdown && data.status_breakdown.length) {
            var pieLabels = [];
            var pieCounts = [];
            var pieColors = [];
            data.status_breakdown.forEach(function (row) {
                if (leg) {
                    var rowWrap = document.createElement('div');
                    rowWrap.className = 'd-flex align-items-center gap-2 border rounded px-2 py-2 bg-white shadow-sm';
                    var ic = document.createElement('i');
                    ic.className = 'bi ' + row.icon + ' flex-shrink-0';
                    ic.style.color = row.color;
                    ic.style.fontSize = '1.15rem';
                    ic.setAttribute('aria-hidden', 'true');
                    var labEl = document.createElement('span');
                    labEl.className = 'small flex-grow-1';
                    labEl.textContent = row.label;
                    var badge = document.createElement('span');
                    badge.className = 'badge rounded-pill fw-semibold flex-shrink-0';
                    badge.style.backgroundColor = row.color;
                    badge.style.color = poBadgeTextColor(row.color);
                    badge.textContent = String(row.count);
                    rowWrap.appendChild(ic);
                    rowWrap.appendChild(labEl);
                    rowWrap.appendChild(badge);
                    leg.appendChild(rowWrap);
                }
                if (row.count > 0) {
                    pieLabels.push(row.label);
                    pieCounts.push(row.count);
                    pieColors.push(row.color);
                }
            });
            if (pieLabels.length) {
                charts.push(new Chart(document.getElementById('poChartStatuses'), {
                    type: 'doughnut',
                    data: {
                        labels: pieLabels,
                        datasets: [{ data: pieCounts, backgroundColor: pieColors, borderWidth: 1, borderColor: '#fff' }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: { legend: { display: false } },
                        cutout: '52%'
                    }
                }));
            }
        }

        if (data.monthly && data.monthly.labels.length) {
            var monthlySizer = document.getElementById('poMonthlyChartSizer');
            var scrollWrap = monthlySizer ? monthlySizer.closest('.oa-chart-scroll-x') : null;
            var nM = data.monthly.labels.length;
            var pxPerPoint = nM > 48 ? 28 : (nM > 24 ? 32 : 40);
            if (monthlySizer && scrollWrap) {
                var viewW = scrollWrap.getBoundingClientRect().width || scrollWrap.clientWidth || 320;
                monthlySizer.style.minWidth = Math.max(viewW, nM * pxPerPoint) + 'px';
            }
            var chartMo = new Chart(document.getElementById('poChartMonthly'), {
                type: 'line',
                data: {
                    labels: data.monthly.labels,
                    datasets: [{
                        label: 'Передзамовлень',
                        data: data.monthly.counts,
                        borderColor: pal.blue,
                        backgroundColor: 'rgba(13, 110, 253, 0.12)',
                        fill: true,
                        tension: 0.25,
                        pointRadius: nM > 60 ? 2 : 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { maxRotation: 45, minRotation: 0, autoSkip: false, font: { size: nM > 36 ? 9 : 10 } } },
                        y: { ticks: { precision: 0 }, beginAtZero: true }
                    }
                }
            });
            charts.push(chartMo);
            if (monthlySizer && typeof ResizeObserver !== 'undefined') {
                var roM = new ResizeObserver(function () { try { chartMo.resize(); } catch (e) {} });
                roM.observe(monthlySizer);
                resizeObservers.push(roM);
            }
        }

        if (data.meta && data.meta.show_top_places && data.top_places && data.top_places.labels.length) {
            var wrap = document.getElementById('poTopPlacesWrap');
            if (wrap) wrap.removeAttribute('hidden');
            var nPl = data.top_places.labels.length;
            var plSizer = document.getElementById('poPlacesChartSizer');
            if (plSizer) plSizer.style.minHeight = Math.max(200, nPl * 24 + 56) + 'px';
            var plScroll = plSizer ? plSizer.closest('.oa-chart-scroll-y') : null;
            var chartPl = new Chart(document.getElementById('poChartPlaces'), {
                type: 'bar',
                data: {
                    labels: data.top_places.labels,
                    datasets: [{ label: 'Передзамовлень', data: data.top_places.counts, backgroundColor: pal.blue }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { precision: 0 } },
                        y: { ticks: { font: { size: nPl > 35 ? 8 : 9 }, maxRotation: 0 } }
                    }
                }
            });
            charts.push(chartPl);
            if (plScroll && typeof ResizeObserver !== 'undefined') {
                var roPl = new ResizeObserver(function () { try { chartPl.resize(); } catch (e) {} });
                roPl.observe(plScroll);
                resizeObservers.push(roPl);
            }
        }

        var tp = data.top_products;
        if (tp && tp.labels && tp.labels.length) {
            var wrapP = document.getElementById('poTopProductsWrap');
            if (wrapP) wrapP.removeAttribute('hidden');
            topProductsData = tp;
            var catsRaw = tp.categories || [];
            topProductCategories = tp.labels.map(function (_, i) {
                return (catsRaw[i] != null && String(catsRaw[i]).length) ? String(catsRaw[i]) : '—';
            });
            var selCat = document.getElementById('poProdCat');
            var selLim = document.getElementById('poProdLimit');
            if (selCat) {
                selCat.innerHTML = '<option value="">Усі категорії</option>';
                var uniq = {};
                topProductCategories.forEach(function (c) { uniq[c] = true; });
                Object.keys(uniq).sort(function (a, b) { return a.localeCompare(b, 'uk'); }).forEach(function (c) {
                    var opt = document.createElement('option');
                    opt.value = c;
                    opt.textContent = c;
                    selCat.appendChild(opt);
                });
                if (!selCat.dataset.bound) {
                    selCat.addEventListener('change', rebuildProductsChart);
                    selCat.dataset.bound = '1';
                }
            }
            if (selLim && !selLim.dataset.bound) {
                selLim.addEventListener('change', rebuildProductsChart);
                selLim.dataset.bound = '1';
            }
            rebuildProductsChart();
        }
    }

    function loadAnalytics() {
        var fingerprint = filterFingerprint();
        if (loadedFingerprint === fingerprint || fetchInFlight) return;

        var url = collapseEl.getAttribute('data-analytics-url');
        var method = (collapseEl.getAttribute('data-analytics-method') || 'POST').toUpperCase();
        if (!url) return;

        fetchInFlight = true;
        setVisible(loadingEl, true);
        setVisible(errorEl, false);
        setVisible(contentEl, false);

        var options = { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } };

        if (method === 'GET') {
            fetch(url + (window.location.search || ''), Object.assign({ method: 'GET' }, options))
                .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
                .then(function (data) {
                    loadedFingerprint = fingerprint;
                    renderPreordersAnalytics(data);
                    setVisible(contentEl, true);
                })
                .catch(function () { loadedFingerprint = null; setVisible(errorEl, true); })
                .finally(function () { fetchInFlight = false; setVisible(loadingEl, false); });
            return;
        }

        if (!filterForm) {
            fetchInFlight = false;
            setVisible(loadingEl, false);
            return;
        }

        var fd = new FormData(filterForm);
        var csrf = filterForm.querySelector('[name=csrfmiddlewaretoken]');
        options.method = 'POST';
        options.body = fd;
        if (csrf) options.headers['X-CSRFToken'] = csrf.value;

        fetch(url, options)
            .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
            .then(function (data) {
                loadedFingerprint = fingerprint;
                renderPreordersAnalytics(data);
                setVisible(contentEl, true);
            })
            .catch(function () { loadedFingerprint = null; setVisible(errorEl, true); })
            .finally(function () { fetchInFlight = false; setVisible(loadingEl, false); });
    }

    collapseEl.addEventListener('shown.bs.collapse', loadAnalytics);
})();
