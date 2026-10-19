const $ = id => document.getElementById(id);
let selected, objectURL, original, originalURL, corners, sourceWidth, sourceHeight, busy = false, sourceName = '单据';
function status(message, error=false) { $('status').textContent=message; $('status').classList.toggle('error',error); }
function readTable() { return [...document.querySelectorAll('tbody tr')].map(tr => [...tr.querySelectorAll('td[contenteditable]')].map(td=>td.innerText)); }
function render(rows) {
  const width = Math.max(1,...rows.map(row=>row.length));
  const table = document.createElement('table'); const head=table.createTHead().insertRow();
  for(let i=0;i<=width;i++){const th=document.createElement('th'); th.textContent=i ? '列 '+i : '#';head.append(th);}
  const body=table.createTBody();
  rows.forEach((row,i)=>{const tr=body.insertRow();tr.insertCell().textContent=i+1;for(let j=0;j<width;j++){const td=tr.insertCell();td.contentEditable='true';td.setAttribute('aria-label',`第 ${i+1} 行第 ${j+1} 列`);td.textContent=row[j]??'';td.addEventListener('paste',e=>{e.preventDefault();document.execCommand('insertText',false,e.clipboardData.getData('text/plain'));});}});
  $('tablearea').replaceChildren(table);$('count').textContent=`${rows.length} 行 · ${width} 列`;$('export').disabled=!rows.length || busy;
}
async function select(file) {
  if(busy)return;
  if(!file || !['image/png','image/jpeg','image/webp'].includes(file.type)){status('请选择 JPG、PNG 或 WebP 图片。',true);return;}
  if(file.size>15*1024*1024){status('图片超过 15 MB，请压缩后重试。',true);return;}
  const url=URL.createObjectURL(file); const test=new Image();test.src=url;
  try{await test.decode();if(test.naturalWidth*test.naturalHeight>25000000)throw Error('图片尺寸超过 2500 万像素，请缩小后重试。');}
  catch(error){URL.revokeObjectURL(url);status(error.message.startsWith('图片尺寸')?error.message:'无法读取这张图片，请换一张重试。',true);return;}
  if(objectURL && objectURL!==originalURL)URL.revokeObjectURL(objectURL);if(originalURL)URL.revokeObjectURL(originalURL);originalURL=objectURL=url;original=selected=file;sourceName=file.name.replace(/\.[^.]+$/,'');
  sourceWidth=test.naturalWidth;sourceHeight=test.naturalHeight;corners=[[0,0],[sourceWidth-1,0],[sourceWidth-1,sourceHeight-1],[0,sourceHeight-1]];
  $('image').src=url;$('drop').style.display='none';$('preview').style.display='block';$('filename').textContent=file.name;$('filemeta').textContent=`${test.naturalWidth} × ${test.naturalHeight}`;$('recognize').disabled=true;
  $('raw').value='';$('tablearea').replaceChildren();$('count').textContent='尚无识别结果';$('export').disabled=true;status('正在定位单据四角…');$('progress').style.display='none';
  correctionMode(true);busy=true;['choose','replace','demo','rectify','use-original'].forEach(id=>$(id).disabled=true);
  try{
    const response=await fetch('/api/corners',{method:'POST',headers:{'Content-Type':file.type},body:file});
    if(!response.ok)throw Error('自动定位暂不可用，请手动调整四角。');
    const data=await response.json();corners=data.corners;drawCorners();
    status(data.detected?'已定位单据边界，请检查四角后点击“校正并预览”。':'未可靠定位纸张边缘，请手动调整四角；端正图片可直接使用原图。');
  }catch(error){status(error.message,true);}
  finally{busy=false;['choose','replace','demo','rectify','use-original'].forEach(id=>$(id).disabled=false);drawCorners();}

}

