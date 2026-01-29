// The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-09
const currentUserId = document.body.dataset.currentUserId;
const currentUserUuid = currentUserId.split('/').filter(Boolean).pop();
const authorEditUrl = `/api/authors/${currentUserUuid}/`;

document.addEventListener('DOMContentLoaded', function () {
  const btn = document.getElementById('follow-btn');
  if (!btn) return;

  async function fetchAuthorData(id) {
    const Uuid = id.replace(/\/$/, '').split('/').pop();
    const res = await fetch(`/api/authors/${Uuid}/`);
    if (!res.ok) throw new Error('author fetch failed');
    return await res.json();
  }

  btn.addEventListener('click', async function () {
    const state = btn.dataset.following;  // "false", "pending", "true"
    const profileId = document.body.dataset.profileId;
    const userId = document.body.dataset.currentUserId;
    const profileUuid = profileId.split('/').filter(Boolean).pop();
    let inboxUrl = `/api/authors/${profileUuid}/inbox/`;
    const csrfToken = document
      .querySelector('meta[name="csrf-token"]')
      .getAttribute('content');
    let url = inboxUrl;
    let method;
    let payload;

    if (state === 'false') {
      method = 'POST';
      try {
        const actor = await fetchAuthorData(userId);
        const object = await fetchAuthorData(profileId);         
        // Always send follow requests through our server so it can
        // forward to remote nodes with proper credentials
        // inboxUrl already points to our local endpoint
        payload = {
          type: 'follow',
          summary: `${actor.displayName} wants to follow ${object.displayName}`,
          actor,
          object
        };
      } catch (err) {
        alert('Failed to fetch author info.');
        return;
      }
    } else {
      url = '/api/follow/';
      method = 'DELETE';
      payload = { from_author: userId, to_author: profileId };
    }

    try {
      const res = await fetch(url, {
        method,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        window.location.reload();
      } else {
        const err = await res.json();
        alert(err.detail || 'Request failed');
      }
    } catch (e) {
      console.error('Inbox request error', e);
      alert('Network error, operation failed');
    }
  });
});

function openSettings() { document.getElementById('settingsModal').style.display = 'flex'; }
window.openSettings = openSettings;
function closeSettings() { document.getElementById('settingsModal').style.display = 'none'; }
window.closeSettings = closeSettings;
function openChangeName() { closeSettings(); document.getElementById('changeNameModal').style.display = 'flex'; }
window.openChangeName = openChangeName;
function closeChangeName() { document.getElementById('changeNameModal').style.display = 'none'; openSettings(); }
window.closeChangeName = closeChangeName;
function openChangeUsername() { closeSettings(); document.getElementById('changeUsernameModal').style.display = 'flex'; }
window.openChangeUsername = openChangeUsername;
function closeChangeUsername() { document.getElementById('changeUsernameModal').style.display = 'none'; openSettings(); }
window.closeChangeUsername = closeChangeUsername;
function openChangePassword() { closeSettings(); document.getElementById('changePasswordModal').style.display = 'flex'; }
window.openChangePassword = openChangePassword;
function closeChangePassword() { document.getElementById('changePasswordModal').style.display = 'none'; openSettings(); }
window.closeChangePassword = closeChangePassword;
function openLinkGithub() { closeSettings(); document.getElementById('linkGithubModal').style.display = 'flex'; }
window.openLinkGithub = openLinkGithub;
function closeLinkGithub() { document.getElementById('linkGithubModal').style.display = 'none'; openSettings(); }
window.closeLinkGithub = closeLinkGithub;
let avatarFromSettings = false;
function openChangeAvatar() {
  const settingsModal = document.getElementById('settingsModal');
  avatarFromSettings = settingsModal && settingsModal.style.display !== 'none';
  closeSettings();
  document.getElementById('changeAvatarModal').style.display = 'flex';
  const fileInput = document.getElementById('avatar-file-input');
  const urlInput = document.getElementById('avatar-url-input');
  if (fileInput) fileInput.value = '';
  if (urlInput) urlInput.value = '';
}
window.openChangeAvatar = openChangeAvatar;
function closeChangeAvatar() {
  document.getElementById('changeAvatarModal').style.display = 'none';
  if (avatarFromSettings) openSettings();
}
window.closeChangeAvatar = closeChangeAvatar;

async function validateImageUrl(url) {
  return new Promise(resolve => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url;
  });
}

const editBtn = document.getElementById('edit-profile-btn');
if (editBtn) {
  editBtn.addEventListener('click', openSettings);
}

const avatarImg = document.getElementById('profile-avatar');
if (avatarImg) {
  const isSelf = document.body.dataset.isSelf === 'True' || document.body.dataset.isSelf === 'true';
}

