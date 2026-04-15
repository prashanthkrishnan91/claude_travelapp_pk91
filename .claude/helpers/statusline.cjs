#!/usr/bin/env node
/**
 * RuFlo V3 Statusline Generator
 * Displays real-time V3 implementation progress and system status
 */

/* eslint-disable @typescript-eslint/no-var-requires */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const os = require('os');

const CONFIG = { maxAgents: 15 };
const CWD = process.cwd();

const c = {
  reset: '\x1b[0m', bold: '\x1b[1m', dim: '\x1b[2m',
  red: '\x1b[0;31m', green: '\x1b[0;32m', yellow: '\x1b[0;33m',
  blue: '\x1b[0;34m', purple: '\x1b[0;35m', cyan: '\x1b[0;36m',
  brightRed: '\x1b[1;31m', brightGreen: '\x1b[1;32m', brightYellow: '\x1b[1;33m',
  brightBlue: '\x1b[1;34m', brightPurple: '\x1b[1;35m', brightCyan: '\x1b[1;36m',
  brightWhite: '\x1b[1;37m',
};

function safeExec(cmd, timeoutMs = 2000) {
  try {
    return execSync(cmd, { encoding: 'utf-8', timeout: timeoutMs, stdio: ['pipe', 'pipe', 'pipe'] }).trim();
  } catch { return ''; }
}

function readJSON(filePath) {
  try {
    if (fs.existsSync(filePath)) return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  } catch { /* ignore */ }
  return null;
}

function safeStat(filePath) {
  try { return fs.statSync(filePath); } catch { return null; }
}

let _settingsCache = undefined;
function getSettings() {
  if (_settingsCache !== undefined) return _settingsCache;
  _settingsCache = readJSON(path.join(CWD, '.claude', 'settings.json'))
    || readJSON(path.join(CWD, '.claude', 'settings.local.json')) || null;
  return _settingsCache;
}

function getGitInfo() {
  const result = { name: 'user', gitBranch: '', modified: 0, untracked: 0, staged: 0, ahead: 0, behind: 0 };
  const script = [
    'git config user.name 2>/dev/null || echo user',
    'echo "---SEP---"',
    'git branch --show-current 2>/dev/null',
    'echo "---SEP---"',
    'git status --porcelain 2>/dev/null',
    'echo "---SEP---"',
    'git rev-list --left-right --count HEAD...@{upstream} 2>/dev/null || echo "0 0"',
  ].join('; ');
  const raw = safeExec("sh -c '" + script + "'", 3000);
  if (!raw) return result;
  const parts = raw.split('---SEP---').map(s => s.trim());
  if (parts.length >= 4) {
    result.name = parts[0] || 'user';
    result.gitBranch = parts[1] || '';
    if (parts[2]) {
      for (const line of parts[2].split('\n')) {
        if (!line || line.length < 2) continue;
        const x = line[0], y = line[1];
        if (x === '?' && y === '?') { result.untracked++; continue; }
        if (x !== ' ' && x !== '?') result.staged++;
        if (y !== ' ' && y !== '?') result.modified++;
      }
    }
    const ab = (parts[3] || '0 0').split(/\s+/);
    result.ahead = parseInt(ab[0]) || 0;
    result.behind = parseInt(ab[1]) || 0;
  }
  return result;
}

function getModelName() {
  try {
    const claudeConfig = readJSON(path.join(os.homedir(), '.claude.json'));
    if (claudeConfig && claudeConfig.projects) {
      for (const [projectPath, projectConfig] of Object.entries(claudeConfig.projects)) {
        if (CWD === projectPath || CWD.startsWith(projectPath + '/')) {
          const usage = projectConfig.lastModelUsage;
          if (usage) {
            const ids = Object.keys(usage);
            if (ids.length > 0) {
              let modelId = ids[ids.length - 1], latest = 0;
              for (const id of ids) {
                const ts = usage[id] && usage[id].lastUsedAt ? new Date(usage[id].lastUsedAt).getTime() : 0;
                if (ts > latest) { latest = ts; modelId = id; }
              }
              if (modelId.includes('opus')) return 'Opus 4.6 (1M context)';
              if (modelId.includes('sonnet')) return 'Sonnet 4.6';
              if (modelId.includes('haiku')) return 'Haiku 4.5';
              return modelId.split('-').slice(1, 3).join(' ');
            }
          }
          break;
        }
      }
    }
  } catch { /* ignore */ }
  const settings = getSettings();
  if (settings && settings.model) {
    const m = settings.model;
    if (m.includes('opus')) return 'Opus 4.6 (1M context)';
    if (m.includes('sonnet')) return 'Sonnet 4.6';
    if (m.includes('haiku')) return 'Haiku 4.5';
  }
  return 'Claude Code';
}

