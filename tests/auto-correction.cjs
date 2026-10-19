const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

async function upload({detected = true, rectifyFails = false} = {}) {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      disabled: false, hidden: false, style: {}, textContent: '',
      classList: {toggle() {}}, setAttribute() {}, replaceChildren() {}
    });
    return elements.get(id);
  };
  const calls = [];
  class Image {
    naturalWidth = 1900; naturalHeight = 1450;
    async decode() {}
  }
  const context = vm.createContext({
    document: {getElementById: element, querySelectorAll: () => []},
    Image, File: class {constructor(parts, name, options) {this.name = name; this.type = options.type;}},
    URL: {createObjectURL: () => 'blob:preview', revokeObjectURL() {}},
    fetch: async url => {
      calls.push(url);
      if (url === '/api/corners') return {ok: true, json: async () => ({detected, corners: [[160,180],[1750,55],[1690,1320],[60,1130]]})};
      if (url === '/api/rectify') return {ok: !rectifyFails, blob: async () => ({}), json: async () => ({error: '校正失败'})};
      throw Error('Unexpected request: ' + url);
    }
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../dist/app.js'), 'utf8'), context);
  await context.select({type: 'image/png', size: 100, name: 'photo.png'});
  return {calls, element};
}

(async () => {
  let result = await upload();
  assert.deepEqual(result.calls, ['/api/corners', '/api/rectify'], 'upload must automatically rectify detected corners');
  assert.equal(result.element('recognize').disabled, false);
  assert.match(result.element('filemeta').textContent, /校正后/);
  result = await upload({detected: false});
  assert.deepEqual(result.calls, ['/api/corners'], 'uncertain boundaries must stop before rectification');
  assert.equal(result.element('recognize').disabled, true);
  assert.equal(result.element('replace').disabled, false);
  assert.match(result.element('status').textContent, /边界不可靠|校正失败/);
  result = await upload({rectifyFails: true});
  assert.equal(result.element('recognize').disabled, true);
  assert.equal(result.element('replace').disabled, false);
  assert.match(result.element('status').textContent, /边界不可靠|校正失败/);
  assert.match(result.element('status').textContent, /校正失败/);
  const html = fs.readFileSync(path.join(__dirname, '../dist/index.html'), 'utf8');
  assert.doesNotMatch(html, /id="(?:rectify|use-original|edit-corners)"|class="corner"/, 'no manual corner controls');
  console.log('PASS: upload auto-correction, uncertain boundaries, and correction errors block recognition');
})().catch(error => {console.error(error); process.exitCode = 1;});
