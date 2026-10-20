function parseText(text) {
  if (!text) return [];
  return text.replace(/\r\n/g,'\n').replace(/\n$/,'').split('\n').map(line =>
    line.includes('\t') ? line.split('\t').map(cell => cell.trim()) : line.trim().split(/\s{2,}|\s*[|｜]\s*/));
}
function headerFields(text) {
  return text.split(/\r?\n/).filter(line=>line.trim()).flatMap((line,i)=>{
    line=line.trim();
    const bilingual=i===0 && line.match(/^([\u4e00-\u9fff]+)\s*([A-Z][A-Z ]*)$/);
    if(bilingual)return [[bilingual[1],bilingual[2].replace(/\s+/g,'')]];
    const labels=[...line.matchAll(/(?:客户名称|客户电话|客户地址|联系人|单据日期|订单编号|供应商|申请人|部门|地址|电话|日期)\s*[：:]|No\./gi)];
    if(labels.length){
      const prefix=line.slice(0,labels[0].index).trim();
      return [...(prefix?[[prefix,'']]:[]),...labels.map((label,j)=>[
        label[0].replace(/[：:]\s*$/,'').trim(),line.slice(label.index+label[0].length,labels[j+1]?.index).trim()
      ])];
    }
    // shortcut: fused OCR labels are split only for known fields; other fields need a colon or space.
    const known=line.match(/^(订单编号|日期|供应商)(?:\s*[：:]\s*|\s*)(.*)$/);
    if(known)return [[known[1],known[2].trim()]];
    const pair=line.match(/^(.+?)[：:\t]\s*(.*)$/) || (i>0 && line.match(/^(\S+)\s+(.+)$/));
    if(pair)return [[pair[1].trim(),pair[2].trim()]];
    if(/公司$/.test(line))return [['公司名称',line]];
    if(line.length>2 && /单$/.test(line))return [['单据名称',line]];
    return [[line,'']];
  });
}
function footerFields(text) {
  return text.split(/\r?\n/).filter(line=>line.trim()).flatMap(line=>{
    line=line.trim();
    const labels=[...line.matchAll(/合计|总计|小计|制单|核批|承办|审核|复核|批准|签字|经办|日期/g)];
    if(labels[0]?.index===0)return labels.map((label,i)=>[
      label[0],line.slice(label.index+label[0].length,labels[i+1]?.index).replace(/^[：:\s]+/,'').trim()
    ]);
    const pair=line.match(/^(.+?)[：:\t]\s*(.*)$/) || line.match(/^(\S+)\s+(.+)$/);
    return [pair?[pair[1].trim(),pair[2].trim()]:[line,'']];
  });
}
function exportRows(fields, rows, footer) {
  const detailWidth=Math.max(0,...rows.map(row=>row.length));
  const width=Math.max(footer.length?2:1,fields.length+detailWidth);
  const height=Math.max(rows.length,fields.length?2:0);
  const result=Array.from({length:height},(_,r)=>[
    ...fields.map(field=>r<2?field[r]:''),
    ...Array.from({length:width-fields.length},(_,c)=>rows[r]?.[c]??'')
  ]);
  for(const field of footer)result.push([field[0],field[1],...Array(width-2).fill('')]);
  return result;
}
function exportSheet(xlsx, header, rows, footer) {
  const combined=exportRows(header,rows,footer), sheet=xlsx.utils.aoa_to_sheet(combined);
  for(const address of Object.keys(sheet))if(!address.startsWith('!') && sheet[address].t==='s')sheet[address].z='@';
  const width=combined[0]?.length||1, bodyHeight=combined.length-footer.length;
  const textWidth=value=>[...String(value??'')].reduce((sum,char)=>sum+(/[^\x00-\x7F]/.test(char)?2:1),0);
  sheet['!cols']=Array.from({length:width},(_,c)=>({wch:Math.min(40,Math.max(18,...combined.slice(0,bodyHeight).map(row=>textWidth(row[c])+2)))}));
  sheet['!rows']=combined.map((_,r)=>({hpt:r===1?38:r>=bodyHeight?30:26}));
  sheet['!merges']=width>2?footer.map((_,i)=>({s:{r:bodyHeight+i,c:1},e:{r:bodyHeight+i,c:width-1}})):[];
  return sheet;
}
if (typeof module !== 'undefined') module.exports = { parseText, headerFields, footerFields, exportRows, exportSheet };
