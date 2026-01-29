// The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-09
document.addEventListener('DOMContentLoaded', () => {
  function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
  }

  const textarea = document.querySelector('#content');
  const previewEl = document.getElementById('preview');
  const editorContainer = document.querySelector('.editor-container');
  const editBox = editorContainer.firstElementChild;
  const previewBox = editorContainer.lastElementChild;
  const contentTypeSelect = document.querySelector('#contentType');
  const imageInput = document.querySelector('#image');
  const uploadImageBtn = document.getElementById('uploadImageBtn');
  const insertImageBtn = document.getElementById('insertImageBtn');
  let soloImageBase64 = '';
  let soloImageMime = '';

  function updateMode() {
    const type = contentTypeSelect.value;
    if (type === 'image') {
      editBox.style.display = 'none';
      previewBox.style.display = '';
      textarea.value = '';
      previewEl.innerHTML = '';
      uploadImageBtn.style.display = '';
      insertImageBtn.style.display = 'none';
      soloImageBase64 = '';
      soloImageMime = '';
    } else if (type === 'text/markdown') {
      editBox.style.display = '';
      previewBox.style.display = '';
      previewEl.innerHTML = convertMarkdownToHtml(textarea.value);
      uploadImageBtn.style.display = 'none';
      insertImageBtn.style.display = '';
      soloImageBase64 = '';
      soloImageMime = '';
    } else {
      editBox.style.display = '';
      previewBox.style.display = 'none';
      previewEl.innerHTML = '';
      uploadImageBtn.style.display = 'none';
      insertImageBtn.style.display = 'none';
      soloImageBase64 = '';
      soloImageMime = '';
    }
  }

  contentTypeSelect.addEventListener('change', updateMode);

  function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  textarea.addEventListener('input', () => {
    if (contentTypeSelect.value === 'text/plain') {
      previewEl.innerHTML = '';
    } else {
      previewEl.innerHTML = convertMarkdownToHtml(textarea.value);
    }
  });

  const initialContentType = document.body.dataset.initialContentType;
  const initialContent = document.body.dataset.initialContent;
  if (initialContentType === 'image' || initialContentType === 'application/base64' || initialContentType.startsWith('image/')) {
    contentTypeSelect.value = 'image';
    updateMode();
    soloImageBase64 = initialContent || '';
    soloImageMime = document.body.dataset.initialMime || '';
    previewEl.innerHTML = `<img src="data:${soloImageMime};base64,${soloImageBase64}" style="max-width:100%;">`;
  } else {
    contentTypeSelect.value = initialContentType || 'text/plain';
    previewEl.innerHTML = convertMarkdownToHtml(textarea.value);
    updateMode();
  }

  document.querySelector('.post-btn').addEventListener('click', async event => {
    event.preventDefault();
    const title = document.querySelector('#title').value.trim();
    const description = document.querySelector('#description').value.trim();
    const visibility = document.querySelector('input[name="visibility"]:checked').value.toUpperCase();
    const selectedContentType = document.querySelector('#contentType').value;
    let content = document.querySelector('#content').value.trim();
    let finalContentType = selectedContentType;
    if (selectedContentType === 'image') {
      if (!soloImageBase64) {
        alert('Please choose an image.');
        return;
      }
      content = soloImageBase64;
      if (soloImageMime === 'application/base64') {
        finalContentType = 'application/base64';
      } else {
        finalContentType = `${soloImageMime};base64`;
      }
    }
    const body = document.body;
    const authorId = body.dataset.authorId;
    const entryId = body.dataset.entryId;
    const encodedEntryId = encodeURIComponent(entryId);
    const entryUuid = entryId.split('/').filter(Boolean).pop();
    const authorUuid = authorId.split('/').filter(Boolean).pop();
    const url = `/api/authors/${authorUuid}/entries/${entryUuid}/`;
    const data = { title, content, description, visibility, contentType: finalContentType };
    try {
      const response = await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify(data)
      });
      const result = await response.json();
      if (!response.ok) {
        console.error('Server error:', result);
        return;
      }
      console.log('Success:', result);
      alert('Post updated successfully!');
      window.location.href = `/authors/${authorUuid}/entries/${encodedEntryId}/`;
    } catch (err) {
      console.error('Fetch error:', err);
    }
  });

  document.querySelector('.cancel-btn').addEventListener('click', () => {
    const body = document.body;
    const authorId = body.dataset.authorId;
    const entryId = body.dataset.entryId;
    const encodedEntryId = encodeURIComponent(entryId);
    const authorUuid = authorId.split('/').filter(Boolean).pop();
    window.location.href = `/authors/${authorUuid}/entries/${encodedEntryId}/`;
  });

  uploadImageBtn.addEventListener('click', () => {
    imageInput.click();
  });

  imageInput.addEventListener('change', async function () {
    if (contentTypeSelect.value !== 'image') return;
    const file = this.files[0];
    if (!file) return;
    const base64 = await readFileAsBase64(file);
    soloImageBase64 = base64;
    if (file.type === 'image/png') {
      soloImageMime = 'image/png';
    } else if (file.type === 'image/jpeg') {
      soloImageMime = 'image/jpeg';
    } else {
      soloImageMime = 'application/base64';
    }
    previewEl.innerHTML = `<img src="data:${soloImageMime};base64,${base64}" style="max-width:100%;">`;
    this.value = '';
  });

  insertImageBtn.addEventListener('click', () => {
    const url = prompt('Enter image URL:');
    if (!url) return;
    const alt = prompt('Enter alt text (optional):', '') || '';
    let markdown = `![${alt}](${url})`;
    textarea.value += (textarea.value ? '\n\n' : '') + markdown;
    previewEl.innerHTML = convertMarkdownToHtml(textarea.value);
  });
});
