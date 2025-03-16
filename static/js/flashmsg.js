window.onload = function() {
    setTimeout(function() {
        var flashes = document.getElementsByClassName('flash');
        for (var i = 0; i < flashes.length; i++) {
            flashes[i].style.opacity = '0';
            setTimeout(function(flash) {
                flash.style.display = 'none';
            }, 500, flashes[i]); // Adjust the time to match the transition duration
        }
    }, 5000); // Adjust the duration the flash message should be visible (in milliseconds)
    };