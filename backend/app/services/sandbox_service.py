import subprocess
import os
import sys
import threading
import time
import json
import collections

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

class SandboxService:
    def __init__(self):
        self._processes: dict[str, subprocess.Popen] = {}
        self._current_config: dict | None = None
        self._supervisor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._logs = collections.deque(maxlen=300)
        self._log_reader_thread: threading.Thread | None = None

    def get_logs(self) -> list[str]:
        return list(self._logs)

    def get_available_scripts(self) -> list[str]:
        scripts = []
        try:
            # Scan root
            for file in os.listdir(PROJECT_ROOT):
                if file.endswith(".py") and os.path.isfile(os.path.join(PROJECT_ROOT, file)):
                    scripts.append(file)
            # Scan tools
            tools_dir = os.path.join(PROJECT_ROOT, "tools")
            if os.path.isdir(tools_dir):
                for file in os.listdir(tools_dir):
                    if file.endswith(".py") and os.path.isfile(os.path.join(tools_dir, file)):
                        scripts.append(f"tools/{file}")
            scripts.sort()
        except Exception:
            pass
        return scripts

    def start(self, config: dict) -> dict:
        main_script = config.get("script_name")
        if not main_script:
            return {"status": "error", "message": "Aucun script principal spécifié"}

        # Sandbox bornée : n'exécuter QUE des scripts de la liste blanche (racine + tools/).
        # Bloque l'exécution arbitraire et le path-traversal (ex. "../x.py") avant tout Popen.
        if main_script not in self.get_available_scripts():
            return {"status": "error", "message": f"Script non autorisé (hors liste blanche) : {main_script}"}

        if "main" in self._processes and self._processes["main"].poll() is None:
            return {"status": "error", "message": f"Une expérimentation est déjà en cours : {self._current_config.get('script_name')}"}

        script_path = os.path.join(PROJECT_ROOT, main_script)
        if not os.path.isfile(script_path):
            return {"status": "error", "message": f"Script introuvable : {main_script}"}

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = PROJECT_ROOT  # Ensure it can import src.*
        
        # Pass new world parameters
        if config.get("world_type"):
            env["WORLD_TYPE"] = str(config.get("world_type"))
        if config.get("import_agent_id"):
            env["IMPORT_AGENT_ID"] = str(config.get("import_agent_id"))
        env["KEEP_MEMORY"] = "1" if config.get("keep_memory") else "0"
        env["RESOURCE_LIMIT"] = str(config.get("resource_limit", 4))
        env["BATCH_SIZE"] = str(config.get("batch_size", 0))
        if config.get("mutation_rate") is not None:
            env["MUTATION_RATE"] = str(config.get("mutation_rate"))
        if config.get("seed") is not None:
            env["RANDOM_SEED"] = str(config.get("seed"))

        # 1. Run Migration if requested
        if config.get("run_migration"):
            migrate_script = os.path.join(PROJECT_ROOT, "migrate_v10.py")
            if os.path.isfile(migrate_script):
                try:
                    subprocess.run([sys.executable, "migrate_v10.py"], cwd=PROJECT_ROOT, env=env, check=True)
                except subprocess.CalledProcessError as e:
                    return {"status": "error", "message": f"Échec de la migration : {str(e)}"}

        # 2. Start Main Process
        try:
            self._logs.clear()
            self._logs.append(f"Starting {main_script}...")
            
            self._processes["main"] = subprocess.Popen(
                [sys.executable, main_script],
                cwd=PROJECT_ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            def read_logs(proc):
                for line in proc.stdout:
                    if line:
                        self._logs.append(line.rstrip("\n"))
            
            self._log_reader_thread = threading.Thread(target=read_logs, args=(self._processes["main"],), daemon=True)
            self._log_reader_thread.start()
            
            self._current_config = config
            self._stop_event.clear()
        except Exception as e:
            return {"status": "error", "message": f"Erreur démarrage {main_script}: {str(e)}"}

        # 3. Start Supervisor Thread if requested
        if config.get("enable_supervisor"):
            self._supervisor_thread = threading.Thread(target=self._supervisor_loop, args=(env,))
            self._supervisor_thread.daemon = True
            self._supervisor_thread.start()

        return {"status": "success", "message": f"Démarré {main_script} avec PID {self._processes['main'].pid}"}

    def _supervisor_loop(self, env: dict):
        supervisor_script = "src/graph_rag/supervisor.py"
        while not self._stop_event.is_set():
            if "main" in self._processes and self._processes["main"].poll() is not None:
                # Main process died, stop supervisor
                break
            
            # Run supervisor one-shot
            if os.path.isfile(os.path.join(PROJECT_ROOT, supervisor_script)):
                proc = subprocess.Popen([sys.executable, supervisor_script], cwd=PROJECT_ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self._processes["supervisor"] = proc
                for line in proc.stdout:
                    if line:
                        self._logs.append("🧠 [SUPERVISOR] " + line.rstrip("\n"))
                proc.wait() # wait for it to finish its evaluation pass
            
            # Sleep 10s before next evaluation, break early if stopped
            for _ in range(10):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

        # Post-run analysts (Idée A)
        if self._current_config:
            post_run_tools = []
            if self._current_config.get("run_sociologist"):
                post_run_tools.append("tools/sociologist.py")
            if self._current_config.get("run_linguist"):
                post_run_tools.append("tools/linguist.py")
            if self._current_config.get("run_metacognition"):
                post_run_tools.append("tools/metacognition_tracker.py")
            if self._current_config.get("run_dream_analyzer"):
                post_run_tools.append("tools/dream_analyzer.py")
                
            for tool_script in post_run_tools:
                if os.path.isfile(os.path.join(PROJECT_ROOT, tool_script)):
                    print(f"Running post-run analyst: {tool_script}")
                    subprocess.run([sys.executable, tool_script], cwd=PROJECT_ROOT, env=env)

    def stop(self) -> dict:
        self._stop_event.set() # Stop the supervisor thread

        messages = []
        for name, proc in list(self._processes.items()):
            if proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                messages.append(f"{name} arrêté")
        
        self._processes.clear()
        self._current_config = None
        
        if self._supervisor_thread:
            self._supervisor_thread.join(timeout=2)
            self._supervisor_thread = None

        return {"status": "success", "message": " | ".join(messages) if messages else "Aucune expérimentation en cours"}

    def get_status(self) -> dict:
        main_proc = self._processes.get("main")
        if main_proc and main_proc.poll() is None:
            return {
                "running": True,
                "script": self._current_config.get("script_name") if self._current_config else None,
                "pid": main_proc.pid,
                "config": self._current_config
            }
        
        # Cleanup if dead
        if main_proc:
            self.stop()

        return {
            "running": False,
            "script": None,
            "pid": None,
            "config": None
        }

sandbox_service = SandboxService()
