const root = document.documentElement;

// Capture image errors even when they occur before DOMContentLoaded.
document.addEventListener("error", event => {
    const image = event.target;
    if (image instanceof HTMLImageElement && image.dataset.fallback) {
        const fallback = document.createElement("span");
        fallback.className = "image-fallback";
        fallback.textContent = image.dataset.fallback;
        image.replaceWith(fallback);
    }
}, true);

// Read before the stylesheet loads to avoid flashing the wrong saved theme.
try {
    if (localStorage.getItem("library-theme") === "dark") root.dataset.theme = "dark";
} catch {
    // Browser privacy settings may disable storage; the toggle still works.
}

document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("theme-toggle");
    function updateLabel() {
        const next = root.dataset.theme === "dark" ? "light" : "dark";
        toggle.setAttribute("aria-label", `Switch to ${next} mode`);
        toggle.setAttribute("title", `Switch to ${next} mode`);
    }
    updateLabel();
    toggle.hidden = false;
    toggle.addEventListener("click", () => {
        root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
        updateLabel();
        try {
            localStorage.setItem("library-theme", root.dataset.theme);
        } catch {
            // Keep the current page usable when the preference cannot be saved.
        }
    });
});
