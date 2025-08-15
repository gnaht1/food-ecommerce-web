// Welcome Popup JavaScript functionality
$(document).ready(function () {
    // Constants
    const STORAGE_KEY = 'welcomePopupSettings';
    const ONE_DAY_MS = 24 * 60 * 60 * 1000; // 1 day in milliseconds

    // Get stored popup settings
    function getPopupSettings() {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : null;
    }

    // Save popup settings
    function savePopupSettings(dontShowAgain, timestamp) {
        const settings = {
            dontShowAgain: dontShowAgain,
            lastDismissed: timestamp
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    }

    // Check if popup should be shown
    function shouldShowPopup() {
        const settings = getPopupSettings();

        // First time visitor - show popup
        if (!settings) {
            return true;
        }

        // User chose "Don't show again" - never show
        if (settings.dontShowAgain) {
            return false;
        }

        // Check if enough time has passed (1 day)
        const now = Date.now();
        const timeSinceLastDismissed = now - settings.lastDismissed;

        return timeSinceLastDismissed >= ONE_DAY_MS;
    }

    // Welcome Popup functionality
    function showWelcomePopup() {
        if (shouldShowPopup()) {
            // Delay popup appearance by 1 second for better user experience
            setTimeout(function () {
                $('#welcomePopup').modal('show');
            }, 1000);
        }
    }

    // Handle modal dismissal (when modal is hidden)
    $('#welcomePopup').on('hidden.bs.modal', function () {
        const dontShowAgain = $('#dontShowAgain').is(':checked');
        const timestamp = Date.now();

        savePopupSettings(dontShowAgain, timestamp);
    });

    // Load checkbox state when modal is shown
    $('#welcomePopup').on('show.bs.modal', function () {
        const settings = getPopupSettings();
        if (settings && settings.dontShowAgain) {
            $('#dontShowAgain').prop('checked', true);
        } else {
            $('#dontShowAgain').prop('checked', false);
        }
    });

    // Show popup when page loads
    showWelcomePopup();

    // Optional: Reset localStorage for testing (uncomment if needed)
    // localStorage.removeItem(STORAGE_KEY);
});
