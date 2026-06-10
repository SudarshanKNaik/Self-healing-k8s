# KubePulse Daily Startup Guide

This guide outlines the exact steps to spin up your entire development environment from scratch tomorrow. 

> [!IMPORTANT]
> Make sure you open multiple terminal windows or tabs, as several of these commands are long-running processes that need to stay open.

### Step 1: Start Docker Desktop
Before starting Minikube or anything else, ensure Docker Desktop is running in the background.
1. Open the Windows Start menu and search for **Docker Desktop**.
2. Launch it and wait for the engine icon to turn green in your system tray.

### Step 2: Start Minikube & Kubernetes
Open your first terminal (e.g., PowerShell) and navigate to your project directory.
```powershell
cd D:\k8s-self-healing
minikube start
```
*Wait for this command to finish. It will boot up your cluster and the Online Boutique pods will automatically start initializing.*

### Step 3: Expose the Online Boutique App
In a **new terminal tab**, port-forward the boutique frontend so you can view it in your browser.
```powershell
cd D:\k8s-self-healing
kubectl port-forward svc/frontend 54290:80
```
*Leave this terminal open. The shop will be accessible at [http://127.0.0.1:54290](http://127.0.0.1:54290).*

### Step 4: Start the Python KubePulse Agent
In a **new terminal tab**, start your local Python agent which collects pod details.
```powershell
cd D:\k8s-self-healing
.venv\Scripts\python.exe app.py
```
*Leave this terminal open. The agent will run on port 5000.*

### Step 5: Start the Ngrok Tunnel
In a **new terminal tab**, expose your Python agent to the internet so the Next.js dashboard can poll it.
```powershell
cd D:\k8s-self-healing
ngrok http 5000
```
*Leave this terminal open. Ngrok will print a public URL (e.g., `https://<random>.ngrok-free.dev`). Copy this URL, append `/pods` to it, and paste it into your KubePulse Dashboard endpoint settings.*

### Step 6: Start the Next.js Dashboard (Frontend & Backend)
Finally, in a **new terminal tab**, start the main web application.
```powershell
cd D:\k8s-self-healing\h24-app
npm run dev
```
*Leave this terminal open. Your dashboard will be accessible at [http://localhost:3000](http://localhost:3000).*

---

> [!TIP]
> **Quick Recap of Active URLs:**
> - **Dashboard**: `http://localhost:3000`
> - **Online Boutique**: `http://127.0.0.1:54290`
> - **Agent Pods API**: `<your-ngrok-url>/pods`
> - **MongoDB Database**: Running locally at `mongodb://127.0.0.1:27017` (Ensure the MongoDB Windows service is running if the dashboard fails to load).
