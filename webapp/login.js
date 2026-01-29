// The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-09
document.addEventListener('DOMContentLoaded', () => {
  const csrftoken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
  document.getElementById('login-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const msgBox = document.getElementById('message');
    msgBox.innerText = '';
    const response = await fetch('/api/login/', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken,
      },
      body: JSON.stringify({ username, password })
    });
    const data = await response.json();
    if (response.ok) {
      alert('Login successful!');
      window.location.href = '/';
    } else {
      alert(data.error || 'Login failed.');
    }
  });
});