function getLearningStats() {
  let patterns = 0, sessions = 0;
  const patternStorePath = path.join(CWD, '.claude-flow', 'data', 'patterns.json');
  try {
    if (fs.existsSync(patternStorePath)) {
      const data = JSON.parse(fs.readFileSync(patternStorePath, 'utf-8'));
      if (Array.isArray(data)) patterns = data.length;
      else if (data && data.patterns) patterns = Array.isArray(data.patterns) ? data.patterns.length : Object.keys(data.patterns).length;
    }
  } catch { /* ignore */ }
  if (patterns === 0) {
    const autoStorePath = path.join(CWD, '.claude-flow', 'data', 'auto-memory-store.json');
    try {
      if (fs.existsSync(autoStorePath)) {
        const data = JSON.parse(fs.readFileSync(autoStorePath, 'utf-8'));
        if (Array.isArray(data)) patterns = data.length;
        else if (data && data.entries) patterns = data.entries.length;
      }
    } catch { /* ignore */ }
  }
  try {
    const sessDir = path.join(CWD, '.claude', 'sessions');
    if (fs.existsSync(sessDir)) sessions = fs.readdirSync(sessDir).filter(f => f.endsWith('.json')).length;
  } catch { /* ignore */ }
  if (sessions === 0) {
    try {
      const cfSessDir = path.join(CWD, '.claude-flow', 'sessions');
      if (fs.existsSync(cfSessDir)) sessions = fs.readdirSync(cfSessDir).filter(f => f.endsWith('.json')).length;
    } catch { /* ignore */ }
  }
  return { patterns, sessions };
}

function getV3Progress() {
  const learning = getLearningStats();
  const totalDomains = 5;
  const dddData = readJSON(path.join(CWD, '.claude-flow', 'metrics', 'ddd-progress.json'));
  let dddProgress = dddData ? (dddData.progress || 0) : 0;
  let domainsCompleted = Math.min(5, Math.floor(dddProgress / 20));
  if (dddProgress === 0 && learning.patterns > 0) {
    domainsCompleted = Math.min(5, Math.floor(learning.patterns / 100));
    dddProgress = Math.floor((domainsCompleted / totalDomains) * 100);
  }
  return { domainsCompleted, totalDomains, dddProgress, patternsLearned: learning.patterns, sessionsCompleted: learning.sessions };
}

function getSecurityStatus() {
  const auditData = readJSON(path.join(CWD, '.claude-flow', 'security', 'audit-status.json'));
  if (auditData) {
    const auditDate = auditData.lastAudit || auditData.lastScan;
    if (!auditDate) return { status: 'PENDING', cvesFixed: 0, totalCves: 0 };
    const isStale = Date.now() - new Date(auditDate).getTime() > 7 * 24 * 60 * 60 * 1000;
    return { status: isStale ? 'STALE' : (auditData.status || 'PENDING'), cvesFixed: auditData.cvesFixed || 0, totalCves: auditData.totalCves || 0 };
  }
  let scanCount = 0;
  try {
    const scanDir = path.join(CWD, '.claude', 'security-scans');
    if (fs.existsSync(scanDir)) scanCount = fs.readdirSync(scanDir).filter(f => f.endsWith('.json')).length;
  } catch { /* ignore */ }
  return { status: scanCount > 0 ? 'SCANNED' : 'NONE', cvesFixed: 0, totalCves: 0 };
}

function getSwarmStatus() {
  const staleThresholdMs = 5 * 60 * 1000;
  const now = Date.now();
  const swarmState = readJSON(path.join(CWD, '.claude-flow', 'swarm', 'swarm-state.json'));
  if (swarmState) {
    const age = swarmState.updatedAt ? now - new Date(swarmState.updatedAt).getTime() : Infinity;
    if (age < staleThresholdMs) return { activeAgents: (swarmState.agents && swarmState.agents.length) || swarmState.agentCount || 0, maxAgents: swarmState.maxAgents || CONFIG.maxAgents, coordinationActive: true };
  }
  return { activeAgents: 0, maxAgents: CONFIG.maxAgents, coordinationActive: false };
}