const avatarSubmit = document.getElementById('change-avatar-submit');
if (avatarSubmit) {
  avatarSubmit.addEventListener('click', async function () {
    const fileInput = document.getElementById('avatar-file-input');
    const urlInput = document.getElementById('avatar-url-input');
    const file = fileInput ? fileInput.files[0] : null;
    const csrfToken = document
      .querySelector('meta[name="csrf-token"]')
      .getAttribute('content');
    let res;
    if (file) {
      const formData = new FormData();
      formData.append('profile_image', file);
      res = await fetch(authorEditUrl, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'X-CSRFToken': csrfToken },
        body: formData
      });
    } else {
      const url = urlInput.value.trim();
      if (!url) { alert('Provide a file or URL.'); return; }
      const valid = await validateImageUrl(url);
      if (!valid) { alert('Invalid image URL.'); return; }
      res = await fetch(authorEditUrl, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ profile_image: url })
      });
    }
    if (res.ok) {
      const data = await res.json();
      avatarImg.src = data.profileImage;
      avatarFromSettings = false;
      closeChangeAvatar();
    } else {
      const d = await res.json();
      alert(d.error || 'Upload failed');
    }
  });
}

document.addEventListener('DOMContentLoaded', function () {
  const nameBtn = document.getElementById('change-name-submit');
  const usernameBtn = document.getElementById('change-username-submit');
  const passwordBtn = document.getElementById('change-password-submit');

  const nameInput = document.getElementById('new-display-name');
  const usernameInput = document.getElementById('new-username');
  const passwordInput = document.getElementById('new-password');
  const confirmInput = document.getElementById('confirm-password');
  const githubBtn = document.getElementById('link-github-submit');
  const githubInput = document.getElementById('github-link-input');
  const csrftoken = document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute('content');

  if (nameBtn) {
    nameBtn.addEventListener('click', async function () {
      const value = nameInput.value.trim();
      if (!value) { alert('Name cannot be empty.'); return; }
      res = await fetch(authorEditUrl, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
        body: JSON.stringify({ display_name: value })
      });
      if (res.ok) { closeChangeName(); window.location.reload(); }
      else { const d = await res.json(); alert(d.error || 'Update failed'); }
    });
  }

  if (usernameBtn) {
    usernameBtn.addEventListener('click', async function () {
      const value = usernameInput.value.trim();
      if (!value) { alert('Username cannot be empty.'); return; }
      res = await fetch(authorEditUrl, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
        body: JSON.stringify({ username: value })
      });
      if (res.ok) { closeChangeUsername(); window.location.reload(); }
      else { const d = await res.json(); alert(d.error || 'Update failed'); }
    });
  }

  if (passwordBtn) {
    passwordBtn.addEventListener('click', async function () {
      const value = passwordInput.value;
      const confirm = confirmInput.value;
      if (!value) { alert('Password cannot be empty.'); return; }
      if (value !== confirm) { alert('Passwords do not match.'); return; }
      res = await fetch(authorEditUrl, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
        body: JSON.stringify({ password: value })
      });
      if (res.ok) { window.location.href = '/login/'; }
      else { const d = await res.json(); alert(d.error || 'Update failed'); }
    });
  }

  if (githubBtn) {
    githubBtn.addEventListener('click', async function () {
      const value = githubInput.value.trim();
      if (!value) { alert('Github link cannot be empty.'); return; }
      res = await fetch(authorEditUrl, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
        body: JSON.stringify({ github_link: value })
      });
      if (res.ok) { closeLinkGithub(); window.location.reload(); }
      else { const d = await res.json(); alert(d.error || 'Update failed'); }
    });
  }
});

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.like-btn').forEach(button => {
    button.addEventListener('click', async function () {
      const rawPostId = this.dataset.postId;
      const entryUrl = rawPostId.replace(/\/+$/, "");
      const entryAuthorId = this.dataset.authorId;
      const entryAuthorUuid = entryAuthorId.split('/').filter(Boolean).pop();
      const currentUserId = document.body.dataset.currentUserId;
      const currentUserUuId = currentUserId.split('/').filter(Boolean).pop();
      const csrfToken = document
        .querySelector('meta[name="csrf-token"]')
        .getAttribute('content');

      let author;
      try {
        const r = await fetch(`/api/authors/${currentUserUuId}/`);
        if (!r.ok) throw new Error('author fetch failed');
        author = await r.json();
      } catch (err) {
        alert('Failed to fetch author info.');
        return;
      }

      const likeId = `${currentUserId.replace(/\/+$/, '')}/liked/${crypto.randomUUID()}`;
      const payload = {
        type: 'like',
        author,
        object: entryUrl,
        published: new Date().toISOString(),
        id: likeId
      };
      const inboxUrl = `/api/authors/${entryAuthorUuid}/inbox/`;

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

        if (!res.ok) {
          const err = await res.json();
          return alert(err.detail || 'Failed to like');
        }

        const countSpan = this.querySelector('.like-count');
        let count = parseInt(countSpan.textContent) || 0;
        countSpan.textContent = `${count + 1} ${count + 1 === 1 ? 'Like' : 'Likes'}`;
        this.disabled = true;

      } catch (e) {
        console.error('Inbox like error', e);
        alert('Network error, could not like');
      }
    });
  });
  document.querySelectorAll('.comment-btn').forEach(button => {
    button.addEventListener('click', function () {
      const rawPostId   = this.dataset.postId;
      const entryId = encodeURIComponent(rawPostId);
      const authorId = this.getAttribute('data-author-id');
      const authorUuid = authorId.split('/').filter(Boolean).pop();
      if (entryId && authorId) {
        window.location.href = `/authors/${authorUuid}/entries/${entryId}/`;
      }
    });
  });

  const updateBtn = document.getElementById('update-btn');
  if (updateBtn) {
    updateBtn.addEventListener('click', async () => {
      const authorId = document.body.dataset.profileId;
      const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
      const url = `/api/authors/${authorId}/github_update/`;

      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
        });
        const data = await res.json();

        if (!res.ok) {
          return alert(data.detail);
        }
        alert(data.detail);
        if (res.status === 201) {
          window.location.reload();
        }
      } catch (err) {
        console.error(err);
        alert('Unexpected error. Please try again later.');
      } finally {
        window.location.reload();
      }

    });
  }

});