function drawCorners() {
  $('corner-overlay').setAttribute('viewBox',`0 0 ${sourceWidth} ${sourceHeight}`);
  $('corner-polygon').setAttribute('points',corners.map(p=>p.join(',')).join(' '));
  document.querySelectorAll('.corner').forEach((button,i)=>{button.style.left=100*corners[i][0]/sourceWidth+'%';button.style.top=100*corners[i][1]/sourceHeight+'%';button.disabled=busy;});
}
function correctionMode(editing) {
  $('correction-stage').classList.toggle('editing',editing);$('correction-help').hidden=!editing;
  $('rectify').hidden=$('use-original').hidden=!editing;$('edit-corners').hidden=editing;
  if(editing){$('filemeta').textContent=`${sourceWidth} × ${sourceHeight}`;$('image').src=originalURL;$('correction-stage').style.maxWidth=(480*sourceWidth/sourceHeight)+'px';drawCorners();$('recognize').disabled=true;}
}
function clearResult() {
  $('raw').value='';$('tablearea').replaceChildren();$('count').textContent='尚无识别结果';$('export').disabled=true;
}
document.querySelectorAll('.corner').forEach((button,i)=>{
  const move=(x,y)=>{corners[i]=[Math.max(0,Math.min(sourceWidth-1,x)),Math.max(0,Math.min(sourceHeight-1,y))];drawCorners();};
  button.onpointerdown=e=>{if(busy)return;e.preventDefault();button.focus();button.setPointerCapture(e.pointerId);};
  button.onpointermove=e=>{if(busy||!button.hasPointerCapture(e.pointerId))return;const box=$('correction-stage').getBoundingClientRect();move((e.clientX-box.left)*sourceWidth/box.width,(e.clientY-box.top)*sourceHeight/box.height);};
  button.onpointerup=e=>{if(button.hasPointerCapture(e.pointerId))button.releasePointerCapture(e.pointerId);};
  button.onkeydown=e=>{const step=e.shiftKey?10:1;const delta={ArrowLeft:[-step,0],ArrowRight:[step,0],ArrowUp:[0,-step],ArrowDown:[0,step]}[e.key];if(!busy&&delta){e.preventDefault();move(corners[i][0]+delta[0],corners[i][1]+delta[1]);}};
});
$('use-original').onclick=()=>{if(busy)return;selected=original;$('image').src=originalURL;correctionMode(false);$('recognize').disabled=false;clearResult();status('已使用原图，点击“开始识别”。');};
$('edit-corners').onclick=()=>{if(busy)return;correctionMode(true);status('正在调整原图四角，确认完整单据范围后重新校正。');};
$('rectify').onclick=async()=>{
  if(busy||!original)return;busy=true;['rectify','use-original','replace','demo','choose'].forEach(id=>$(id).disabled=true);drawCorners();status('正在校正旋转与透视…');
  try{
    const response=await fetch('/api/rectify',{method:'POST',headers:{'Content-Type':original.type,'X-Document-Corners':JSON.stringify(corners)},body:original});
    if(!response.ok){const data=await response.json();throw Error(data.error||'校正失败，请重试。');}
    const blob=await response.blob();const nextURL=URL.createObjectURL(blob);const preview=new Image();preview.src=nextURL;
    try{await preview.decode();}catch(error){URL.revokeObjectURL(nextURL);throw Error('无法读取校正预览，请重试。');}
    if(objectURL!==originalURL)URL.revokeObjectURL(objectURL);objectURL=nextURL;selected=new File([blob],sourceName+'-校正.png',{type:'image/png'});
    $('image').src=nextURL;$('correction-stage').style.maxWidth=(480*preview.naturalWidth/preview.naturalHeight)+'px';correctionMode(false);clearResult();$('recognize').disabled=false;
    $('filemeta').textContent=`校正后 ${preview.naturalWidth} × ${preview.naturalHeight}`;status('校正预览已就绪，请检查横竖方向及内容是否完整，再点击“开始识别”。');
  }catch(error){status(error.message,true);}
  finally{busy=false;['rectify','use-original','replace','demo','choose'].forEach(id=>$(id).disabled=false);drawCorners();}
};

