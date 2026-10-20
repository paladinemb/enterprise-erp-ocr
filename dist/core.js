function parseText(text) {
  if (!text) return [];
  return text.replace(/\r\n/g,'\n').replace(/\n$/,'').split('\n').map(line =>
    line.includes('\t') ? line.split('\t').map(cell => cell.trim()) : line.trim().split(/\s{2,}|\s*[|｜]\s*/));
}
function headerFields(text) {
  return text.split(/\r?\n/).filter(line=>line.trim()).map((line,i)=>{
    line=line.trim();
    const bilingual=i===0 && line.match(/^([\u4e00-\u9fff]+)\s*([A-Z][A-Z ]*)$/);
    if(bilingual)return [bilingual[1],bilingual[2].replace(/\s+/g,'')];
    // shortcut: fused OCR labels are split only for known fields; other fields need a colon or space.
    const known=line.match(/^(订单编号|日期|供应商)(?:\s*[：:]\s*|\s*)(.*)$/);
    if(known)return [known[1],known[2].trim()];
    const pair=line.match(/^(.+?)[：:\t]\s*(.*)$/) || (i>0 && line.match(/^(\S+)\s+(.+)$/));
    return pair?[pair[1].trim(),pair[2].trim()]:[line,''];
  });
}
function exportRows(header, rows, footer) {
  const fields=headerFields(header), detailWidth=Math.max(0,...rows.map(row=>row.length));
  const width=Math.max(1,fields.length+detailWidth);
  const height=Math.max(rows.length,fields.length?2:0);
  const result=Array.from({length:height},(_,r)=>[
    ...fields.map(field=>r<2?field[r]:''),
    ...Array.from({length:detailWidth},(_,c)=>rows[r]?.[c]??'')
  ]);
  for(const line of footer.split(/\r?\n/).filter(line=>line.trim()))result.push([line.trim(),...Array(width-1).fill('')]);
  return result;
}
function exportSheet(xlsx, header, rows, footer) {
  const combined=exportRows(header,rows,footer), sheet=xlsx.utils.aoa_to_sheet(combined);
  for(const address of Object.keys(sheet))if(!address.startsWith('!') && sheet[address].t==='s')sheet[address].z='@';
  const width=combined[0]?.length||1;
  const footerCount=footer.split(/\r?\n/).filter(line=>line.trim()).length;
  const bodyHeight=combined.length-footerCount;
  const textWidth=value=>[...String(value??'')].reduce((sum,char)=>sum+(/[^\x00-\x7F]/.test(char)?2:1),0);
  sheet['!cols']=Array.from({length:width},(_,c)=>({wch:Math.min(40,Math.max(18,...combined.slice(0,bodyHeight).map(row=>textWidth(row[c])+2)))}));
  sheet['!rows']=combined.map((_,r)=>({hpt:r===1?38:r>=bodyHeight?30:26}));
  sheet['!merges']=width>1?Array.from({length:footerCount},(_,i)=>({s:{r:bodyHeight+i,c:0},e:{r:bodyHeight+i,c:width-1}})):[];
  return sheet;
}
if (typeof module !== 'undefined') module.exports = { parseText, exportRows, exportSheet };
