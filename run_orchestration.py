import subprocess
import time
import os
import sys

def main():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    print("Launching multiverse_runner.py...")
    runner_proc = subprocess.Popen([sys.executable, "multiverse_runner.py"], env=env)
    
    print("Starting supervisor loop...")
    while runner_proc.poll() is None:
        print("Running supervisor.py...")
        subprocess.run([sys.executable, "src/graph_rag/supervisor.py"], env=env)
        time.sleep(10)
        
    print(f"Runner finished with code {runner_proc.returncode}.")

if __name__ == "__main__":
    main()
