// The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-09
document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;
  const authorId = body.dataset.authorId;
  const entryId = body.dataset.entryId;
  const encodedEntryId = encodeURIComponent(entryId);
  const entryUuid = entryId.split('/').filter(Boolean).pop();
  const currentUserId = body.dataset.currentUserId;
  const authorUuid = authorId.split('/').filter(Boolean).pop();
  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
  

  const dropdownToggle = document.getElementById('dropdown-toggle');
  const dropdownMenu = document.getElementById('dropdown-menu');

  if (dropdownToggle && dropdownMenu) {
    dropdownToggle.addEventListener('click', () => {
      dropdownMenu.classList.toggle('hidden');
    });
    
    document.addEventListener('click', (e) => {
      if (!dropdownToggle.contains(e.target) && !dropdownMenu.contains(e.target)) {
        dropdownMenu.classList.add('hidden');
      }
    });
  }

  const deleteBtn = document.getElementById('delete-entry-btn');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', async () => {
      if (!confirm('Are you sure you want to delete this post?')) return;
      try {
        const res = await fetch(`/api/authors/${authorUuid}/entries/${entryUuid}/`, {

          method: 'DELETE',
          headers: { 'X-CSRFToken': csrfToken }
        });
        if (res.status === 204) {
          alert('Post deleted successfully.');
          window.location.href = '/';
        } else if (res.status === 403) {
          alert('You are not authorized to delete this post.');
        } else {
          alert('Failed to delete the post.');
          console.error(await res.text());
        }
      } catch (err) {
        alert('An error occurred while deleting the post.');
        console.error(err);
      }
    });
  }

  const editBtn = document.getElementById('edit-entry-btn');
  if (editBtn) {
    editBtn.addEventListener('click', () => {
      window.location.href = `/authors/${authorUuid}/entries/${encodedEntryId}/edit/`;
    });
  }

  const showFormBtn = document.getElementById('show-comment-form-btn');
  const commentForm = document.getElementById('comment-form');
  const cancelBtn = document.getElementById('cancel-comment-btn');
  const sendBtn = document.getElementById('send-comment-btn');
  const commentText = document.getElementById('comment-text');

  showFormBtn.addEventListener('click', () => {
    commentForm.style.display = 'block';
    showFormBtn.style.display = 'none';
  });

  cancelBtn.addEventListener('click', () => {
    commentForm.style.display = 'none';
    showFormBtn.style.display = 'inline-block';
    commentText.value = '';
  });

  sendBtn.addEventListener('click', async () => {
    const content = commentText.value.trim();
    if (!content) return alert('Please enter your comment');

    // prevent duplicate submissions
    if (sendBtn.disabled) return;
    sendBtn.disabled = true;

    try {
      const payload = {
        type: 'comment',
        comment: content,
        contentType: 'text/plain',
        object: entryId,
        published: new Date().toISOString()
      };
      const res = await fetch(`/api/authors/${authorUuid}/entries/${encodedEntryId}/commented/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        commentText.value = '';
        commentForm.style.display = 'none';
        showFormBtn.style.display = 'inline-block';
        await loadComments();
      } else {
        const err = await res.json();
        alert(err.detail || 'Fail to post a comment');
      }
    } finally {
      sendBtn.disabled = false;
    }
  });

  loadComments();

  async function loadComments() {
    const url = `/api/authors/${authorUuid}/entries/${entryUuid}/comments/`;
    try {
      const res = await fetch(url, { credentials: 'include' });
      if (!res.ok) {
        console.error("Comments fetch failed:", await res.text());
        document.querySelector('.comments-section').innerHTML =
          '<p>Could not load comments.</p>';
        return;
      };
      const data = await res.json();
      const list = data.src || [];
      const container = document.querySelector('.comments-section');
      container.innerHTML = '';
      if (list.length === 0) {
        container.innerHTML = '<p>No comments yet.</p>';
        return;
      }
      list.forEach(c => {
        const date = new Date(c.published).toLocaleString();
        const authorUrl = c.author.id;
        const parts = authorUrl.split('/').filter(Boolean);
        const commentAuthorUuid = parts[parts.length - 1];
        const avatar = c.author.profileImage || '/static/avatar.jpg';
        container.insertAdjacentHTML('beforeend', `
          <div class="comment-box">
            <div class="comment-avatar"><img src="${avatar}" alt="Avatar"></div>
            <div class="comment-content">
              <div class="comment-author">${c.author.displayName}</div>
              <span class="comment-date">${date}</span>
              <div class="comment-text">${c.comment}</div>
              <div class="comment-actions">
                <button class="comment-action-btn" data-comment-id="${c.id}" data-author-id="${commentAuthorUuid}">
                  <span class="action-icon">❤️</span>
                  <span class="action-text like-count">${c.likes.count || 0} Likes</span>
                </button>
              </div>
            </div>
          </div>
        `);
      });
      document.querySelectorAll('.comment-action-btn').forEach(btn => btn.addEventListener('click', async function () {
        const commentId = this.dataset.commentId;
        const commentUuid = commentId.replace(/\/$/, '').split('/').pop();
        const commentAuthor = this.dataset.authorId;
        const commentAuthorUuid = commentAuthor.split('/').filter(Boolean).pop();
        const inboxUrl = `/api/authors/${commentAuthorUuid}/inbox/`;
        let authorData;
        try {
          const currentUserUuid = currentUserId.split('/').filter(Boolean).pop();
          const r = await fetch(`/api/authors/${currentUserUuid}/`);
          if (!r.ok) throw new Error('author fetch failed');
          authorData = await r.json();
        } catch (err) {
          alert('Failed to fetch author info.');
          return;
        }

          const likeId = `${currentUserId.replace(/\/+$/, '')}/liked/${crypto.randomUUID()}`;
          const payload = {
            type: 'like',
            author: authorData,
            object: commentId,
            published: new Date().toISOString(),
            id: likeId
          };
        try {
          const res = await fetch(inboxUrl, {
            method: 'POST',
            credentials: 'include',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
          });
          if (res.ok) {
            const span = this.querySelector('.like-count');
            const current = parseInt(span.textContent) || 0;
            span.textContent = `${current + 1} Likes`;
            this.disabled = true;
          } else {
            const e = await res.json();
            alert(e.detail || 'Failed to like this comment again');
          }
        } catch (e) {
          console.error(e);
          alert('Network error');
        }
      }));
    } catch (e) {
      console.error(e);
    }
  }
});



