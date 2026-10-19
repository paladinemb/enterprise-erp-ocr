function parseText(text) {
  if (!text) return [];
  return text.replace(/\r\n/g,'\n').replace(/\n$/,'').split('\n').map(line =>
    line.includes('\t') ? line.split('\t').map(cell => cell.trim()) : line.trim().split(/\s{2,}|\s*[|｜]\s*/));
}
function exportRows(header, rows, footer) {
  const lines = text => text.split(/\r?\n/).filter(line=>line.trim()).map(line=>[line]);
  const top = lines(header), bottom = lines(footer);
  return [...top, ...(top.length?[[]]:[]), ...rows, ...(bottom.length?[[]]:[]), ...bottom];
}
if (typeof module !== 'undefined') module.exports = { parseText, exportRows };
