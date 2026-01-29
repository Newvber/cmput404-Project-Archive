document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const isAuth = body.dataset.authenticated === '1';

  const profileToggle = document.getElementById("profile-toggle");
  const profileMenu = document.getElementById("profile-menu");
  const logoutBtn = document.getElementById("logout-btn");

  if (profileToggle && profileMenu) {
    profileToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      profileMenu.style.display = profileMenu.style.display === "block" ? "none" : "block";
    });

    document.addEventListener("click", () => {
      profileMenu.style.display = "none";
    });
  }

  if (isAuth && logoutBtn) {
    logoutBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const csrftoken = document
        .querySelector('meta[name="csrf-token"]')
        ?.getAttribute("content");

      const res = await fetch("/api/logout/", {
        method: "POST",
        credentials: "include",
        headers: { "X-CSRFToken": csrftoken }
      });

      if (res.ok) {
        window.location.href = "/";
      } else {
        alert("Logout failed");
      }
    });
  }


  const input = document.getElementById("author-search-input");
  const suggestions = document.getElementById("search-suggestions");

  if (input && suggestions) {
    input.addEventListener("click", async () => {
      try {
        await fetch("/api/sync_remote_authors/");
      } catch (_err) {
        // ignore
      }
    });

    input.addEventListener("input", async () => {
      const query = input.value.trim();
      if (query.length === 0) {
        suggestions.style.display = "none";
        return;
      }

      try {
        const res = await fetch(`/api/author_autocomplete/?q=${encodeURIComponent(query)}`);
        const data = await res.json();

        suggestions.innerHTML = "";
        data.results.forEach(author => {
          const li = document.createElement("li");
          const encodedId = encodeURIComponent(author.id);
          li.innerHTML = `
            <div class="suggestion-entry">
              <div class="suggestion-icon">👤</div>
              <div class="suggestion-text">
                <div class="display-name">${author.display_name}</div>
                <div class="author-id">${author.id}</div>
              </div>
            </div>
          `;

          li.addEventListener("click", () => {
            window.location.href = `/authors/${encodedId}/`;
          });

          suggestions.appendChild(li);
        });

        suggestions.style.display = data.results.length > 0 ? "block" : "none";
      } catch (err) {
        console.error("Autocomplete fetch failed", err);
        suggestions.style.display = "none";
      }
    });

    document.addEventListener("click", (e) => {
      if (!suggestions.contains(e.target) && e.target !== input) {
        suggestions.style.display = "none";
      }
    });
  }
});
