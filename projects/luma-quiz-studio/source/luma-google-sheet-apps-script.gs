/**
 * 知光 Luma · Google Sheet 同步腳本
 * 1. 建立或開啟 Google Sheet
 * 2. 擴充功能 > Apps Script，貼上此程式碼
 * 3. 執行 setup() 一次並授權
 * 4. 部署 > 新增部署 > 網頁應用程式
 *    執行身分：我；存取權：任何人
 * 5. 把 Web App URL 貼回 Luma 的設定頁
 */
const SHEET_NAMES = ['Submissions', 'Students', 'QuestionBank', 'Notes', 'Quizzes'];

function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const specs = {
    Submissions: ['Submitted At','Quiz ID','Quiz Title','Class','Class Number','Student ID','Student Name','Score','Band','Started At','Time Used (sec)','Auto Submitted','Answers JSON','Review JSON'],
    Students: ['Class','Number','Name'],
    QuestionBank: ['Question ID','Learning Point','Type','Prompt','Marks','Answer Key','Keywords'],
    Notes: ['Note ID','Subject','Title','Learning Point','Content'],
    Quizzes: ['Quiz ID','Title','Published At','Time Limit','Sections JSON']
  };

  Object.entries(specs).forEach(([name, headers]) => {
    let sh = ss.getSheetByName(name);
    if (!sh) sh = ss.insertSheet(name);
    // Keep rows below the header when setup() is run again after importing CSV data.
    sh.getRange(1, 1, 1, headers.length).setValues([headers]);
    sh.getRange(1, 1, 1, headers.length)
      .setFontWeight('bold')
      .setBackground('#193d2f')
      .setFontColor('#ffffff');
    sh.setFrozenRows(1);
    sh.autoResizeColumns(1, headers.length);
  });

  ss.setActiveSheet(ss.getSheetByName('Submissions'));
  return 'Luma sheets ready';
}

function doGet(e) {
  try {
    const action = e && e.parameter ? e.parameter.action : '';
    if (action === 'roster') {
      const ss = SpreadsheetApp.getActiveSpreadsheet();
      let sheet = ss.getSheetByName('Students');
      if (!sheet) { setup(); sheet = ss.getSheetByName('Students'); }
      const rows = sheet.getDataRange().getValues().slice(1).filter(r => r[0] && r[2]);
      const students = rows.map(r => ({ class: String(r[0]), number: r[1], name: String(r[2]) }));
      if (e.parameter.format === 'json') {
        return ContentService.createTextOutput(JSON.stringify({ ok: true, students }))
          .setMimeType(ContentService.MimeType.JSON);
      }
      return HtmlService.createHtmlOutput(`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Luma 名單接口</title><style>body{font-family:system-ui,sans-serif;background:#f4f3ee;color:#17221b;display:grid;place-items:center;min-height:100vh;margin:0}.card{background:#fffefa;border:1px solid #e4e4dc;border-radius:24px;padding:38px;max-width:560px;margin:20px;box-shadow:0 24px 70px rgba(39,54,44,.09)}h1{font-size:28px;margin:0 0 10px}p{color:#737b75;line-height:1.7}.ok{display:inline-block;background:#dcebe1;color:#315c49;border-radius:100px;padding:5px 10px;font-size:12px;font-weight:700}</style></head><body><main class="card"><span class="ok">接口正常</span><h1>Luma 名單接口已連線</h1><p>這個網址供測驗系統讀取班別及學生姓名，不需要直接分享給學生。</p><p>目前讀取到 <strong>${students.length}</strong> 位學生。程式使用的資料版本為 <code>?action=roster&format=json</code>。</p></main></body></html>`)
        .setTitle('Luma 名單接口')
        .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
    }
    const requestedMode = (e && e.parameter && e.parameter.mode === 'student') ? 'student' : 'teacher';
    const source = HtmlService.createHtmlOutputFromFile('Index').getContent();
    const html = source.replace('__LUMA_SERVER_MODE__', requestedMode);
    return HtmlService.createHtmlOutput(html)
      .setTitle('知光 Luma｜網上測驗卷生成工具')
      .addMetaTag('viewport', 'width=device-width, initial-scale=1')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false, error: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents);
    if (payload.type === 'replaceRoster') return jsonOutput_(replaceRoster(payload));
    if (payload.type === 'aiGenerateQuestions') return jsonOutput_(aiGenerateQuestions(payload));
    if (payload.type === 'submission') return jsonOutput_(saveSubmission(payload));
    throw new Error('Unsupported payload');
  } catch (err) {
    return jsonOutput_({ ok: false, error: err.message });
  }
}

