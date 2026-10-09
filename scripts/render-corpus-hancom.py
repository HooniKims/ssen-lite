"""Export test originals/results through Hancom, compare real pages/text/control lists."""
from pathlib import Path
import hashlib
import json
import sys
import time
import uuid
import winreg
import win32com.client

ROOT = Path(__file__).resolve().parent.parent
TEST = ROOT / 'test-documents'
OUTPUT = TEST / 'rendered'
OUTPUT.mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8')

def main():
    cases = json.loads((Path(sys.argv[1]) if len(sys.argv) > 1 else TEST / 'structural-report.json').read_text(encoding='utf-8'))
    cases = [case for case in cases if case['preset'] == 'balanced']
    module = ROOT / '_workspace/hancom/FilePathCheckerModuleExample.dll'
    registration = 'SsenLiteTest_' + uuid.uuid4().hex
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\HNC\HwpAutomation\Modules')
    winreg.SetValueEx(key, registration, 0, winreg.REG_SZ, str(module))
    hwp = None
    results = []
    try:
        hwp = win32com.client.DispatchEx('HWPFrame.HwpObject')
        if not hwp.RegisterModule('FilePathCheckDLL', registration):
            raise RuntimeError('Hancom module registration failed')
        hwp.XHwpWindows.Active_XHwpWindow.Visible = False
        for case in cases:
            pair = []
            for kind, name in [('original', case['source']), ('optimized', case['output'])]:
                source = Path(name)
                before = hashlib.sha256(source.read_bytes()).hexdigest()
                if not hwp.Open(str(source), 'HWPX', 'forceopen:true'):
                    raise RuntimeError('Hancom cannot open: ' + source.name)
                controls = []
                ctrl = hwp.HeadCtrl
                while ctrl:
                    controls.append(ctrl.CtrlID)
                    ctrl = ctrl.Next
                text = hwp.GetTextFile('TEXT', '')
                pdf = OUTPUT / (Path(case['file']).stem + '_' + kind + '.pdf')
                if not hwp.SaveAs(str(pdf), 'PDF', ''):
                    raise RuntimeError('Hancom PDF export failed: ' + source.name)
                item = {'kind': kind, 'source': str(source), 'pdf': str(pdf), 'pages': hwp.PageCount, 'text': text, 'controls': controls}
                hwp.Clear(1)
                if before != hashlib.sha256(source.read_bytes()).hexdigest():
                    raise RuntimeError('Source unexpectedly modified by rendering')
                pair.append(item)
                print(f"Rendered {source.name}: {item['pages']} pages", flush=True)
            matches = {field: pair[0][field] == pair[1][field] for field in ['pages', 'text', 'controls']}
            results.append({'file': case['file'], 'matches': matches, 'pair': pair, 'status': 'PASS' if all(matches.values()) else 'FAIL'})
            (TEST / 'hancom-report.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        if hwp:
            hwp.Quit()
        winreg.DeleteValue(key, registration)
        key.Close()
    if any(r['status'] != 'PASS' for r in results):
        raise RuntimeError('Hancom layout/text/control comparison failed')

if __name__ == '__main__':
    main()
