// The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-09
document.addEventListener('DOMContentLoaded', () => {
  const csrftoken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
  const currentUserId = document.body.dataset.currentUserId;

  async function fetchAuthorData(id) {
    const Uuid = id.replace(/\/$/, '').split('/').pop();
    const res = await fetch(`/api/authors/${Uuid}/`);
    if (!res.ok) throw new Error('author fetch failed');
    return await res.json();
  }

  async function sendFollowRequest(button, fromId, toId) {
    const toUuid = toId.split('/').filter(Boolean).pop();
    let inboxUrl = `/api/authors/${toUuid}/inbox/`;
    let payload;
    try {
        const actor = await fetchAuthorData(fromId);
        const object = await fetchAuthorData(toId);     

      // Always send through our backend so it can handle remote auth
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
    const response = await fetch(inboxUrl, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      body: JSON.stringify(payload)
    });
    if (response.ok) {
      button.textContent = 'Pending';
      button.disabled = true;
      button.classList.remove('follow');
    } else {
      const err = await response.json();
      alert(err.detail || 'Failed to send follow request.');
    }
  }
  window.sendFollowRequest = sendFollowRequest;

  async function handleUnfollow(button) {
    const fromId = button.getAttribute('data-from-id');
    const toId   = button.getAttribute('data-to-id');
    const response = await fetch('/api/follow/', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
      body: JSON.stringify({ from_author: fromId, to_author: toId })
    });
    if (response.ok) window.reloadRelationshipsModal();
    else alert('Failed to unfollow user.');
  }
  window.handleUnfollow = handleUnfollow;

  async function handleAccept(button) {
    const fromId = button.getAttribute('data-from-id');
    const response = await fetch('/api/follow/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
      body: JSON.stringify({ from_author: fromId, to_author: currentUserId })
    });
    if (response.ok) window.reloadRelationshipsModal();
    else alert('Failed to accept request.');
  }
  window.handleAccept = handleAccept;

  async function handleDecline(button) {
    const fromId = button.getAttribute('data-from-id');
    const response = await fetch('/api/follow/', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
      body: JSON.stringify({ from_author: fromId, to_author: currentUserId })
    });
    if (response.ok) window.reloadRelationshipsModal();
    else alert('Failed to decline request.');
  }
  window.handleDecline = handleDecline;

  async function unfollowThem(fromId, toId, reload = true) {
    const response = await fetch('/api/follow/', {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      body: JSON.stringify({ from_author: fromId, to_author: toId })
    });
    if (response.ok) {
      if (reload) window.reloadRelationshipsModal();
    } else {
      alert('Unfollow failed.');
    }
  }
  window.unfollowThem = unfollowThem;
  
  async function makeThemUnfollowMe(fromId, toId, reload = true) {
    const response = await fetch('/api/follow/', {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      body: JSON.stringify({ from_author: fromId, to_author: toId })
    });
    if (response.ok) {
      if (reload) window.reloadRelationshipsModal();
    } else {
      alert('Request failed.');
    }
  }
  window.makeThemUnfollowMe = makeThemUnfollowMe;

  async function unfriend(user1, user2) {
    await Promise.all([
      unfollowThem(user1, user2, false),
      makeThemUnfollowMe(user2, user1, false)
    ]);
    window.reloadRelationshipsModal();
  }
  window.unfriend = unfriend;

});

function showTab(tabId, button) {
  document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
  document.getElementById(tabId).style.display = 'block';
  document.querySelectorAll('.tabs button').forEach(btn => btn.classList.remove('active'));
  button.classList.add('active');
}
window.showTab = showTab;