function jsonOutput_(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}

function getRoster() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName('Students');
  if (!sheet) { setup(); sheet = ss.getSheetByName('Students'); }
  const rows = sheet.getDataRange().getValues().slice(1).filter(r => r[0] && r[2]);
  const students = rows.map(r => ({ class: String(r[0]), number: r[1], name: String(r[2]) }));
  return { ok: true, students };
}

function replaceRoster(payload) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let roster = ss.getSheetByName('Students');
  if (!roster) { setup(); roster = ss.getSheetByName('Students'); }
  const rows = (payload.students || []).map(s => [s.class || '', s.number || '', s.name || '']);
  roster.getRange(2, 1, Math.max(roster.getMaxRows() - 1, 1), 3).clearContent();
  if (rows.length) roster.getRange(2, 1, rows.length, 3).setValues(rows);
  return { ok: true, saved: rows.length };
}

function saveSubmission(payload) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName('Submissions');
  if (!sh) { setup(); sh = ss.getSheetByName('Submissions'); }
  sh.appendRow([
    payload.submittedAt || new Date().toISOString(),
    payload.quizId || '',
    payload.quizTitle || '',
    payload.className || '',
    payload.classNumber || '',
    payload.studentId || '',
    payload.studentName || '',
    payload.score ?? '',
    payload.band || '',
    payload.startedAt || '',
    payload.timeUsedSeconds ?? '',
    payload.autoSubmitted ? 'Yes' : 'No',
    JSON.stringify(payload.answers || {}),
    JSON.stringify(payload.review || [])
  ]);
  return { ok: true };
}

function aiGenerateQuestions(payload) {
  return handleDeepSeekGenerate_(payload || {});
}

function handleDeepSeekGenerate_(payload) {
  const props = PropertiesService.getScriptProperties();
  const apiKey = props.getProperty('DEEPSEEK_API_KEY');
  if (!apiKey) throw new Error('DeepSeek API Key 尚未設定。請在 Apps Script 的「專案設定 › 指令碼屬性」加入 DEEPSEEK_API_KEY。');
  const accessCode = props.getProperty('LUMA_AI_TOKEN');
  if (!accessCode) throw new Error('AI 存取碼尚未設定。請在指令碼屬性加入 LUMA_AI_TOKEN。');
  if (String(payload.aiToken || '') !== accessCode) throw new Error('AI 存取碼不正確。');
  const endpoint = props.getProperty('DEEPSEEK_API_URL') || 'https://api.deepseek.com/chat/completions';
  const model = props.getProperty('DEEPSEEK_MODEL') || 'deepseek-flash';
  const note = payload.note || {};
  const requestedTypes = Array.isArray(payload.types) ? payload.types.filter(t => ['multiple_choice','matching','short','long','image','true_false','video','fill_blank','drawing'].includes(t)) : ['multiple_choice'];
  const types = requestedTypes.length ? requestedTypes : ['multiple_choice'];
  const count = Math.max(1, Math.min(12, Number(payload.count) || types.length));
  const noteContent = String(note.content || '').slice(0, 14000);
  if (noteContent.trim().length < 10) throw new Error('筆記內容太短，未能生成題目。');
  const instructions = [
    '你是香港中學老師的測驗題目設計助手。',
    '你必須只根據使用者提供的教學筆記出題，不可加入筆記以外的知識、人物、數字或事實。',
    '使用繁體中文（香港），用字正面、清楚、適合中學生。',
    '每道題的 sourceQuote 必須是筆記原文中的完整句子或連續片段，不可自行改寫。',
    '不要輸出 Markdown、程式碼圍欄、前言或解釋；只輸出一個有效 JSON 物件。',
    'JSON 物件格式必須是：{"questions":[{"type":"multiple_choice","prompt":"題目","options":["甲","乙","丙","丁"],"correctIndex":0,"answer":"","acceptedAnswers":[],"keywords":[],"rightOptions":[],"pairs":[],"correct":true,"marks":2,"sourceQuote":"筆記原句","explanation":"答案說明","mediaTerms":[]}]}。',
    'type 只可使用以下其中一個值：multiple_choice、matching、short、long、image、true_false、video、fill_blank、drawing。',
    '選擇題／圖片題／影片題：提供 3 至 4 個 options 及 0-based correctIndex。',
    '正反題：提供 boolean correct；不可使用 options。',
    '填充題：answer 為要填入的詞；acceptedAnswers 可包含同義答案。',
    '配對題：pairs 為 [{"left":"概念","right":"相符描述"}]，rightOptions 可留空。',
    '簡答題及詳答題：提供 keywords；答案不應超出筆記。',
    '繪圖題：提供清楚的繪圖指示，answer 留空。',
    'sourceQuote 和 explanation 必須針對每道題提供。'
  ].join('\n');
  const userPrompt = `教學筆記標題：${note.title || ''}\n學習點：${note.learningPoint || ''}\n題目數量：${count}\n指定題型：${types.join(', ')}\n\n請平均使用指定題型，生成剛好 ${count} 道題。\n\n筆記原文：\n${noteContent}`;
  const requestBody = {
    model,
    messages: [
      { role: 'system', content: instructions },
      { role: 'user', content: userPrompt }
    ],
    response_format: { type: 'json_object' },
    temperature: 0.2,
    max_tokens: 8000,
    stream: false
  };
  const response = UrlFetchApp.fetch(endpoint, {
    method: 'post',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + apiKey },
    payload: JSON.stringify(requestBody),
    muteHttpExceptions: true
  });
  const status = response.getResponseCode();
  const responseText = response.getContentText();
  if (status < 200 || status >= 300) throw new Error('DeepSeek API 回應錯誤（' + status + '）：' + responseText.slice(0, 500));
  const data = JSON.parse(responseText);
  const message = data && data.choices && data.choices[0] && data.choices[0].message;
  let content = message ? message.content : '';
  if (Array.isArray(content)) content = content.map(part => typeof part === 'string' ? part : (part.text || '')).join('');
  if (!content || !String(content).trim()) throw new Error('DeepSeek 沒有回傳題目內容。');
  let parsed;
  try { parsed = JSON.parse(content); } catch (err) { throw new Error('DeepSeek 回傳的題目 JSON 格式不正確。'); }
  const questions = normalizeDeepSeekQuestions_(parsed.questions || [], note);
  if (!questions.length) throw new Error('DeepSeek 沒有產生可用的題目。');
  return { ok: true, model, questions };
}

