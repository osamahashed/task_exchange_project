(function(){
  document.addEventListener('DOMContentLoaded', function(){
    if (window.bootstrap) {
      document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function(el){
        new bootstrap.Tooltip(el);
      });
    }

    document.querySelectorAll('.alert').forEach(function(alertEl){
      var dismissDelay = parseInt(alertEl.getAttribute('data-dismiss-ms') || '4000', 10);
      if (isNaN(dismissDelay) || dismissDelay <= 0) {
        dismissDelay = 4000;
      }
      if (window.bootstrap && typeof window.bootstrap.Alert === 'function') {
        var bsAlert = window.bootstrap.Alert.getOrCreateInstance(alertEl);
        setTimeout(function(){
          bsAlert.close();
        }, dismissDelay);
      } else {
        setTimeout(function(){
          alertEl.classList.add('fade');
          alertEl.classList.remove('show');
          setTimeout(function(){
            if (alertEl.parentNode) {
              alertEl.parentNode.removeChild(alertEl);
            }
          }, 150);
        }, dismissDelay);
      }
    });

    var csrfMeta = document.querySelector('meta[name="csrf-token"]');
    var csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';
    if (csrfToken) {
      var originalFetch = window.fetch;
      window.fetch = function(input, init){
        init = init || {};
        var headers = init.headers || {};
        if (!(headers instanceof Headers)) {
          headers = new Headers(headers);
        }
        var method = (init.method || 'GET').toUpperCase();
        if (method !== 'GET' && method !== 'HEAD') {
          if (!headers.has('X-CSRFToken')) {
            headers.set('X-CSRFToken', csrfToken);
          }
          if (!init.credentials) {
            init.credentials = 'same-origin';
          }
        }
        init.headers = headers;
        return originalFetch.call(this, input, init);
      };
    }
  });
})();
