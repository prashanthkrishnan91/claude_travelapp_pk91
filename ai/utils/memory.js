#!/usr/bin/env node
/**
 * Claude Flow Memory Helper
 * Simple key-value memory for cross-session context persistence.
 *
 * Usage:
 *   node ai/utils/memory.js set <key> <value>
 *   node ai/utils/memory.js get <key>
 *   node ai/utils/memory.js delete <key>
 *   node ai/utils/memory.js keys
 *   node ai/utils/memory.js clear
 */

'use strict';

const fs = require('fs');
const path = require('path');

const MEMORY_DIR = path.join(process.cwd(), '.claude-flow', 'data');
const MEMORY_FILE = path.join(MEMORY_DIR, 'memory.json');

function loadMemory() {
  try {
    if (fs.existsSync(MEMORY_FILE)) {
      return JSON.parse(fs.readFileSync(MEMORY_FILE, 'utf-8'));
    }
  } catch (_) {
    // Corrupted file — start fresh
  }
  return {};
}

function saveMemory(memory) {
  fs.mkdirSync(MEMORY_DIR, { recursive: true });
  fs.writeFileSync(MEMORY_FILE, JSON.stringify(memory, null, 2));
}

const commands = {
  get(key) {
    const memory = loadMemory();
    const value = key ? memory[key] : memory;
    console.log(JSON.stringify(value, null, 2));
    return value;
  },

  set(key, value) {
    if (!key) {
      console.error('Error: key is required');
      process.exit(1);
    }
    const memory = loadMemory();
    memory[key] = value;
    memory._updated = new Date().toISOString();
    saveMemory(memory);
    console.log(`Set: ${key}`);
  },

  delete(key) {
    if (!key) {
      console.error('Error: key is required');
      process.exit(1);
    }
    const memory = loadMemory();
    delete memory[key];
    saveMemory(memory);
    console.log(`Deleted: ${key}`);
  },

  clear() {
    saveMemory({});
    console.log('Memory cleared');
  },

  keys() {
    const memory = loadMemory();
    const keys = Object.keys(memory).filter(k => !k.startsWith('_'));
    console.log(keys.join('\n'));
    return keys;
  },
};

// CLI entry point
const [,, command, key, ...valueParts] = process.argv;
const value = valueParts.join(' ');

if (command && commands[command]) {
  commands[command](key, value);
} else {
  console.log('Usage: memory.js <get|set|delete|clear|keys> [key] [value]');
}

module.exports = commands;
