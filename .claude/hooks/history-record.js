#!/usr/bin/env node
"use strict";

// Contract: read COMP_HOOK_INPUT (Claude Stop event JSON), then read its
// transcript_path as UTF-8 JSONL. Print one JSON object with request and
// outcome for the latest user turn, or print nothing for missing/malformed
// input. Never write files. Exit 0 for absent data; an unreadable transcript
// is treated as absent so the Stop hook cannot block the conversation.
const fs = require("node:fs");

function textOf(content) {
  if (typeof content === "string") return content.trim();
  if (!Array.isArray(content)) return "";
  return content
    .filter((part) => part && part.type === "text" && typeof part.text === "string")
    .map((part) => part.text.trim())
    .filter(Boolean)
    .join("\n");
}

function redact(text) {
  return text
    .replace(/\b(?:sk-|ghp_|github_pat_|AIza|xox[baprs]-|AKIA)[A-Za-z0-9_-]{8,}/g, "[REDACTED]")
    .replace(/\b(api[_-]?key|token)\s*[:=]\s*["']?([A-Za-z0-9_+\/-]{16,})/gi, "$1=[REDACTED]");
}

function main() {
  try {
    const event = JSON.parse(process.env.COMP_HOOK_INPUT || "{}");
    if (typeof event.transcript_path !== "string" || !event.transcript_path) return;
    const lines = fs.readFileSync(event.transcript_path, "utf8").split(/\r?\n/);
    let request = "";
    let outcome = null;
    for (const line of lines) {
      let item;
      try {
        item = JSON.parse(line);
      } catch {
        continue;
      }
      const role = item.type || item.role;
      const content = textOf(item.message?.content ?? item.content);
      if (role === "user" && content) {
        request = content;
        outcome = null;
      } else if (role === "assistant" && request && content) {
        outcome = content;
      }
    }
    if (request) {
      process.stdout.write(JSON.stringify({
        request: redact(request).slice(0, 600),
        outcome: outcome === null ? null : redact(outcome).slice(0, 400),
      }));
    }
  } catch {
    // Claude must be able to stop even if the transcript disappeared.
  }
}

main();
