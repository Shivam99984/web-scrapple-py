document.addEventListener('DOMContentLoaded', function() {
    var previewContainer = document.getElementById('preview-container');
    if (previewContainer) {
        previewContainer.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            var el = e.target;
            // Build a basic CSS selector: tag#id.class1.class2
            var selector = el.tagName.toLowerCase();
            if (el.id) {
                selector += '#' + el.id;
            }
            if (el.className) {
                var classes = el.className.trim().split(/\s+/);
                classes.forEach(function(cls) {
                    selector += '.' + cls;
                });
            }
            // Optional: highlight the selected element
            el.style.outline = "2px solid red";
            // Populate the selector in the form
            var selectorInput = document.getElementById('selector');
            if (selectorInput) {
                selectorInput.value = selector;
            }
        });
    }
});
