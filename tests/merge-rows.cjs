const assert=require('node:assert/strict');
const {parseText,headerFields,footerFields,exportRows,exportSheet}=require('../dist/core.js');
const XLSX=require('../dist/vendor/xlsx.full.min.js');
const rows=[['编号','名称'],['001',''],['',''],['003','轴承']];
assert.deepEqual(parseText(rows.map(row=>row.join('\t')).join('\n')),rows);
assert.deepEqual(parseText(''),[]);
assert.deepEqual(headerFields('采购订单PURCHASEORDER\n订单编号PO20261019001\n日期2026-10-19\n供应商示例工业设备有限公司'),[
 ['采购订单','PURCHASEORDER'],['订单编号','PO20261019001'],['日期','2026-10-19'],['供应商','示例工业设备有限公司']
]);
assert.deepEqual(headerFields('地址：某市场2-153电话：00000000000\n客户名称：示例客户 客户电话： No.XS-0001'),[
 ['地址','某市场2-153'],['电话','00000000000'],['客户名称','示例客户'],['客户电话',''],['No.','XS-0001']
]);
assert.deepEqual(headerFields('物资采购申请单'),[['单据名称','物资采购申请单']]);
assert.deepEqual(headerFields('示例商贸有限公司\n销售单'),[['公司名称','示例商贸有限公司'],['单据名称','销售单']]);
assert.deepEqual(footerFields('合计CNY1250.00\n制单 核批 承办\n红色日期标记：2012 11 19'),[
 ['合计','CNY1250.00'],['制单',''],['核批',''],['承办',''],['红色日期标记','2012 11 19']
]);
assert.deepEqual(footerFields('制单：张三 核批：李四 承办：王五'),[['制单','张三'],['核批','李四'],['承办','王五']]);
assert.deepEqual(footerFields('收货人 张三\n没有明确分隔的说明'),[['收货人','张三'],['没有明确分隔的说明','']]);
const heading=[['采购申请单',''],['部门','设备部']];
const footer=[['制单','张三'],['核批','李四'],['承办','']];
const combined=exportRows(heading,rows,footer);
assert.deepEqual(combined,[
 ['采购申请单','部门','编号','名称'],['','设备部','001',''],['','','',''],['','','003','轴承'],
 ['制单','张三','',''],['核批','李四','',''],['承办','','','']
]);
assert.deepEqual(exportRows([],rows,[]),rows);
assert.deepEqual(exportRows([['自定义：字段','第一行\n第二行']],rows,[])[1].slice(0,1),['第一行\n第二行'],'edited values must not be reparsed');
const sheet=exportSheet(XLSX,heading,rows,footer);
const book=XLSX.utils.book_new();XLSX.utils.book_append_sheet(book,sheet,'识别结果');
const restored=XLSX.read(XLSX.write(book,{type:'buffer',bookType:'xlsx'}),{type:'buffer',cellStyles:true}).Sheets['识别结果'];
assert.equal(restored.C2.v,'001');assert.equal(restored.C2.t,'s');assert.equal(restored.C2.z,'@');
assert.equal(restored.B5.v,'张三');assert.equal(restored.B6.v,'李四');
assert.deepEqual(restored['!merges'],[4,5,6].map(r=>({s:{r,c:1},e:{r,c:3}})));
assert.deepEqual(XLSX.utils.sheet_to_json(restored,{header:1,defval:'',blankrows:true}),combined);
console.log('PASS: two-column heading/footer fields, signature splitting, edited values, isolated body rows, XLSX layout and leading zeros');
