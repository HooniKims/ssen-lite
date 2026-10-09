"""Read the app's generated HWPX in an isolated Hancom COM instance; no source saves."""
import json
import pathlib
import sys
import winreg
import uuid
import win32com.client

sys.stdout.reconfigure(encoding="utf-8")
hwp = win32com.client.DispatchEx("HWPFrame.HwpObject")
results = []
registry_path = r"Software\HNC\HwpAutomation\Modules"
module_name = "SsenLiteTest_" + uuid.uuid4().hex
module = pathlib.Path(__file__).resolve().parent.parent / "_workspace/hancom/FilePathCheckerModuleExample.dll"
registry_key = None
try:
    if module.exists():
        registry_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path)
        winreg.SetValueEx(registry_key, module_name, 0, winreg.REG_SZ, str(module))
    registered = hwp.RegisterModule("FilePathCheckDLL", module_name)
    if not registered:
        raise RuntimeError("FilePathCheckerModule is unavailable; skip automated open")
    hwp.XHwpWindows.Active_XHwpWindow.Visible = False
    for name in sys.argv[1:]:
        file = pathlib.Path(name).resolve()
        if not hwp.Open(str(file), "HWPX", "forceopen:true"):
            raise RuntimeError(f"Hancom could not open {file.name}")
        text = hwp.GetTextFile("TEXT", "")
        controls = []
        ctrl = hwp.HeadCtrl
        while ctrl:
            controls.append(ctrl.CtrlID)
            ctrl = ctrl.Next
        results.append({"name": file.name, "pages": hwp.PageCount, "text": text, "controls": controls})
        hwp.Clear(1)
    if len(results) == 2:
        for field in ["pages", "text", "controls"]:
            if results[0][field] != results[1][field]:
                raise RuntimeError(f"Hancom {field} mismatch")
    print(json.dumps(results, ensure_ascii=False, indent=2))
finally:
    hwp.Quit()
    if registry_key:
        winreg.DeleteValue(registry_key, module_name)
        winreg.CloseKey(registry_key)