function getAgentDBStats() {
  let vectorCount = 0, dbSizeKB = 0, namespaces = 0, hasHnsw = false;
  const storePath = path.join(CWD, '.claude-flow', 'data', 'auto-memory-store.json');
  const storeStat = safeStat(storePath);
  if (storeStat) {
    dbSizeKB += storeStat.size / 1024;
    try {
      const store = JSON.parse(fs.readFileSync(storePath, 'utf-8'));
      if (Array.isArray(store)) vectorCount += store.length;
      else if (store && store.entries) vectorCount += store.entries.length;
    } catch { /* fall back */ }
  }
  const hnswPaths = [path.join(CWD, '.swarm', 'hnsw.index'), path.join(CWD, '.claude-flow', 'hnsw.index')];
  for (const p of hnswPaths) { if (safeStat(p)) { hasHnsw = true; break; } }
  if (!hasHnsw) {
    const memPkgPaths = [path.join(CWD, 'v3', '@claude-flow', 'memory', 'dist'), path.join(CWD, 'node_modules', '@claude-flow', 'memory')];
    for (const p of memPkgPaths) { if (fs.existsSync(p)) { hasHnsw = true; break; } }
  }
  return { vectorCount, dbSizeKB: Math.floor(dbSizeKB), namespaces, hasHnsw };
}

function getSystemMetrics() {
  const memoryMB = Math.floor(process.memoryUsage().heapUsed / 1024 / 1024);
  const learning = getLearningStats();
  const agentdb = getAgentDBStats();
  const learningData = readJSON(path.join(CWD, '.claude-flow', 'metrics', 'learning.json'));
  let intelligencePct = 0, contextPct = 0;
  if (learningData && learningData.intelligence && learningData.intelligence.score !== undefined) {
    intelligencePct = Math.min(100, Math.floor(learningData.intelligence.score));
  } else {
    const fromPatterns = learning.patterns > 0 ? Math.min(100, Math.floor(learning.patterns / 20)) : 0;
    const fromVectors = agentdb.vectorCount > 0 ? Math.min(100, Math.floor(agentdb.vectorCount / 20)) : 0;
    intelligencePct = Math.max(fromPatterns, fromVectors);
  }
  contextPct = learning.sessions > 0 ? Math.min(100, learning.sessions * 5) : 0;
  return { memoryMB, contextPct, intelligencePct, subAgents: 0 };
}

function getADRStatus() {
  const adrPaths = [path.join(CWD, 'v3', 'implementation', 'adrs'), path.join(CWD, 'docs', 'adrs'), path.join(CWD, '.claude-flow', 'adrs')];
  for (const adrPath of adrPaths) {
    try {
      if (fs.existsSync(adrPath)) {
        const files = fs.readdirSync(adrPath).filter(f => f.endsWith('.md') && (f.startsWith('ADR-') || f.startsWith('adr-') || /^\d{4}-/.test(f)));
        return { count: files.length, implemented: files.length, compliance: 0 };
      }
    } catch { /* ignore */ }
  }
  return { count: 0, implemented: 0, compliance: 0 };
}

function getHooksStatus() {
  let enabled = 0, total = 0;
  const settings = getSettings();
  if (settings && settings.hooks) {
    for (const category of Object.keys(settings.hooks)) {
      const matchers = settings.hooks[category];
      if (!Array.isArray(matchers)) continue;
      for (const matcher of matchers) {
        const hooks = matcher && matcher.hooks;
        if (Array.isArray(hooks)) { total += hooks.length; enabled += hooks.length; }
      }
    }
  }
  return { enabled, total };
}

function getTestStats() {
  let testFiles = 0;
  function countTestFiles(dir, depth) {
    if (depth === undefined) depth = 0;
    if (depth > 6) return;
    try {
      if (!fs.existsSync(dir)) return;
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules') countTestFiles(path.join(dir, entry.name), depth + 1);
        else if (entry.isFile()) {
          const n = entry.name;
          if (n.includes('.test.') || n.includes('.spec.') || n.includes('_test.') || n.includes('_spec.')) testFiles++;
        }
      }
    } catch { /* ignore */ }
  }
  for (const d of ['tests', 'test', '__tests__', 'src', 'v3']) countTestFiles(path.join(CWD, d));
  return { testFiles, testCases: testFiles * 4 };
}