document.addEventListener('DOMContentLoaded', () => {
  const descText = document.getElementById('description-text');
  const descInput = document.getElementById('edit-description-input');
  const editDescBtn = document.getElementById('edit-description-btn');
  const saveDescBtn = document.getElementById('save-description-btn');
  const cancelDescBtn = document.getElementById('cancel-description-btn');
  const descBtnBox = document.getElementById('edit-description-buttons');
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  if (editDescBtn && descInput && descText && saveDescBtn && cancelDescBtn) {
    editDescBtn.addEventListener('click', () => {
      descInput.style.display = 'block';
      descBtnBox.style.display = 'block';
      descText.style.display = 'none';
      editDescBtn.style.display = 'none';
      descInput.value = descText.textContent.trim();
    });

    cancelDescBtn.addEventListener('click', () => {
      descInput.style.display = 'none';
      descBtnBox.style.display = 'none';
      descText.style.display = 'block';
      editDescBtn.style.display = 'inline';
    });

    saveDescBtn.addEventListener('click', async () => {
      const newDesc = descInput.value.trim();
      if (!newDesc) {
        alert("Description can't be empty.");
        return;
      }
      try {
        res = await fetch(authorEditUrl, {
          method: 'PUT',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({ description: newDesc })
        });
        if (res.ok) {
          descText.textContent = newDesc;
          descText.style.display = 'block';
          editDescBtn.style.display = 'inline';
          descInput.style.display = 'none';
          descBtnBox.style.display = 'none';
        } else {
          const data = await res.json();
          alert(data.error || 'Update failed');
        }
      } catch (err) {
        console.error('Description update error:', err);
        alert('Network error');
      }
    });
  }
});

async function reloadRelationshipsModal() {
  const modal = document.getElementById('relationships-modal');
  const content = document.getElementById('relationships-content');
  const authorId = document.body.dataset.profileId;

  const activeBtn = content.querySelector('.tabs button.active');
  const activeTab = activeBtn?.dataset.tab;

  try {
    const res = await fetch(`/profile/${authorId}/relationships/?embed=true`);
    const html = await res.text();
    content.innerHTML = html;
    modal.style.display = 'flex';

    const oldScript = document.querySelector("script[data-rel='true']");
    if (oldScript) oldScript.remove();
    const newScript = document.createElement("script");
    newScript.src = window.STATIC_URL + "relationships.min.js";
    newScript.type = "module";
    newScript.dataset.rel = "true";

    newScript.onload = () => {
      if (activeTab) {
        const btn = content.querySelector(`.tabs button[data-tab="${activeTab}"]`);
        if (btn && window.showTab) window.showTab(activeTab, btn);
      }
    };

    document.body.appendChild(newScript);
  } catch (err) {
    content.innerHTML = "<p>Failed to load follow manager.</p>";
    modal.style.display = 'flex';
  }
}
window.reloadRelationshipsModal = reloadRelationshipsModal;

document.getElementById('open-relationships-modal')?.addEventListener('click', async (e) => {
  e.preventDefault();
  await reloadRelationshipsModal();
});

document.getElementById('close-relationships-modal')?.addEventListener('click', () => {
  document.getElementById('relationships-modal').style.display = 'none';
});