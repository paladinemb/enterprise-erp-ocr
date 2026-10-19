const $ = id => document.getElementById(id);
let selected, objectURL, busy = false, sourceName = '单据', tableHeaderRows = 0;
function status(message, error=false) { $('status').textContent=message; $('status').classList.toggle('error',error); }
function readTable() { return [...document.querySelectorAll('tbody tr')].map(tr => [...tr.querySelectorAll('td[contenteditable]')].map(td=>td.innerText)); }
function render(rows, headerRows=tableHeaderRows) {
  tableHeaderRows=Math.min(headerRows,rows.length);
  const width = Math.max(1,...rows.map(row=>row.length));
  const table = document.createElement('table'); const head=table.createTHead().insertRow();
  for(let i=0;i<=width;i++){const th=document.createElement('th'); th.textContent=i ? '列 '+i : '#';head.append(th);}
  const body=table.createTBody();
  rows.forEach((row,i)=>{const tr=body.insertRow();if(i<tableHeaderRows)tr.classList.add('column-header');tr.insertCell().textContent=i+1;for(let j=0;j<width;j++){const td=tr.insertCell();td.contentEditable='true';td.setAttribute('aria-label',`第 ${i+1} 行第 ${j+1} 列`);td.textContent=row[j]??'';td.addEventListener('paste',e=>{e.preventDefault();document.execCommand('insertText',false,e.clipboardData.getData('text/plain'));});}});
  $('tablearea').replaceChildren(table);$('count').textContent= `表头 ${tableHeaderRows} 行 · 表体 ${rows.length-tableHeaderRows} 行 · ${width} 列`;$('export').disabled=!rows.length || busy;
}
async function select(file) {
  if(busy)return;
  if(!file || !['image/png','image/jpeg','image/webp'].includes(file.type)){status('请选择 JPG、PNG 或 WebP 图片。',true);return;}
  if(file.size>15*1024*1024){status('图片超过 15 MB，请压缩后重试。',true);return;}
  const url=URL.createObjectURL(file); const test=new Image();test.src=url;
  try{await test.decode();if(test.naturalWidth*test.naturalHeight>25000000)throw Error('图片尺寸超过 2500 万像素，请缩小后重试。');}
  catch(error){URL.revokeObjectURL(url);status(error.message.startsWith('图片尺寸')?error.message:'无法读取这张图片，请换一张重试。',true);return;}
  if(objectURL)URL.revokeObjectURL(objectURL);objectURL=url;selected=undefined;sourceName=file.name.replace(/\.[^.]+$/,'');
  $('image').src=url;$('drop').style.display='none';$('preview').style.display='block';$('filename').textContent=file.name;$('filemeta').textContent=`${test.naturalWidth} × ${test.naturalHeight}`;$('recognize').disabled=true;
  $('correction-stage').style.maxWidth=(480*test.naturalWidth/test.naturalHeight)+'px';
  tableHeaderRows=0;$('doc-header').value=$('doc-footer').value='';$('doc-header-section').hidden=$('doc-footer-section').hidden=true;$('warnings').hidden=true;$('warnings').textContent='';
  $('raw').value='';$('tablearea').replaceChildren();$('count').textContent='尚无识别结果';$('export').disabled=true;status('正在自动定位单据四角…');$('progress').style.display='none';
  busy=true;['choose','replace','demo'].forEach(id=>$(id).disabled=true);
  try{
    const boundary=await fetch('/api/corners',{method:'POST',headers:{'Content-Type':file.type},body:file});
    if(!boundary.ok)throw Error('自动定位四角失败，请重新上传图片。');
    const data=await boundary.json();
    if(!data.detected)throw Error('单据边界不可靠，无法自动定位四角。请上传边缘完整、背景清晰的图片。');
    status('已定位四角，正在自动校正旋转与透视…');
    const response=await fetch('/api/rectify',{method:'POST',headers:{'Content-Type':file.type,'X-Document-Corners':JSON.stringify(data.corners)},body:file});
    if(!response.ok)throw Error('自动校正失败，请重新拍摄或更换图片。');
    const blob=await response.blob();const nextURL=URL.createObjectURL(blob);const preview=new Image();preview.src=nextURL;
    try{await preview.decode();}catch(error){URL.revokeObjectURL(nextURL);throw Error('无法读取校正预览，请重新上传图片。');}
    URL.revokeObjectURL(objectURL);objectURL=nextURL;selected=new File([blob],sourceName+'-校正.png',{type:'image/png'});
    $('image').src=nextURL;$('correction-stage').style.maxWidth=(480*preview.naturalWidth/preview.naturalHeight)+'px';$('recognize').disabled=false;
    $('filemeta').textContent=`校正后 ${preview.naturalWidth} × ${preview.naturalHeight}`;status('已自动定位四角并校正，请检查预览后点击“开始识别”。');
  }catch(error){status(error.message==='Failed to fetch'?'自动校正失败：无法连接本地服务，请重试。':error.message,true);}
  finally{busy=false;['choose','replace','demo'].forEach(id=>$(id).disabled=false);}
}

