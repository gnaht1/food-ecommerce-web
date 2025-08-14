// Welcome Popup JavaScript functionality
$(document).ready(function () {
    // Welcome Popup functionality
    function showWelcomePopup() {
        // Check if user has opted not to see this popup again
        if (!localStorage.getItem('dontShowWelcomePopup')) {
            // Delay popup appearance by 1 second for better user experience
            setTimeout(function () {
                $('#welcomePopup').modal('show');
            }, 1000);
        }
    }

    // Handle "Don't show again" checkbox
    $('#dontShowAgain').on('change', function () {
        if ($(this).is(':checked')) {
            localStorage.setItem('dontShowWelcomePopup', 'true');
        } else {
            localStorage.removeItem('dontShowWelcomePopup');
        }
    });

    // Show popup when page loads
    showWelcomePopup();

    // You can also manually trigger the popup by calling:
    // $('#welcomePopup').modal('show');

    // Optional: Reset localStorage for testing (uncomment if needed)
    // localStorage.removeItem('dontShowWelcomePopup');
});