function getIntegrationStatus() {
  const mcpServers = { total: 0, enabled: 0 };
  const mcpConfig = readJSON(path.join(CWD, '.mcp.json')) || readJSON(path.join(os.homedir(), '.claude', 'mcp.json'));
  if (mcpConfig && mcpConfig.mcpServers) {
    const s = Object.keys(mcpConfig.mcpServers);
    mcpServers.total = s.length;
    mcpServers.enabled = s.length;
  }
  const hasDatabase = ['.swarm/memory.db', '.claude-flow/memory.db', 'data/memory.db'].some(p => fs.existsSync(path.join(CWD, p)));
  const hasApi = !!(process.env.ANTHROPIC_API_KEY || process.env.OPENAI_API_KEY);
  return { mcpServers, hasDatabase, hasApi };
}

function getSessionStats() {
  for (const sp of ['.claude-flow/session.json', '.claude/session.json']) {
    const data = readJSON(path.join(CWD, sp));
    if (data && data.startTime) {
      const mins = Math.floor((Date.now() - new Date(data.startTime).getTime()) / 60000);
      return { duration: mins < 60 ? mins + 'm' : Math.floor(mins / 60) + 'h' + (mins % 60) + 'm' };
    }
  }
  return { duration: '' };
}

function progressBar(current, total) {
  const width = 5, filled = Math.round((current / total) * width);
  return '[' + '\u25CF'.repeat(filled) + '\u25CB'.repeat(width - filled) + ']';
}

let _stdinData = null;
function getStdinData() {
  if (_stdinData !== undefined && _stdinData !== null) return _stdinData;
  try {
    if (process.stdin.isTTY) { _stdinData = null; return null; }
    const chunks = [], buf = Buffer.alloc(4096);
    let bytesRead;
    try { while ((bytesRead = fs.readSync(0, buf, 0, buf.length, null)) > 0) chunks.push(buf.slice(0, bytesRead)); } catch { /* EOF */ }
    const raw = Buffer.concat(chunks).toString('utf-8').trim();
    _stdinData = (raw && raw.startsWith('{')) ? JSON.parse(raw) : null;
  } catch { _stdinData = null; }
  return _stdinData;
}

function getModelFromStdin() {
  const data = getStdinData();
  return (data && data.model && data.model.display_name) ? data.model.display_name : null;
}

function getContextFromStdin() {
  const data = getStdinData();
  if (data && data.context_window) return { usedPct: Math.floor(data.context_window.used_percentage || 0), remainingPct: Math.floor(data.context_window.remaining_percentage || 100) };
  return null;
}

function getCostFromStdin() {
  const data = getStdinData();
  if (data && data.cost) {
    const durationMs = data.cost.total_duration_ms || 0;
    const mins = Math.floor(durationMs / 60000), secs = Math.floor((durationMs % 60000) / 1000);
    return { costUsd: data.cost.total_cost_usd || 0, duration: mins > 0 ? mins + 'm' + secs + 's' : secs + 's', linesAdded: data.cost.total_lines_added || 0, linesRemoved: data.cost.total_lines_removed || 0 };
  }
  return null;
}

