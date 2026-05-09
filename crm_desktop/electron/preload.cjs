const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('desktop', {
  platform: process.platform,
  isElectron: true,
  apiRequest: (options) => ipcRenderer.invoke('api:request', options),
})
