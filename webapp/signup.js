// The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-09
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('signup-form').addEventListener('submit', async function(e) {
    const csrftoken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    e.preventDefault();
    const username = document.getElementById('username').value;
    const display_name = document.getElementById('display_name').value;
    const password = document.getElementById('password').value;
    const confirm = document.getElementById('confirm_password').value;
    const msgBox = document.getElementById('message');
    msgBox.innerText = '';
    if (password !== confirm) {
      msgBox.innerText = 'Passwords do not match.';
      return;
    }
    const response = await fetch('/api/signup/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      body: JSON.stringify({ username, display_name, password })
    });
    const data = await response.json();
    if (response.ok) {
      alert(data.message || 'Signup successful!');
      window.location.href = '/login/';
    } else {
      msgBox.innerText = JSON.stringify(data);
    }
  });
});
