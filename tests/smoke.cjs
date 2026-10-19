const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const XLSX = require('../dist/vendor/xlsx.full.min.js');
async function post(endpoint,body,headers={}) {
  const response = await fetch('http://127.0.0.1:8765/api/'+endpoint,{method:'POST',headers:{'Content-Type':'image/png',...headers},body});
  if (!response.ok) throw Error(await response.text());
  return response;
}
async function photoResult(file,type) {
  const photo=fs.readFileSync(file);
  const boundary=await (await post('corners',photo,{'Content-Type':type})).json();
  assert.equal(boundary.detected,true);
  const corrected=Buffer.from(await (await post('rectify',photo,{'Content-Type':type,'X-Document-Corners':JSON.stringify(boundary.corners)})).arrayBuffer());
  return (await post('recognize',corrected)).json();
}
(async () => {
  const sample=await (await post('recognize',fs.readFileSync(path.join(__dirname,'fixtures/example-purchase-order.png')))).json();
  assert.equal(sample.header_rows,1);
  assert.match(sample.header.join('\n'),/PO20261019001/);
  assert.deepEqual(sample.rows,[
    ['物料编码','物料名称','数量','单价','金额'],
    ['A001','标准轴承','20','35.00','700.00'],
    ['A002','固定螺栓','100','2.50','250.00'],
    ['A003','密封垫圈','50','6.00','300.00']
  ]);
  assert.match(sample.footer.join('\n'),/1250\.00/);
  const projected=await photoResult(path.join(__dirname,'fixtures/perspective-purchase-order.png'),'image/png');
  assert.deepEqual(projected.rows,sample.rows);
  assert.match(projected.header.join('\n'),/PO20261019001/);
  assert.match(projected.footer.join('\n'),/1250\.00/);
  console.log('PASS: wireless purchase order, perspective correction, separate headings and totals');
  if (process.argv[2]) {
    const actual=await photoResult(process.argv[2],'image/jpeg');
    assert.deepEqual(actual.header,['物资采购申请单']);
    assert.equal(actual.header_rows,1);
    assert.deepEqual(actual.rows[0],['编号','物资名称','规格型号','单位','数量','备注']);
    assert.deepEqual(actual.rows.slice(1),Array.from({length:8},(_,i)=>[String(i+1),'','','','','']));
    assert.match(actual.footer.join('\n'),/制单.*核批.*承办/);
    assert.ok(actual.footer.includes('红色日期标记：2012 11 19'));
    assert.ok(actual.warnings.some(text=>text.includes('重叠')));
    console.log('PASS: actual photo -> full paper -> title + six columns + eight blank body rows + footer/date overlay');
  }
  if (process.argv[3]) {
    const book=XLSX.read(fs.readFileSync(process.argv[3]),{type:'buffer'});
    const sheet=book.Sheets['识别结果'];
    const rows=XLSX.utils.sheet_to_json(sheet,{header:1,defval:'',blankrows:true});
    assert.equal(rows[0][0],'物资采购申请单');
    assert.deepEqual(rows[2],['编号','物资名称','规格型号','单位','数量','备注']);
    assert.deepEqual(rows.slice(3,11).map(row=>row[0]),['1','2','3','4','5','6','7','8']);
    assert.equal(sheet.A4.t,'s');
    assert.match(rows.slice(12).map(row=>row.join(' ')).join('\n'),/制单.*核批.*承办/);
    console.log('PASS: browser XLSX export includes all sections and eight empty body rows');
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