function normalizeDeepSeekQuestions_(input, note) {
  const allowed = ['multiple_choice','matching','short','long','image','true_false','video','fill_blank','drawing'];
  return (Array.isArray(input) ? input : []).map((q, index) => {
    const type = allowed.includes(String(q.type)) ? String(q.type) : 'short';
    const options = Array.isArray(q.options) ? q.options.map(String).filter(Boolean) : [];
    let correctIndex = Number(q.correctIndex);
    if (!Number.isInteger(correctIndex) || correctIndex < 0 || correctIndex >= options.length) correctIndex = 0;
    const pairsInput = Array.isArray(q.pairs) ? q.pairs : [];
    const rightOptions = pairsInput.map(p => String(p.right || ''));
    const pairs = {};
    pairsInput.forEach((p, i) => { if (p && p.left) pairs[String(p.left)] = i; });
    return {
      type,
      prompt: String(q.prompt || '').trim(),
      options,
      correctIndex: ['multiple_choice','image','video'].includes(type) ? correctIndex : null,
      correct: type === 'true_false' ? q.correct === true : null,
      answer: String(q.answer || ''),
      acceptedAnswers: Array.isArray(q.acceptedAnswers) ? q.acceptedAnswers.map(String) : [],
      keywords: Array.isArray(q.keywords) ? q.keywords.map(String) : [],
      rightOptions: rightOptions.length ? rightOptions : (Array.isArray(q.rightOptions) ? q.rightOptions.map(String) : []),
      pairs,
      marks: Math.max(1, Math.min(20, Number(q.marks) || 2)),
      sourceQuote: String(q.sourceQuote || '').trim(),
      explanation: String(q.explanation || '').trim(),
      difficulty: String(q.difficulty || (index > 4 ? '進階' : '基礎')),
      mediaTerms: Array.isArray(q.mediaTerms) ? q.mediaTerms.map(String).slice(0, 4) : [],
      learningPoint: String(note.learningPoint || '')
    };
  }).filter(q => q.prompt);
}

function authorizeLumaServices() {
  const endpoint = PropertiesService.getScriptProperties().getProperty('DEEPSEEK_API_URL') || 'https://api.deepseek.com/chat/completions';
  UrlFetchApp.getRequest(endpoint, {
    method: 'post',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer placeholder' },
    payload: JSON.stringify({ ping: true })
  });
  return 'Luma external request authorization ready';
}