$('choose').onclick=$('replace').onclick=()=>$('file').click();
$('file').onchange=e=>{select(e.target.files[0]);e.target.value='';};
$('drop').ondragover=e=>{e.preventDefault();$('drop').classList.add('over');};
$('drop').ondragleave=()=>$('drop').classList.remove('over');
$('drop').ondrop=e=>{e.preventDefault();$('drop').classList.remove('over');select(e.dataTransfer.files[0]);};
$('recognize').onclick=async()=>{
  if(!selected||busy)return;
  busy=true;['recognize','replace','demo','addrow','addcol','rebuild','export','raw','doc-header','doc-footer'].forEach(id=>$(id).disabled=true);$('progress').style.display='block';$('progress').removeAttribute('value');status('正在识别文字与表格结构，首次运行需下载模型…');
  try{
    const response=await fetch('/api/recognize',{method:'POST',headers:{'Content-Type':selected.type},body:selected});
    if(response.status===501||response.status===404)throw Error('请使用 Python 识别服务启动程序，当前服务只提供静态页面。');
    const data=await response.json();
    if(!response.ok)throw Error(data.error||'表格识别失败，请重试。');
    $('raw').value=data.text;
    $('doc-header').value=(data.header||[]).join('\n');$('doc-footer').value=(data.footer||[]).join('\n');
    $('doc-header-section').hidden=$('doc-footer-section').hidden=false;
    $('warnings').textContent=(data.warnings||[]).join('\n');$('warnings').hidden=!data.warnings?.length;
    render(data.rows,data.header_rows||0);status('识别完成，已按位置区分单据抬头、表头、表体和表尾，请校对后导出。');$('progress').value=1;
  }catch(error){console.error(error);status(error.message==='Failed to fetch'?'无法连接本地识别服务，请确认服务正在运行。':error.message,true);}
  finally{busy=false;['recognize','replace','demo','addrow','addcol','rebuild','raw','doc-header','doc-footer'].forEach(id=>$(id).disabled=false);$('export').disabled=!readTable().length;}

};
$('rebuild').onclick=()=>{render(parseText($('raw').value));status('已从文本重新生成表格，抬头与表尾保持当前内容。');};
$('addrow').onclick=()=>{const rows=readTable();rows.push(Array(Math.max(1,rows[0]?.length||4)).fill(''));render(rows);};
$('addcol').onclick=()=>{const rows=readTable();if(!rows.length)rows.push([]);rows.forEach(row=>row.push(''));render(rows);};
$('export').onclick=()=>{
  if(!window.XLSX){status('Excel 组件未加载，请刷新页面。',true);return;}
  const rows=readTable();if(!rows.length)return;
  try{const sheet=XLSX.utils.aoa_to_sheet(exportRows($('doc-header').value,rows,$('doc-footer').value));sheet['!cols']=Array.from({length:Math.max(...rows.map(row=>row.length))},()=>({wch:22}));const book=XLSX.utils.book_new();XLSX.utils.book_append_sheet(book,sheet,'识别结果');XLSX.writeFile(book,sourceName+'-识别结果.xlsx');status('已导出 Excel（文本单元格），编号前导零保持不变。');}catch(error){status('导出失败，请重试。',true);console.error(error);}
};
$('demo').onclick=()=>{
  if(busy)return;const canvas=document.createElement('canvas');canvas.width=1600;canvas.height=1050;const c=canvas.getContext('2d');c.fillStyle='#c4c7c9';c.fillRect(0,0,1600,1050);c.fillStyle='white';c.fillRect(30,30,1540,990);c.fillStyle='#111';c.font='bold 54px sans-serif';c.textAlign='center';c.fillText('采购订单 PURCHASE ORDER',800,120);c.textAlign='left';c.font='32px sans-serif';c.fillText('订单编号 PO20261019001',100,220);c.fillText('日期 2026-10-19',100,285);c.fillText('供应商 示例工业设备有限公司',100,350);
  const rows=[['物料编码','物料名称','数量','单价','金额'],['A001','标准轴承','20','35.00','700.00'],['A002','固定螺栓','100','2.50','250.00'],['A003','密封垫圈','50','6.00','300.00']];const x=[100,400,830,1050,1300];rows.forEach((row,i)=>row.forEach((text,j)=>c.fillText(text,x[j],480+i*95)));c.fillText('合计 CNY 1250.00',100,930);canvas.toBlob(blob=>select(new File([blob],'示例采购订单.png',{type:'image/png'})),'image/png');
};
