const assert = require('node:assert/strict');
const {parseText,exportRows,exportSheet} = require('../dist/core.js');
const XLSX = require('../dist/vendor/xlsx.full.min.js');
const rows = [['编号','名称'],['001',''],['',''],['003','轴承']];
assert.deepEqual(parseText(rows.map(row=>row.join('\t')).join('\n')),rows, 'blank cells and rows survive text rebuild');
assert.deepEqual(parseText(''),[]);
assert.deepEqual(parseText('名称  数量\n轴承  20'),[['名称','数量'],['轴承','20']]);
const combined = exportRows('采购申请单\n部门：设备部',rows,'制单 核批 承办');
assert.deepEqual(combined,[
  ['采购申请单','部门','编号','名称'],
  ['','设备部','001',''],
  ['','','',''],
  ['','','003','轴承'],
  ['制单 核批 承办','','','']
], 'heading fields go on the left, values appear once, footer follows the full table');
const heading='采购订单PURCHASEORDER\n订单编号PO20261019001\n日期2026-10-19\n供应商示例工业设备有限公司';
const details=[['物料编码','物料名称','数量','单价','金额'],['A001','标准轴承','20','35.00','700.00']];
const purchase=exportRows(heading,details,'合计 CNY 700.00');
assert.deepEqual(purchase[0].slice(0,4),['采购订单','订单编号','日期','供应商']);
assert.deepEqual(purchase[1].slice(0,4),['PURCHASEORDER','PO20261019001','2026-10-19','示例工业设备有限公司']);
assert.deepEqual(purchase[0].slice(4),details[0]);
assert.equal(exportRows('供应商：',rows,'')[0][0],'供应商');
assert.equal(exportRows('供应商：',rows,'')[1][0],'');
assert.deepEqual(exportRows('',rows,''),rows,'no empty metadata columns when no heading exists');
assert.deepEqual(exportRows('标题', [['物料','数量']], ''),[['标题','物料','数量'],['','','']]);
const sheet=exportSheet(XLSX,'采购申请单\n部门：设备部',rows,'制单 核批 承办');
const workbook=XLSX.utils.book_new();
XLSX.utils.book_append_sheet(workbook,sheet,'识别结果');
const restored=XLSX.read(XLSX.write(workbook,{type:'buffer',bookType:'xlsx'}),{type:'buffer',cellStyles:true});
const output=restored.Sheets['识别结果'];
assert.equal(output.C2.v,'001');
assert.equal(output.C2.t,'s');
assert.equal(output.C2.z,'@');
assert.equal(output.B2.v,'设备部');
assert.equal(output.A5.v,'制单 核批 承办');
assert.deepEqual(output['!merges'],[{s:{r:4,c:0},e:{r:4,c:3}}]);
assert.equal(output['!cols'].length,4);
assert.deepEqual(XLSX.utils.sheet_to_json(output,{header:1,defval:'',blankrows:true}),combined);
console.log('PASS: dynamic heading columns on left, values once, blank body rows, merged footer below, XLSX leading zeros');
