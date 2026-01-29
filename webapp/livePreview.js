// The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-09
import { Parser, HtmlRenderer } from 'commonmark';

const reader = new Parser();
const writer = new HtmlRenderer();

function updatePreview() {
  const typeSelect = document.getElementById('contentType');
  if (typeSelect && typeSelect.value === 'image') return;
  const md = textarea.value;
  const parsed = reader.parse(md);
  preview.innerHTML = writer.render(parsed);
}

export function convertMarkdownToHtml(md) {
  const parsed = reader.parse(md);
  return writer.render(parsed);
}

// allow global access from non-module scripts:
window.convertMarkdownToHtml = convertMarkdownToHtml;

const textarea = document.getElementById('content');
const preview  = document.getElementById('preview');

textarea.addEventListener('input', updatePreview);
document.addEventListener('DOMContentLoaded', updatePreview);
