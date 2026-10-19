function parseText(text) {
  return text.split(/\r?\n/).filter(line => line.trim()).map(line =>
    line.includes('\t') ? line.split('\t').map(cell => cell.trim()) : line.trim().split(/\s{2,}|\s*[|｜]\s*/));
}
function fromLines(lines) {
  // shortcut: 以横向空隙推断列；复杂合并单元格需升级到表格结构识别。
  return lines.filter(line => line.words?.length).map(line => {
    const words = line.words.slice().sort((a,b) => a.bbox.x0-b.bbox.x0);
    const cells = []; let last;
    for (const word of words) {
      const gap = last ? word.bbox.x0-last.bbox.x1 : Infinity;
      if (!last || gap > Math.max(14, (word.bbox.y1-word.bbox.y0)*0.9)) cells.push(word.text);
      else cells[cells.length-1] += (/^[\x00-\x7F]+$/.test(word.text) && gap > 4 ? ' ' : '') + word.text;
      last = word;
    }
    return cells;
  });
}
function mergeFirstRows(rows) {
  if (!rows.length) return [];
  // shortcut: 标题和值依据冒号、已有分列或空格拆分；无明确分隔时请直接校对单元格。
  const fields = Array.from({ length: 4 }, (_, i) => {
    const row = rows[i] || [];
    const text = row.join(' ').trim();
    const bilingualTitle = i === 0 && text.match(/^([\u4e00-\u9fff]+)\s+([A-Z][A-Z ]*)$/);
    if (bilingualTitle) return [bilingualTitle[1], bilingualTitle[2].replace(/\s+/g, '')];
    const colon = text.match(/^(.+?)[：:]\s*(.*)$/);
    if (colon) return [colon[1].trim(), colon[2]];
    const label = text.match(/^(订单编号|日期|供应商)\s*(.+)$/);
    if (label) return [label[1], label[2].trim()];
    if (row.length > 1) return [row[0].trim(), row.slice(1).join(' ').trim()];
    const space = text.match(/^(\S+)\s+(.+)$/);
    return space ? [space[1], space[2]] : [text, ''];
  });
  const remaining = rows.slice(4);
  const details = remaining.length > 1 ? remaining.slice(1) : [[]];
  return [
    [...fields.map(field => field[0]), ...(remaining[0] || [])],
    ...details.map((row, i) => [...(i === 0 ? fields.map(field => field[1]) : ['', '', '', '']), ...row])
  ];
}
if (typeof module !== 'undefined') module.exports = { parseText, fromLines, mergeFirstRows };
