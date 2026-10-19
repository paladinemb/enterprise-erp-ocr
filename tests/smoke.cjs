const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { mergeFirstRows } = require('../dist/core.js');
const XLSX = require('../dist/vendor/xlsx.full.min.js');
const expected = require('./fixtures/expected-first-four.json');
(async () => {
  const response = await fetch('http://127.0.0.1:8765/api/recognize', {
    method: 'POST', headers: {'Content-Type':'image/png'},
    body: fs.readFileSync(path.join(__dirname, 'fixtures/example-purchase-order.png'))
  });
  const result = await response.json();
  assert.equal(response.status, 200, JSON.stringify(result));
  assert.equal(result.engine, 'TableStructureRec');
  const rows = mergeFirstRows(result.rows);
  assert.deepEqual(rows.map(row=>row.slice(0,4)), expected);
  assert.deepEqual(rows.slice(1,4).map(row=>row.slice(4)), [
    ['A001','标准轴承','20','35.00','700.00'],
    ['A002','固定螺栓','100','2.50','250.00'],
    ['A003','密封垫圈','50','6.00','300.00']
  ]);
  assert.match(rows[4][4], /1250\.00/);
  if (process.argv[2]) {
    const workbook = XLSX.read(fs.readFileSync(process.argv[2]), {type:'buffer'});
    const sheet = workbook.Sheets['识别结果'];
    const exported = XLSX.utils.sheet_to_json(sheet, {header:1,defval:''});
    assert.deepEqual(exported.map(row=>row.slice(0,4)), expected);
    assert.equal(sheet.B2.t,'s');
    assert.equal(sheet.E2.v,'A001');
    assert.equal(sheet.I4.v,'300.00');
  }
  console.log('PASS: real TableStructureRec API, manual first-four fixture, all item rows and total, browser-exported XLSX');
})().catch(error=>{console.error(error);process.exitCode=1;});
