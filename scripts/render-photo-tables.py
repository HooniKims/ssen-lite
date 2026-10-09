"""Export both photo fixtures and all six packaged-app outputs in real Hancom."""
from pathlib import Path
import hashlib,json,sys,uuid,winreg
import win32com.client
ROOT=Path(__file__).resolve().parent.parent
CASE=ROOT/'test-documents/photo-tables-261009'
OUT=CASE/'rendered';OUT.mkdir(exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8')
rows=json.loads((CASE/'structural-report.json').read_text(encoding='utf-8'))
files=list(dict.fromkeys([r['source'] for r in rows]+[r['output'] for r in rows]))
registration='SsenLitePhoto_'+uuid.uuid4().hex
key=winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\HNC\HwpAutomation\Modules')
winreg.SetValueEx(key,registration,0,winreg.REG_SZ,str(ROOT/'_workspace/hancom/FilePathCheckerModuleExample.dll'))
hwp=None;rendered={}
try:
    hwp=win32com.client.DispatchEx('HWPFrame.HwpObject')
    assert hwp.RegisterModule('FilePathCheckDLL',registration)
    hwp.XHwpWindows.Active_XHwpWindow.Visible=False
    for n,name in enumerate(files):
        file=Path(name);before=hashlib.sha256(file.read_bytes()).hexdigest()
        assert hwp.Open(str(file),'HWPX','forceopen:true'),name
        pages=hwp.PageCount;text=hwp.GetTextFile('TEXT','');controls=[];ctrl=hwp.HeadCtrl
        while ctrl:controls.append(ctrl.CtrlID);ctrl=ctrl.Next
        pdf=OUT/f'{n:02d}_{file.stem}.pdf'
        assert hwp.SaveAs(str(pdf),'PDF',''),name
        hwp.Clear(1);assert before==hashlib.sha256(file.read_bytes()).hexdigest()
        rendered[name]={'pdf':str(pdf),'pages':pages,'text':text,'controls':controls,'sha256':before}
        print(n,file.name,pages,'pages',flush=True)
finally:
    if hwp:hwp.Quit()
    winreg.DeleteValue(key,registration);key.Close()
report=[]
for row in rows:
    a,b=rendered[row['source']],rendered[row['output']]
    matches={k:a[k]==b[k] for k in ['pages','text','controls']}
    report.append({**row,'originalRender':a,'optimizedRender':b,'matches':matches,'status':'PASS' if all(matches.values()) else 'FAIL'})
(CASE/'hancom-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert len(report)==6 and all(r['status']=='PASS' for r in report)
