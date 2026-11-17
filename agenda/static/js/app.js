document.addEventListener("DOMContentLoaded", () => {
  const root = document.documentElement;
  const themeToggle = document.getElementById("themeToggle");
  const setTheme = (theme) => {
    root.dataset.theme = theme;
    try { localStorage.setItem("agenda-ifal-theme", theme); } catch (_) { /* Theme still works for this page. */ }
    if (themeToggle) {
      const dark = theme === "dark";
      themeToggle.setAttribute("aria-label", dark ? "Ativar modo claro" : "Ativar modo escuro");
      themeToggle.setAttribute("aria-pressed", String(dark));
      themeToggle.title = dark ? "Ativar modo claro" : "Ativar modo escuro";
    }
  };
  setTheme(root.dataset.theme === "dark" ? "dark" : "light");
  themeToggle?.addEventListener("click", () => setTheme(root.dataset.theme === "dark" ? "light" : "dark"));

  const menuToggle = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  const closeMenu = () => {
    sidebar?.classList.remove("sidebar-open");
    backdrop?.classList.remove("backdrop-visible");
    menuToggle?.setAttribute("aria-expanded", "false");
    document.body.classList.remove("menu-is-open");
  };
  const openMenu = () => {
    sidebar?.classList.add("sidebar-open");
    backdrop?.classList.add("backdrop-visible");
    menuToggle?.setAttribute("aria-expanded", "true");
    document.body.classList.add("menu-is-open");
  };
  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", () => sidebar.classList.contains("sidebar-open") ? closeMenu() : openMenu());
    backdrop?.addEventListener("click", closeMenu);
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeMenu(); });
    sidebar.querySelectorAll(".nav-link").forEach((link) => link.addEventListener("click", () => {
      if (window.innerWidth <= 900) closeMenu();
    }));
    window.addEventListener("resize", () => { if (window.innerWidth > 900) closeMenu(); });
  }

  document.querySelectorAll(".flash-close").forEach((button) => {
    button.addEventListener("click", () => button.closest(".flash")?.remove());
  });

  const roleSelect = document.getElementById("role");
  const classField = document.getElementById("classField");
  const updateClassField = () => {
    if (roleSelect && classField) classField.style.display = roleSelect.value === "student" ? "block" : "none";
  };
  if (roleSelect && classField) {
    roleSelect.addEventListener("change", updateClassField);
    updateClassField();
  }

  const photoInput = document.getElementById("profile_photo");
  const photoPreview = document.getElementById("profilePhotoPreview");
  if (photoInput && photoPreview) {
    photoInput.addEventListener("change", () => {
      const file = photoInput.files?.[0];
      if (!file) return;
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        photoInput.value = "";
        window.alert("Escolha uma imagem JPG, PNG ou WEBP.");
        return;
      }
      if (file.size > 3 * 1024 * 1024) {
        photoInput.value = "";
        window.alert("A foto deve ter no máximo 3 MB.");
        return;
      }
      const previewUrl = URL.createObjectURL(file);
      photoPreview.innerHTML = "";
      const image = document.createElement("img");
      image.src = previewUrl;
      image.alt = "Prévia da nova foto de perfil";
      image.onload = () => URL.revokeObjectURL(previewUrl);
      photoPreview.appendChild(image);
    });
  }

  // Reveal page sections gently without slowing navigation.
  document.querySelectorAll(".stat-card, .content-card, .shortcut-card, .notice-card").forEach((card, index) => {
    card.style.setProperty("--reveal-order", Math.min(index, 8));
    card.classList.add("motion-ready");
  });
});
