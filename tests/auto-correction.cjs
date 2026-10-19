const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

async function upload({changed = true, alignFails = false} = {}) {
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
      if (url === '/api/align') return {ok: !alignFails, headers: {get: () => JSON.stringify({changed,angle:changed?5:0})}, blob: async () => ({}), json: async () => ({error: '文字方向检查失败'})};
      throw Error('Unexpected request: ' + url);
    }
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../dist/app.js'), 'utf8'), context);
  await context.select({type: 'image/png', size: 100, name: 'photo.png'});
  return {calls, element};
}

(async () => {
  let result = await upload();
  assert.deepEqual(result.calls, ['/api/align'], 'upload checks text directions without paper detection');
  assert.equal(result.element('recognize').disabled, false);
  assert.match(result.element('filemeta').textContent, /校正后/);
  result = await upload({changed: false});
  assert.deepEqual(result.calls, ['/api/align']);
  assert.equal(result.element('recognize').disabled, false, 'upright borderless pictures must be allowed');
  assert.match(result.element('status').textContent, /端正.*无需校正/);
  result = await upload({alignFails: true});
  assert.equal(result.element('recognize').disabled, true);
  assert.equal(result.element('replace').disabled, false);
  assert.match(result.element('status').textContent, /文字方向检查失败/);
  const html = fs.readFileSync(path.join(__dirname, '../dist/index.html'), 'utf8');
  assert.doesNotMatch(html, /id="(?:rectify|use-original|edit-corners)"|class="corner"/, 'no manual corner controls');
  console.log('PASS: text alignment, straight borderless pictures, and alignment error recovery');
})().catch(error => {console.error(error); process.exitCode = 1;});
