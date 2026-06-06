document.addEventListener("DOMContentLoaded", () => {
  const scrollLink = document.querySelector(".scroll-down");
  const mainContent = document.getElementById("main-content");

  if (!scrollLink || !mainContent) {
    return;
  }

  scrollLink.addEventListener("click", (event) => {
    event.preventDefault();
    mainContent.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});
