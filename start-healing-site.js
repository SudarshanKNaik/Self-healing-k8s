#!/usr/bin/env node
/**
 * Startup script for Ayush Healing Backend Logs
 * This script starts the h24-app website with healing execution logging
 */

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const projectRoot = path.join(__dirname, "..");
const logFilePath = path.join(projectRoot, "ayush.md");

console.log("╔════════════════════════════════════════════════════════════════╗");
console.log("║     Ayush - Healing Backend Logging System                    ║");
console.log("║     Starting Next.js Development Server                       ║");
console.log("╚════════════════════════════════════════════════════════════════╝");
console.log("");

// Check if log file exists, if not create it
if (!fs.existsSync(logFilePath)) {
  console.log("📝 Creating ayush.md log file...");
  const header = `# Ayush - Healing Backend Logs

This file tracks all remediation options executed and their outcomes.

---

`;
  fs.writeFileSync(logFilePath, header, "utf-8");
  console.log(`✓ Log file created at: ${logFilePath}`);
}
console.log("");

console.log("📦 Starting Next.js development server...");
console.log("");

// Start Next.js dev server
const devProcess = spawn("npm", ["run", "dev"], {
  cwd: projectRoot,
  stdio: "inherit",
  shell: true,
});

devProcess.on("error", (error) => {
  console.error("Error starting dev server:", error);
  process.exit(1);
});

// Show instructions after a brief delay
setTimeout(() => {
  console.log("");
  console.log("╔════════════════════════════════════════════════════════════════╗");
  console.log("║                    Setup Complete!                            ║");
  console.log("╚════════════════════════════════════════════════════════════════╝");
  console.log("");
  console.log("📍 Access the Healing Dashboard:");
  console.log("   → http://localhost:3000/dashboard/healing");
  console.log("");
  console.log("📝 Backend Logs Location:");
  console.log(`   → ${logFilePath}`);
  console.log("");
  console.log("🎯 How to Use:");
  console.log("   1. Open the Healing Dashboard in your browser");
  console.log("   2. Select a pod/service from the targets");
  console.log("   3. Choose a remediation option (Fast Restart, etc.)");
  console.log("   4. Click 'Start Healing'");
  console.log("   5. Check the 'Backend Execution Logs (Ayush)' section on the page");
  console.log("   6. Or view the ayush.md file directly");
  console.log("");
  console.log("✨ Features:");
  console.log("   ✓ Logs which option you selected");
  console.log("   ✓ Tracks remediation strategy and scenario");
  console.log("   ✓ Shows target pod/deployment name and namespace");
  console.log("   ✓ Records success/failure status");
  console.log("   ✓ Stores detailed execution results");
  console.log("");
  console.log("🎮 Dashboard Actions:");
  console.log("   • Auto Refresh - Real-time log updates");
  console.log("   • Download - Save logs as markdown file");
  console.log("   • Clear - Reset logs for fresh start");
  console.log("");
}, 2000);
