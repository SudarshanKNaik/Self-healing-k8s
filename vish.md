# Website Guide for Beginners (Step by Step)

This guide is written for someone with no technical background.
Follow the steps in order.

## 1) What you need first

- A Windows computer
- Internet connection
- The project folder already available at `D:\k8s-self-healing`
- Node.js installed (if not installed, ask someone to install Node.js LTS)

## 2) Open the project

1. Open VS Code.
2. Open folder: `D:\k8s-self-healing`.
3. Open Terminal in VS Code:
   - Menu -> Terminal -> New Terminal

## 3) Start the website

1. In the terminal, run:

```powershell
cd D:\k8s-self-healing\h24-app
npm install
npm run dev
```

2. Wait until you see a line similar to:
   - `Local: http://localhost:3000`

3. Open your browser and go to:
   - `http://localhost:3000`

The website is now running.

## 4) Open the healing dashboard

1. In browser, open:
   - `http://localhost:3000/dashboard/healing`

2. This is the main page where you can:
   - See cluster/service health data
   - View healing options
   - Start healing actions
   - Check logs

## 5) How to use it (simple workflow)

1. Select a target service/pod from the page.
2. Wait for remediation options to appear.
3. Click one option to select it.
4. Click **Start Healing**.
5. Watch the status section for updates.
6. Scroll to the logs area to verify what happened.

## 6) How to verify your selected option was really used

1. On the healing page, open the log section (Backend Execution Logs).
2. Confirm these fields:
   - Remediation ID
   - Strategy
   - Target name
   - Status (SUCCESS/FAILED)
3. The same logs are also saved in this file:
   - `D:\k8s-self-healing\h24-app\ayush.md`

If the values match your chosen option, it worked correctly.

## 7) If metrics are not loading

If you see upstream/404/metrics errors:

1. Make sure the app is still running in terminal (`npm run dev`).
2. Refresh browser page.
3. If still failing, stop and restart:

```powershell
cd D:\k8s-self-healing\h24-app
npm run dev
```

4. If your setup needs backend metrics tunnel (ngrok/Flask), ask to run those helper services as well.

## 8) Stop the website

In the terminal where website is running, press:

- `Ctrl + C`

This stops the local server.

## 9) Daily quick start (short version)

```powershell
cd D:\k8s-self-healing\h24-app
npm run dev
```

Then open:

- `http://localhost:3000/dashboard/healing`

## 10) Common mistakes and fixes

- Page not opening:
  - Check if terminal still running.
- "Port already in use":
  - Close old terminal/server and run again.
- Buttons disabled:
  - Select a valid target first.
- No logs shown:
  - Run healing once, then check logs section or `ayush.md`.

---

If you want, this guide can be converted into a one-page checklist version too.