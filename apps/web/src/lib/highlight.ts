/**
 * Converts a string with <mark> tags to safe HTML.
 * Only allows <mark> tags, escaping all other HTML.
 */
export function toMarkedHTML(s?: string) {
  if (!s) return { __html: "" }
  
  // Escape HTML
  const esc = s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;")
  
  // Unescape the <mark> tags we asked ES to insert
  const restored = esc
    .replace(/&lt;mark&gt;/g, "<mark>")
    .replace(/&lt;\/mark&gt;/g, "</mark>")
  
  return { __html: restored }
}
