// The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-09
import { Parser, HtmlRenderer } from 'commonmark';

const reader = new Parser();
const writer = new HtmlRenderer();

export function renderPosts() {
  document.querySelectorAll('[data-contenttype]').forEach(el => {
    const type    = el.dataset.contenttype;
    const content = el.dataset.content || '';

    if (type === 'text/markdown') {
      const parsed = reader.parse(content);
      el.innerHTML = writer.render(parsed);
    } else if (type && (type.startsWith('image') || type === 'application/base64')) {
      el.textContent = '';
    } else {
      el.textContent = content;
    }
  });
}

document.addEventListener('DOMContentLoaded', renderPosts);
