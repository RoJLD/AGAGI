import json
import os

transcript_path = r"C:\Users\robla\.gemini\antigravity\brain\7ed6ba12-f6f2-4679-b5b3-b49f01bcb9c7\.system_generated\logs\transcript.jsonl"
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if 'tool_calls' in data:
                for call in data['tool_calls']:
                    if call['name'] == 'write_to_file' and 'SandboxView.tsx' in str(call['args'].get('TargetFile', '')):
                        with open("SandboxView_full.tsx", "w", encoding='utf-8') as out:
                            out.write(call['args']['CodeContent'])
                        print("Done")
        except Exception:
            pass
