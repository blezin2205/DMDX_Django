const { app, BrowserWindow, shell, ipcMain } = require('electron')
const path = require('node:path')
const axios = require('axios')

const isDev = Boolean(process.env.VITE_DEV_SERVER_URL)

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1024,
    minHeight: 700,
    title: 'DMDX CRM',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (isDev) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

app.whenReady().then(() => {
  ipcMain.handle('api:request', async (_event, options) => {
    const { method = 'GET', url, data, headers } = options ?? {}

    if (!url || typeof url !== 'string') {
      return { ok: false, error: 'Invalid URL' }
    }

    try {
      const response = await axios({
        method,
        url,
        data,
        headers,
        timeout: 10000,
      })

      return {
        ok: true,
        status: response.status,
        data: response.data,
      }
    } catch (error) {
      if (error.response) {
        return {
          ok: false,
          status: error.response.status,
          data: error.response.data,
        }
      }

      return {
        ok: false,
        error: error.message || 'Network error',
      }
    }
  })

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
