// home.js
// Smoothly scrolls from the landing hero section down to the main content on the home page.

document.addEventListener("DOMContentLoaded", () => {
  const scrollLink = document.querySelector(".scroll-down");
  const mainContent = document.getElementById("main-content");

  if (!scrollLink || !mainContent) {
    return;
  }

  // Scrolls to the main content instead of jumping there via the link's default anchor behavior
  scrollLink.addEventListener("click", (event) => {
    event.preventDefault();
    mainContent.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});
