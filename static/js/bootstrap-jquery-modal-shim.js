/**
 * jQuery $(el).modal('show'|'hide'|'toggle') for Bootstrap 5.
 * Load after jQuery and bootstrap.bundle.min.js. Do not load Bootstrap 4 JS alongside BS5.
 */
(function ($) {
    'use strict';
    if (!$ || typeof bootstrap === 'undefined' || !bootstrap.Modal) {
        return;
    }
    $.fn.modal = function (option) {
        return this.each(function () {
            var instance = bootstrap.Modal.getOrCreateInstance(this);
            if (option === 'show') {
                instance.show();
            } else if (option === 'hide') {
                instance.hide();
            } else if (option === 'toggle') {
                instance.toggle();
            } else if (option === undefined || option === null) {
                instance.show();
            }
        });
    };
})(window.jQuery);