$('choose').onclick=$('replace').onclick=()=>$('file').click();
$('file').onchange=e=>{select(e.target.files[0]);e.target.value='';};
$('drop').ondragover=e=>{e.preventDefault();$('drop').classList.add('over');};
$('drop').ondragleave=()=>$('drop').classList.remove('over');
$('drop').ondrop=e=>{e.preventDefault();$('drop').classList.remove('over');select(e.dataTransfer.files[0]);};
$('recognize').onclick=async()=>{
  if(!selected||busy)return;
  busy=true;['recognize','replace','demo','edit-corners','addrow','addcol','rebuild','export','raw'].forEach(id=>$(id).disabled=true);$('progress').style.display='block';$('progress').removeAttribute('value');status('正在识别文字与表格结构，首次运行需下载模型…');
  try{
    const response=await fetch('/api/recognize',{method:'POST',headers:{'Content-Type':selected.type},body:selected});
    if(response.status===501||response.status===404)throw Error('请使用 Python 识别服务启动程序，当前服务只提供静态页面。');
    const data=await response.json();
    if(!response.ok)throw Error(data.error||'表格识别失败，请重试。');
    $('raw').value=data.text;
    render(mergeFirstRows(data.rows));status('识别完成（TableStructureRec），请校对前四列及右侧物料明细后导出。');$('progress').value=1;
  }catch(error){console.error(error);status(error.message==='Failed to fetch'?'无法连接本地识别服务，请确认服务正在运行。':error.message,true);}
  finally{busy=false;['recognize','replace','demo','edit-corners','addrow','addcol','rebuild','raw'].forEach(id=>$(id).disabled=false);$('export').disabled=!readTable().length;}

};
$('rebuild').onclick=()=>{render(mergeFirstRows(parseText($('raw').value)));status('已从原文生成表格，左侧四列已拆分标题与值，物料明细保留在右侧。');};
$('addrow').onclick=()=>{const rows=readTable();rows.push(Array(Math.max(1,rows[0]?.length||4)).fill(''));render(rows);};
$('addcol').onclick=()=>{const rows=readTable();if(!rows.length)rows.push([]);rows.forEach(row=>row.push(''));render(rows);};
$('export').onclick=()=>{
  if(!window.XLSX){status('Excel 组件未加载，请刷新页面。',true);return;}
  const rows=readTable();if(!rows.length)return;
  try{const sheet=XLSX.utils.aoa_to_sheet(rows);sheet['!cols']=Array.from({length:Math.max(...rows.map(row=>row.length))},()=>({wch:22}));const book=XLSX.utils.book_new();XLSX.utils.book_append_sheet(book,sheet,'识别结果');XLSX.writeFile(book,sourceName+'-识别结果.xlsx');status('已导出 Excel（文本单元格），编号前导零保持不变。');}catch(error){status('导出失败，请重试。',true);console.error(error);}
};
$('demo').onclick=()=>{
  if(busy)return;const canvas=document.createElement('canvas');canvas.width=1600;canvas.height=1050;const c=canvas.getContext('2d');c.fillStyle='white';c.fillRect(0,0,1600,1050);c.fillStyle='#111';c.font='bold 54px sans-serif';c.textAlign='center';c.fillText('采购订单 PURCHASE ORDER',800,120);c.textAlign='left';c.font='32px sans-serif';c.fillText('订单编号 PO20261019001',100,220);c.fillText('日期 2026-10-19',100,285);c.fillText('供应商 示例工业设备有限公司',100,350);
  const rows=[['物料编码','物料名称','数量','单价','金额'],['A001','标准轴承','20','35.00','700.00'],['A002','固定螺栓','100','2.50','250.00'],['A003','密封垫圈','50','6.00','300.00']];const x=[100,400,830,1050,1300];rows.forEach((row,i)=>row.forEach((text,j)=>c.fillText(text,x[j],480+i*95)));c.fillText('合计 CNY 1250.00',100,930);canvas.toBlob(blob=>select(new File([blob],'示例采购订单.png',{type:'image/png'})),'image/png');
};
