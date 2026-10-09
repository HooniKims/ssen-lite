"""Normalize fixture namespaces and graft genuine Hancom line/table layout only."""
from pathlib import Path
import sys,json,uuid,winreg,zipfile,hashlib
import win32com.client
ROOT=Path(__file__).resolve().parent.parent
CASE=ROOT/'test-documents/photo-tables-261009'
sys.path.insert(0,str(Path.home()/'.codex/skills/hwpx/scripts'))
from fix_namespaces import fix_hwpx_namespaces
from hancom_layout import graft
sys.stdout.reconfigure(encoding='utf-8')
fixture=json.loads((CASE/'fixture.json').read_text(encoding='utf-8'))
registration='SsenLitePhoto_'+uuid.uuid4().hex
key=winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\HNC\HwpAutomation\Modules')
winreg.SetValueEx(key,registration,0,winreg.REG_SZ,str(ROOT/'_workspace/hancom/FilePathCheckerModuleExample.dll'))
hwp=None
try:
    hwp=win32com.client.DispatchEx('HWPFrame.HwpObject')
    assert hwp.RegisterModule('FilePathCheckDLL',registration)
    hwp.XHwpWindows.Active_XHwpWindow.Visible=False
    for item in [fixture,fixture['separateEmbedding']]:
        source=Path(item['source']);fix_hwpx_namespaces(str(source))
        with zipfile.ZipFile(source) as z:before={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('BinData/')}
        assert hwp.Open(str(source),'HWPX','forceopen:true')
        pages=hwp.PageCount
        laid=CASE/(source.stem+'_layout.hwpx')
        assert hwp.SaveAs(str(laid),'HWPX','')
        hwp.Clear(1)
        graft(str(source),str(laid),str(source))
        with zipfile.ZipFile(source) as z:after={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('BinData/')}
        assert before==after
        item['bytes']=source.stat().st_size;item['initialPages']=pages
        print(source.name,pages,'pages',item['bytes'],'bytes',flush=True)
finally:
    if hwp:hwp.Quit()
    winreg.DeleteValue(key,registration);key.Close()
(CASE/'fixture.json').write_text(json.dumps(fixture,ensure_ascii=False,indent=2),encoding='utf-8')
