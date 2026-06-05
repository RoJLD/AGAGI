import json
import glob

files_to_recover = ['LaboratoryView.tsx', 'SandboxView.tsx', 'TimelineViewer.tsx', 'StrategyTreeViewer.tsx', 'IntrospectionViewer.tsx']
contents = {f: None for f in files_to_recover}

for log_file in glob.glob(r'C:\Users\robla\.gemini\antigravity\brain\*\.system_generated\logs\transcript.jsonl'):
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
                for tc in entry.get('tool_calls', []):
                    if tc.get('name') in ['write_to_file', 'replace_file_content', 'multi_replace_file_content']:
                        args_raw = tc.get('args', {})
                        if isinstance(args_raw, str):
                            try: args = json.loads(args_raw)
                            except: args = {}
                        else:
                            args = args_raw
                        fp = args.get('TargetFile', '')
                        if isinstance(fp, str):
                            if fp.startswith('"'):
                                try: fp = json.loads(fp)
                                except: pass
                        for fn in files_to_recover:
                            if 'laboratory' in fp.lower():
                                print(f"DEBUG: Found laboratory in fp: {fp}")
                            if fp.endswith(fn):
                                cc = args.get('CodeContent', '')
                                if isinstance(cc, str) and cc.startswith('"') and cc.endswith('"'):
                                    try: cc = json.loads(cc)
                                    except: pass
                                contents[fn] = cc
            except Exception as e:
                pass

for fn, text in contents.items():
    if text:
        print(f'Recovered {fn} ({len(text)} chars)')
        with open(f'c:/Users/robla/VScode_Project/AGIseed/frontend/src/components/{fn}', 'w', encoding='utf-8') as out:
            out.write(text.replace('8000', '8001'))
    else:
        print(f'{fn} still not found.')
