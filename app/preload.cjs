const {contextBridge,ipcRenderer,webUtils}=require('electron');
const listen=(channel,callback)=>{const fn=(_event,value)=>callback(value);ipcRenderer.on(channel,fn);return ()=>ipcRenderer.removeListener(channel,fn);};
contextBridge.exposeInMainWorld('lite',{
  selectFiles:()=>ipcRenderer.invoke('files:select'),
  addDropped:files=>ipcRenderer.invoke('files:add',Array.from(files).map(file=>webUtils.getPathForFile(file))),
  removeFile:id=>ipcRenderer.invoke('files:remove',id),clear:()=>ipcRenderer.invoke('files:clear'),demo:()=>ipcRenderer.invoke('files:demo'),
  chooseFolder:()=>ipcRenderer.invoke('folder:choose'),resetFolder:()=>ipcRenderer.invoke('folder:reset'),
  start:(ids,preset)=>ipcRenderer.invoke('task:start',ids,preset),cancel:()=>ipcRenderer.invoke('task:cancel'),
  showResult:id=>ipcRenderer.invoke('result:show',id),openResult:id=>ipcRenderer.invoke('result:open',id),
  onProgress:callback=>listen('task:progress',callback),onResult:callback=>listen('task:result',callback),
  updateState:()=>ipcRenderer.invoke('update:state'),checkUpdate:()=>ipcRenderer.invoke('update:check'),downloadUpdate:()=>ipcRenderer.invoke('update:download'),installUpdate:()=>ipcRenderer.invoke('update:install'),openRelease:()=>ipcRenderer.invoke('update:release'),onUpdate:callback=>listen('update:state',callback),
  minimize:()=>ipcRenderer.send('window:minimize'),maximize:()=>ipcRenderer.send('window:maximize'),close:()=>ipcRenderer.send('window:close')
});