function generateStatusline() {
  const git = getGitInfo();
  const modelName = getModelFromStdin() || getModelName();
  const ctxInfo = getContextFromStdin();
  const costInfo = getCostFromStdin();
  const progress = getV3Progress();
  const security = getSecurityStatus();
  const swarm = getSwarmStatus();
  const system = getSystemMetrics();
  const adrs = getADRStatus();
  const hooks = getHooksStatus();
  const agentdb = getAgentDBStats();
  const tests = getTestStats();
  const session = getSessionStats();
  const integration = getIntegrationStatus();
  const lines = [];

  let pkgVersion = '3.5';
  try {
    const pkgPath = path.join(CWD, 'node_modules', '@claude-flow', 'cli', 'package.json');
    if (fs.existsSync(pkgPath)) { const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8')); if (pkg.version) pkgVersion = pkg.version; }
  } catch { /* use default */ }

  let header = c.bold + c.brightPurple + '\u258A RuFlo V' + pkgVersion + ' ' + c.reset;
  header += (swarm.coordinationActive ? c.brightCyan : c.dim) + '\u25CF ' + c.brightCyan + git.name + c.reset;
  if (git.gitBranch) {
    header += '  ' + c.dim + '\u2502' + c.reset + '  ' + c.brightBlue + '\u23C7 ' + git.gitBranch + c.reset;
    const changes = git.modified + git.staged + git.untracked;
    if (changes > 0) {
      let ind = '';
      if (git.staged > 0) ind += c.brightGreen + '+' + git.staged + c.reset;
      if (git.modified > 0) ind += c.brightYellow + '~' + git.modified + c.reset;
      if (git.untracked > 0) ind += c.dim + '?' + git.untracked + c.reset;
      header += ' ' + ind;
    }
    if (git.ahead > 0) header += ' ' + c.brightGreen + '\u2191' + git.ahead + c.reset;
    if (git.behind > 0) header += ' ' + c.brightRed + '\u2193' + git.behind + c.reset;
  }
  header += '  ' + c.dim + '\u2502' + c.reset + '  ' + c.purple + modelName + c.reset;
  const duration = costInfo ? costInfo.duration : session.duration;
  if (duration) header += '  ' + c.dim + '\u2502' + c.reset + '  ' + c.cyan + '\u23F1 ' + duration + c.reset;
  if (ctxInfo && ctxInfo.usedPct > 0) {
    const ctxColor = ctxInfo.usedPct >= 90 ? c.brightRed : ctxInfo.usedPct >= 70 ? c.brightYellow : c.brightGreen;
    header += '  ' + c.dim + '\u2502' + c.reset + '  ' + ctxColor + '\u25CF ' + ctxInfo.usedPct + '% ctx' + c.reset;
  }
  if (costInfo && costInfo.costUsd > 0) header += '  ' + c.dim + '\u2502' + c.reset + '  ' + c.brightYellow + '$' + costInfo.costUsd.toFixed(2) + c.reset;
  lines.push(header);
  lines.push(c.dim + '\u2500'.repeat(53) + c.reset);

  const domainsColor = progress.domainsCompleted >= 3 ? c.brightGreen : progress.domainsCompleted > 0 ? c.yellow : c.red;
  let perfIndicator;
  if (agentdb.hasHnsw && agentdb.vectorCount > 0) {
    const speedup = agentdb.vectorCount > 10000 ? '12500x' : agentdb.vectorCount > 1000 ? '150x' : '10x';
    perfIndicator = c.brightGreen + '\u26A1 HNSW ' + speedup + c.reset;
  } else if (progress.patternsLearned > 0) {
    const pk = progress.patternsLearned >= 1000 ? (progress.patternsLearned / 1000).toFixed(1) + 'k' : String(progress.patternsLearned);
    perfIndicator = c.brightYellow + '\uD83D\uDCDA ' + pk + ' patterns' + c.reset;
  } else {
    perfIndicator = c.dim + '\u26A1 target: 150x-12500x' + c.reset;
  }
  lines.push(c.brightCyan + '\uD83C\uDFD7\uFE0F  DDD Domains' + c.reset + '    ' + progressBar(progress.domainsCompleted, progress.totalDomains) + '  ' + domainsColor + progress.domainsCompleted + c.reset + '/' + c.brightWhite + progress.totalDomains + c.reset + '    ' + perfIndicator);

  const swarmInd = swarm.coordinationActive ? c.brightGreen + '\u25C9' + c.reset : c.dim + '\u25CB' + c.reset;
  const agentsColor = swarm.activeAgents > 0 ? c.brightGreen : c.red;
  const secIcon = security.status === 'CLEAN' ? '\uD83D\uDFE2' : security.status === 'NONE' ? '\u26AA' : '\uD83D\uDD34';
  const secColor = security.status === 'CLEAN' ? c.brightGreen : security.status === 'NONE' ? c.dim : c.brightRed;
  const hooksColor = hooks.enabled > 0 ? c.brightGreen : c.dim;
  const intellColor = system.intelligencePct >= 80 ? c.brightGreen : system.intelligencePct >= 40 ? c.brightYellow : c.dim;
  lines.push(c.brightYellow + '\uD83E\uDD16 Swarm' + c.reset + '  ' + swarmInd + ' [' + agentsColor + String(swarm.activeAgents).padStart(2) + c.reset + '/' + c.brightWhite + swarm.maxAgents + c.reset + ']  ' + c.brightPurple + '\uD83D\uDC65 ' + system.subAgents + c.reset + '    ' + c.brightBlue + '\uD83E\uDE9D ' + hooksColor + hooks.enabled + c.reset + '/' + c.brightWhite + hooks.total + c.reset + '    ' + secIcon + ' ' + secColor + 'CVE ' + security.cvesFixed + c.reset + '/' + c.brightWhite + security.totalCves + c.reset + '    ' + c.brightCyan + '\uD83D\uDCBE ' + system.memoryMB + 'MB' + c.reset + '    ' + intellColor + '\uD83E\uDDE0 ' + String(system.intelligencePct).padStart(3) + '%' + c.reset);

  const dddColor = progress.dddProgress >= 50 ? c.brightGreen : progress.dddProgress > 0 ? c.yellow : c.red;
  const adrColor = adrs.count > 0 ? (adrs.implemented === adrs.count ? c.brightGreen : c.yellow) : c.dim;
  const adrDisplay = adrColor + '\u25CF' + adrs.implemented + '/' + adrs.count + c.reset;
  lines.push(c.brightPurple + '\uD83D\uDD27 Architecture' + c.reset + '    ' + c.cyan + 'ADRs' + c.reset + ' ' + adrDisplay + '  ' + c.dim + '\u2502' + c.reset + '  ' + c.cyan + 'DDD' + c.reset + ' ' + dddColor + '\u25CF' + String(progress.dddProgress).padStart(3) + '%' + c.reset + '  ' + c.dim + '\u2502' + c.reset + '  ' + c.cyan + 'Security' + c.reset + ' ' + secColor + '\u25CF' + security.status + c.reset);

  const hnswInd = agentdb.hasHnsw ? c.brightGreen + '\u26A1' + c.reset : '';
  const sizeDisp = agentdb.dbSizeKB >= 1024 ? (agentdb.dbSizeKB / 1024).toFixed(1) + 'MB' : agentdb.dbSizeKB + 'KB';
  const vectorColor = agentdb.vectorCount > 0 ? c.brightGreen : c.dim;
  const testColor = tests.testFiles > 0 ? c.brightGreen : c.dim;
  let integStr = '';
  if (integration.mcpServers.total > 0) {
    const mcpCol = integration.mcpServers.enabled === integration.mcpServers.total ? c.brightGreen : integration.mcpServers.enabled > 0 ? c.brightYellow : c.red;
    integStr += c.cyan + 'MCP' + c.reset + ' ' + mcpCol + '\u25CF' + integration.mcpServers.enabled + '/' + integration.mcpServers.total + c.reset;
  }
  if (integration.hasDatabase) integStr += (integStr ? '  ' : '') + c.brightGreen + '\u25C6' + c.reset + 'DB';
  if (integration.hasApi) integStr += (integStr ? '  ' : '') + c.brightGreen + '\u25C6' + c.reset + 'API';
  if (!integStr) integStr = c.dim + '\u25CF none' + c.reset;
  lines.push(c.brightCyan + '\uD83D\uDCCA AgentDB' + c.reset + '    ' + c.cyan + 'Vectors' + c.reset + ' ' + vectorColor + '\u25CF' + agentdb.vectorCount + hnswInd + c.reset + '  ' + c.dim + '\u2502' + c.reset + '  ' + c.cyan + 'Size' + c.reset + ' ' + c.brightWhite + sizeDisp + c.reset + '  ' + c.dim + '\u2502' + c.reset + '  ' + c.cyan + 'Tests' + c.reset + ' ' + testColor + '\u25CF' + tests.testFiles + c.reset + ' ' + c.dim + '(~' + tests.testCases + ' cases)' + c.reset + '  ' + c.dim + '\u2502' + c.reset + '  ' + integStr);

  return lines.join('\n');
}

function generateJSON() {
  const git = getGitInfo();
  return { user: { name: git.name, gitBranch: git.gitBranch, modelName: getModelName() }, v3Progress: getV3Progress(), security: getSecurityStatus(), swarm: getSwarmStatus(), system: getSystemMetrics(), adrs: getADRStatus(), hooks: getHooksStatus(), agentdb: getAgentDBStats(), tests: getTestStats(), git: { modified: git.modified, untracked: git.untracked, staged: git.staged, ahead: git.ahead, behind: git.behind }, lastUpdated: new Date().toISOString() };
}

if (process.argv.includes('--json')) console.log(JSON.stringify(generateJSON(), null, 2));
else if (process.argv.includes('--compact')) console.log(JSON.stringify(generateJSON()));
else console.log(generateStatusline());
