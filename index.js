const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs');
const path = require('path');

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const RUNTIME_DIR = path.join(__dirname, 'runtime');
const INPUT_FILE = path.join(RUNTIME_DIR, 'opencode_input.txt');
const OUTPUT_FILE = path.join(RUNTIME_DIR, 'opencode_output.txt');

let bot;
let bridgeState = {
  paused: false,
  lastProcessedInstruction: '',
  manualConfirmationRequired: null
};

function ensureRuntimeDir() {
  if (!fs.existsSync(RUNTIME_DIR)) {
    fs.mkdirSync(RUNTIME_DIR, { recursive: true });
  }
}

function loadJsonWithFallback(filePath) {
  try {
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, 'utf8');
      if (content.trim()) {
        return JSON.parse(content);
      }
    }
  } catch (e) {
    console.error(`Error loading JSON from ${filePath}:`, e.message);
  }
  return null;
}

function saveJson(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
}

function shouldRequestApproval(instruction) {
  if (!instruction) return false;
  const riskyActions = ['merge', 'push', 'force-push', 'force_push', 'lane_release', 'resume'];
  const lower = instruction.toLowerCase();
  return riskyActions.some(action => lower.includes(action));
}

function sendApprovalKeyboard(chatId, instruction) {
  if (!bot) return;
  
  const keyboard = {
    inline_keyboard: [
      [
        { text: '✅ 同意', callback_data: `approve:${instruction}` },
        { text: '❌ 拒絕', callback_data: `reject:${instruction}` }
      ],
      [
        { text: '⏸ 暫停', callback_data: `pause:${instruction}` }
      ]
    ]
  };
  
  const preview = instruction.length > 100 ? instruction.substring(0, 100) + '...' : instruction;
  bot.sendMessage(chatId, `⚠️ 高風險操作需要審批:\n\n${preview}`, keyboard);
}

function handleCallbackQuery(callbackQuery) {
  const data = callbackQuery.data;
  const chatId = callbackQuery.message.chat.id;
  
  const [action, instruction] = data.split(':');
  
  switch (action) {
    case 'approve':
      bridgeState.paused = false;
      const approveResponse = {
        action: 'approve',
        instruction: instruction,
        timestamp: new Date().toISOString(),
        next_opencode_instruction: instruction
      };
      ensureRuntimeDir();
      fs.writeFileSync(INPUT_FILE, JSON.stringify(approveResponse, null, 2), 'utf8');
      bot.answerCallbackQuery(callbackQuery.id, { text: '✅ 已同意' });
      bot.sendMessage(chatId, '✅ 已同意執行');
      break;
      
    case 'reject':
      bridgeState.paused = false;
      const rejectResponse = {
        action: 'reject',
        instruction: instruction,
        timestamp: new Date().toISOString(),
        status: 'rejected'
      };
      ensureRuntimeDir();
      fs.writeFileSync(INPUT_FILE, JSON.stringify(rejectResponse, null, 2), 'utf8');
      bot.answerCallbackQuery(callbackQuery.id, { text: '❌ 已拒絕' });
      bot.sendMessage(chatId, '❌ 已拒絕執行');
      break;
      
    case 'pause':
      bridgeState.paused = true;
      bot.answerCallbackQuery(callbackQuery.id, { text: '⏸ 已暫停' });
      bot.sendMessage(chatId, '⏸ Bridge 流程已暫停');
      break;
  }
}

function pollForNewInput() {
  try {
    if (!fs.existsSync(INPUT_FILE)) {
      return { status: 'waiting', message: 'runtime/opencode_input.txt not found' };
    }
    
    const content = fs.readFileSync(INPUT_FILE, 'utf8').trim();
    if (!content) {
      return { status: 'waiting', message: 'Input file is empty' };
    }
    
    const parsed = JSON.parse(content);
    
    if (parsed.instruction === bridgeState.lastProcessedInstruction) {
      return { status: 'no_change', message: 'Same as previous instruction' };
    }
    
    return { status: 'new', data: parsed };
  } catch (e) {
    return { status: 'error', message: e.message };
  }
}

function writeOutput(result) {
  ensureRuntimeDir();
  fs.writeFileSync(OUTPUT_FILE, result, 'utf8');
}

function main() {
  if (!TOKEN) {
    console.log('TELEGRAM_BOT_TOKEN not set - running in simulation mode');
    console.log('Bridge ready for manual input via runtime/opencode_input.txt');
    return;
  }
  
  bot = new TelegramBot(TOKEN, { polling: true });
  bot.on('callback_query', handleCallbackQuery);
  
  console.log('Telegram bot started with approval flow');
  console.log('Inline keyboard: ✅ 同意 | ❌ 拒絕 | ⏸ 暫停');
  
  setInterval(() => {
    if (bridgeState.paused) return;
    
    const pollResult = pollForNewInput();
    if (pollResult.status === 'new' && pollResult.data) {
      if (shouldRequestApproval(pollResult.data.instruction)) {
        console.log('High-risk operation detected, requesting Telegram approval');
      }
    }
  }, 2000);
}

main();

module.exports = {
  sendApprovalKeyboard,
  shouldRequestApproval,
  handleCallbackQuery,
  pollForNewInput,
  writeOutput
};