#!/usr/bin/env node
/**
 * Agent Task Router
 * Routes tasks to the most appropriate agent based on task content patterns.
 *
 * Usage:
 *   node ai/utils/router.js "Implement the hotel search endpoint"
 *   node ai/utils/router.js "Write unit tests for the booking service"
 *
 * Output: JSON with recommended agent, confidence, and reasoning.
 */

'use strict';

// Agent capability definitions
const AGENT_CAPABILITIES = {
  coder: [
    'implementation', 'coding', 'programming', 'development',
    'api', 'backend', 'frontend', 'database', 'migration',
    'refactoring', 'feature', 'bug fix', 'debugging',
  ],
  tester: [
    'testing', 'tests', 'unit test', 'integration test', 'e2e',
    'coverage', 'assertion', 'mock', 'stub', 'fixture',
    'quality assurance', 'validation',
  ],
  reviewer: [
    'review', 'code review', 'audit', 'security check',
    'performance review', 'code quality', 'standards', 'lint',
  ],
  researcher: [
    'research', 'investigate', 'analyze', 'analysis', 'explore',
    'documentation', 'understand', 'survey', 'compare', 'evaluate',
  ],
  planner: [
    'plan', 'planning', 'design', 'architecture', 'strategy',
    'roadmap', 'breakdown', 'decompose', 'organize', 'structure',
  ],
  devops: [
    'deploy', 'deployment', 'docker', 'ci', 'cd', 'pipeline',
    'infrastructure', 'server', 'environment', 'configuration',
    'monitoring', 'logging', 'kubernetes', 'container',
  ],
};

// Regex patterns for fast matching
const TASK_PATTERNS = [
  { pattern: /implement|create|build|add feature|write code|develop/i, agent: 'coder' },
  { pattern: /test|testing|coverage|unit test|integration test|e2e|mock/i, agent: 'tester' },
  { pattern: /review|audit|check quality|security review|lint/i, agent: 'reviewer' },
  { pattern: /research|analyze|investigate|understand|explore|document/i, agent: 'researcher' },
  { pattern: /plan|design|architect|strategy|breakdown|decompose/i, agent: 'planner' },
  { pattern: /deploy|docker|ci\/cd|pipeline|infrastructure|monitoring/i, agent: 'devops' },
];

/**
 * Route a task description to the best matching agent.
 *
 * @param {string} taskDescription - Natural language task description
 * @returns {{ agent: string, confidence: number, reasoning: string }}
 */
function routeTask(taskDescription) {
  if (!taskDescription || typeof taskDescription !== 'string') {
    return { agent: 'coder', confidence: 0.5, reasoning: 'Default fallback — no task description provided' };
  }

  const lower = taskDescription.toLowerCase();

  // Check regex patterns first (fast path)
  for (const { pattern, agent } of TASK_PATTERNS) {
    if (pattern.test(lower)) {
      return {
        agent,
        confidence: 0.8,
        reasoning: `Task matched pattern for ${agent} agent`,
      };
    }
  }

  // Keyword scoring fallback
  let bestAgent = 'coder';
  let bestScore = 0;

  for (const [agent, keywords] of Object.entries(AGENT_CAPABILITIES)) {
    const score = keywords.filter(kw => lower.includes(kw)).length;
    if (score > bestScore) {
      bestScore = score;
      bestAgent = agent;
    }
  }

  if (bestScore > 0) {
    return {
      agent: bestAgent,
      confidence: Math.min(0.5 + bestScore * 0.1, 0.9),
      reasoning: `Keyword match: ${bestScore} capabilities matched for ${bestAgent}`,
    };
  }

  // Default fallback
  return {
    agent: 'coder',
    confidence: 0.5,
    reasoning: 'No pattern matched — defaulting to coder agent',
  };
}

// CLI entry point
const taskArg = process.argv.slice(2).join(' ');
if (taskArg) {
  const result = routeTask(taskArg);
  console.log(JSON.stringify(result, null, 2));
}

module.exports = { routeTask, AGENT_CAPABILITIES, TASK_PATTERNS };
