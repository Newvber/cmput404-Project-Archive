// The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-09
document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;
  const isAuth = body.dataset.authenticated === '1';
  const currentUserId = body.dataset.currentUserId;

  if (isAuth) {
    const newPostBtn = document.getElementById('new-post-btn');
    if (newPostBtn) {
      newPostBtn.addEventListener('click', () => {
        if (!currentUserId) return;
        window.location.href = `/feed/${encodeURIComponent(currentUserId)}/newpost/`;
      });
    }

    document.querySelectorAll(".like-btn").forEach(button => {
        button.addEventListener("click", async function() {
          const authorId  = this.dataset.authorId;
          const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");

          const entryUrl = this.dataset.postId.replace(/\/+$/, "");

          let author;
          try {
            const currentUserUuid = currentUserId.split('/').filter(Boolean).pop();
            const r = await fetch(`/api/authors/${currentUserUuid}/`);
            if (!r.ok) throw new Error('author fetch failed');
            author = await r.json();
          } catch (e) {
            alert('Failed to fetch author info.');
            return;
          }

          const likeId = `${currentUserId.replace(/\/+$/, '')}/liked/${crypto.randomUUID()}`;
          const payload = {
          type: "like",
          author,
          object: entryUrl,
          published: new Date().toISOString(),
          id: likeId
          };

          try {
          const authorUuid = authorId.split('/').filter(Boolean).pop();
          const inboxUrl = `/api/authors/${authorUuid}/inbox/`;
          const res = await fetch(
              inboxUrl,
              {
              method: "POST",
              credentials: "include",
              headers: {
                  "Content-Type": "application/json",
                  "X-CSRFToken": csrfToken
              },
              body: JSON.stringify(payload)
              });
          if (!res.ok) {const err = await res.json(); throw err;};
          const countElem = this.querySelector(".like-count");
          let count = parseInt(countElem.textContent) || 0;
          count += 1;
          countElem.textContent = `${count} ${count === 1 ? "Like" : "Likes"}`;

          } catch (err) {
          alert(err.detail || "You've liked this post already");
          // can't distinguish whether it failed or actually liked.. but whatever...
          // alert(err.detail || "Failed to like this post");
          }

        });
      });

    document.querySelectorAll('.comment-btn').forEach(button => {
      button.addEventListener('click', function () {
        const rawPostId   = this.dataset.postId;
        const authorId = this.getAttribute('data-author-id');
        if (rawPostId && authorId) {
          const authorUuid = authorId.split('/').filter(Boolean).pop();
          const entryId = encodeURIComponent(rawPostId);
          window.location.href = `/authors/${authorUuid}/entries/${entryId}/`;
        }
      });
    });
  }

  document.querySelectorAll('.post-avatar').forEach(header => {
    header.addEventListener('click', function () {
      const authorId = this.getAttribute('data-author-id');
      if (authorId) {
        const encoded = encodeURIComponent(authorId);
        window.location.href = `/authors/${encoded}/`;
      }
    });
  });

  document.querySelectorAll('.post-title-link').forEach(link => {
    link.addEventListener('click', () => {
      const authorId = link.dataset.authorId;
      const rawId    = link.dataset.postId;              
      const entryId  = encodeURIComponent(rawId);
      const authorUuid = authorId.split('/').filter(Boolean).pop();        
      window.location.href = `/authors/${authorUuid}/entries/${entryId}/`;
    });
  });

});
