#!/usr/bin/env python
import os
import sys
import io
import re
import configparser
import collections
import struct
import subprocess
import time
import threading
import random
import webbrowser
import tkinter
from tkinter import *
import tkinter.font as font
from tkinter import filedialog
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.widgets import *
from ttkbootstrap.widgets import scrolled
from ttkbootstrap.widgets.tableview import Tableview
from ttkbootstrap.constants import *
from PIL import ImageTk, Image
from sng_parsing import Sng

appVersion = "v1.0.0"

print("FastGH3 Launcher " + appVersion)
print("Created by Yoshibyl (https://github.com/Yoshibyl/)")

repoURL = "https://github.com/Yoshibyl/FastGH3Launcher-python"

if sys.platform == "win32":
    print("\nThis program is designed for Linux, so there may be issues on Windows.\nPlease consider using FGH3ChartBrowser for now:\n - https://github.com/Yoshibyl/FGH3ChartBrowser")

# Stuff for case-insensitive ini parsing.
# Shamelessly taken from Google searches
class CaseInsensitiveDict(collections.abc.MutableMapping):
    def __init__(self, *args, **kwargs):
        self._d = collections.OrderedDict(*args, **kwargs)
        self._convert_keys()
    def _convert_keys(self):
        for k in list(self._d.keys()):
            v = self._d.pop(k)
            self._d.__setitem__(k, v)
    def __len__(self):
        return len(self._d)
    def __iter__(self):
        return iter(self._d)
    def __setitem__(self, k, v):
        self._d[k.lower()] = v
    def __getitem__(self, k):
        return self._d[k.lower()]
    def __delitem__(self, k):
        del self._d[k.lower()]
    def copy(self):
        result = CaseInsensitiveDict()
        for k, v in self.items():
            result[k] = v
        return result

# INI parsing and app configuration

defaultLaunchCommand = "wine \"$fastgh3path\" \"Z:$chart\""
defaultFGH3ExePath = ""
if sys.platform == "win32":
    defaultLaunchCommand = "\"$fastgh3path\" \"$chart\""
    defaultFGH3ExePath = "C:/Program Files (x86)/FastGH3/FastGH3.exe"

appcfg = configparser.ConfigParser(allow_no_value=True, strict=False, interpolation=None)
defaultGeneral = {
    "scan_folder":"", 
    "auto_scan":"true", 
    "launch_command": defaultLaunchCommand, 
    "app_theme":"Dark", 
    "fastgh3_path":defaultFGH3ExePath
}
def update_config(reload=False):
    global appcfg
    if not os.path.exists("config.ini"):
        appcfg["general"] = defaultGeneral
    if reload:
        appcfg.read("config.ini")
        if "general" not in appcfg.sections():
            appcfg["general"] = defaultGeneral
        for k in defaultGeneral.keys():
            if k not in appcfg["general"].keys(): appcfg["general"][k] = defaultGeneral[k]
    else:
        appcfg["general"]["fastgh3_path"] = fgh3ExePathVar.get()
        appcfg["general"]["launch_command"] = launchCmdVar.get()
    with open("config.ini", "w") as cfgfile:
        appcfg.write(cfgfile)
        cfgfile.close()
## read the ini...
update_config(True)

# Functions and stuff
def fixstring(inputstr=""):
    CLEANR = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
    fixedStr = ''.join(c if c <= '\uffff' else ''.join(chr(x) for x in struct.unpack('>2H', c.encode('utf-8'))) for c in inputstr)
    fixedStr = fixedStr.replace("<br>","\n")
    fixedStr = re.sub(CLEANR, "", fixedStr)
    return fixedStr

def treeview_sort_column(tv, col, reverse):
    l = [(tv.set(k, col), k) for k in tv.get_children('')]
    l.sort(reverse=reverse)
    # rearrange items in sorted positions
    for index, (val, k) in enumerate(l):
        tv.move(k, '', index)
    # scroll to selected item (if any)
    if tv.selection():
        sel = tv.selection()
        tv.focus(sel)
        tv.see(sel)
        tv.update()
    # reverse sort next time
    tv.heading(col, command=lambda: \
        treeview_sort_column(tv, col, not reverse))

def browseForSongFolder(path="",forceScan=False):
    global appcfg
    global root
    global scanMeter
    global cancelling
    global songDataList
    global songDataListBackup
    global folderPath
    global isScanning
    root.update()
    autoScanPath = folderVar.get()
    if path == "":
        if forceScan:
            browsePath = autoScanPath
        else:
            if len(autoScanPath) > 1 and os.path.exists(autoScanPath):
                browsePath = filedialog.askdirectory(initialdir=autoScanPath)
            else:
                browsePath = filedialog.askdirectory()
    else:
        browsePath = autoScanPath
    if len(browsePath) > 0:
        isScanning = True
        folderVar.set(browsePath)
        folderEntry.config(state="disabled")
        browseBtn.config(state="disabled")
        scanBtn.config(bootstyle="danger")
        scanTxtVar.set("Cancel Scan")
        root.update()
        appcfg["general"]["scan_folder"] = browsePath
        update_config()
        startTime = time.perf_counter()
        print("Scanning folder: " + browsePath)
        scanMeter.configure(mode="indeterminate", value=0)
        songDataListBackup = songDataList
        songDataList = []
        scanTxtVar.set("Cancel Scan")
        root.update()
        folderPath = browsePath
        getCharts(folderPath)
        if cancelling == False:
            songDataListBackup = songDataList
            for i in songListBox.get_children():
                songListBox.delete(i)
            children = songListBox.get_children()
            if children:
                songListBox.yview_moveto(0)
                songListBox.focus(children[0])
                songListBox.selection_set(children[0])
            endTime = time.perf_counter()
            execTime = endTime - startTime
            print(f"Took {execTime:.4f} seconds to scan")
        else:
            scanTxtVar.set("Scan Songs")
            songDataList = songDataListBackup
    elif forceScan:
        tkinter.messagebox.askok("Error", "You must select a folder to scan songs from.")
    folderEntry.config(state="enabled")
    browseBtn.config(state="enabled")
    if not cancelling:
        treeview_sort_column(songListBox, songListBox["columns"][1], False)
        filter_songs()
    isScanning = False
    cancelling = False
    scanTxtVar.set("Scan Songs")
    scanBtn.config(bootstyle="default")
    root.update()

def scanBtnClick(event=None):
    global isScanning
    global cancelling
    if not isScanning:
        browseForSongFolder(forceScan=True)
    else:
        cancelling = True

def loadMetadata(event):
    selectedSong = songListBox.selection()
    global albumPhoto
    global albumPath
    global lastSelectedPath
    if selectedSong:
        albumPath = songListBox.set(selectedSong, "Album Path")
        lastSelectedPath = albumPath
        albumThread = threading.Thread(target=loadAlbumArtWorker)
        albumThread.start()
        albumName = songListBox.set(selectedSong, "Album")
        artist = songListBox.set(selectedSong, "Artist")
        artistVar.set(artist)
        tipArtist.text = artist
        albumVar.set("Album:  "+albumName)
        tipAlbum.text = albumName
        genreTxt = songListBox.set(selectedSong, "Genre")
        genreVar.set("Genre:  " + genreTxt)
        tipGenre.text = genreTxt
        yearTxt = songListBox.set(selectedSong, "Year")
        yearTxtVar.set("Year:  " + yearTxt[:4])
        tipYear.text = yearTxt
        charter = songListBox.set(selectedSong, "Charter")
        charterVar.set("Charter:  " + charter)
        tipCharter.text = charter
        title = songListBox.set(selectedSong, "Title")
        songTitleVar.set(title)
        tipTitle.text = title
        loadingPhrase = songListBox.set(selectedSong, "Loading Phrase")
        loadingScrTxt.config(state="normal")
        loadingScrTxt.delete(1.0, END)
        loadingScrTxt.insert(1.0, loadingPhrase, END)
        loadingScrTxt.reset_height()
        loadingScrTxt.config(state="disabled")

def loadAlbumArtWorker():
    global lastSelectedPath
    global albumPath
    global albumPhoto
    global blankAlbum
    if os.path.isfile(albumPath):
        try:
            albumImage = Image.open(albumPath)
            albumResized = albumImage.resize((300,300), Image.Resampling.LANCZOS)
            if lastSelectedPath == albumPath:
                albumPhoto = ImageTk.PhotoImage(albumResized)
                albumLabel.configure(image=albumPhoto)
        except: albumLabel.configure(image=blankAlbum)
    else:
        albumPhoto = ImageTk.PhotoImage(blankAlbum)
        albumLabel.configure(image=albumPhoto)

def openImageExternally(event=None):
    selectedSong = songListBox.selection()
    albumPath = songListBox.set(selectedSong, "Album Path")
    if len(albumPath) > 0:
        if sys.platform == "win32":
            os.startfile(os.path.abspath(albumPath))
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, os.path.abspath(albumPath)])

def getCharts(songsFolder=""):
    global songsFound
    global songsScanned
    global scanErrors
    global root
    global scanMeter
    global cancelling
    if os.path.isdir(songsFolder) and len(songsFolder) > 0:
        songPaths = []
        iniPaths = []
        albumPaths = []
        for froot, dirs, files in os.walk(songsFolder):
            for dir in dirs:
                if os.path.exists(os.path.abspath(os.path.join(froot,dir,"notes.chart"))) and os.path.exists(os.path.abspath(os.path.join(froot,dir,"song.ini"))):
                    notesChart = os.path.abspath(os.path.join(froot,dir,"notes.chart"))
                    songPaths += [notesChart.replace("\\","/")]
                    songIni = os.path.abspath(os.path.join(froot,dir,"song.ini"))
                    iniPaths += [songIni.replace("\\","/")]
                    if os.path.exists(os.path.abspath(os.path.join(froot,dir,"album.jpg"))):
                        albumPaths += [os.path.abspath(os.path.join(froot,dir,"album.jpg")).replace("\\","/")]
                    elif os.path.exists(os.path.abspath(os.path.join(froot,dir,"album.png"))):
                        albumPaths += [os.path.abspath(os.path.join(froot,dir,"album.png")).replace("\\","/")]
                    else:
                        albumPaths += [""]
                elif os.path.exists(os.path.abspath(os.path.join(froot,dir,"notes.mid"))) and os.path.exists(os.path.abspath(os.path.join(froot,dir,"song.ini"))):
                    notesMid = os.path.abspath(os.path.join(froot,dir,"notes.mid"))
                    songPaths += [notesMid.replace("\\","/")]
                    songIni = os.path.abspath(os.path.join(froot,dir,"song.ini"))
                    iniPaths += [songIni.replace("\\","/")]
                    if os.path.exists(os.path.abspath(os.path.join(froot,dir,"album.jpg"))):
                        albumPaths += [os.path.abspath(os.path.join(froot,dir,"album.jpg")).replace("\\","/")]
                    elif os.path.exists(os.path.abspath(os.path.join(froot,dir,"album.png"))):
                        albumPaths += [os.path.abspath(os.path.join(froot,dir,"album.png")).replace("\\","/")]
                    else:
                        albumPaths += [""]
                if cancelling: break
            for fil in files:
                if fil.lower().endswith(".sng"):
                    sng = os.path.abspath(os.path.join(froot,fil))
                    songPaths += [sng.replace("\\","/")]
                    albumPaths += [sng.replace("\\","/")]
                    # albumPaths += ["./sngcache/" + fil + "/album.png"] ## old method? idk
                    iniPaths += [sng.replace("\\","/")]
                if cancelling: break
            if cancelling: break
        if not cancelling:
            print("Total songs found: " + str(len(songPaths)))
            print("ATTENTION! Scanning may take a while, especially with a lot of songs and/or slow hardware.")
            j = 0
            scanErrors = 0
            songsFound = len(songPaths)
            scanMeter.configure(mode="determinate", value=0, maximum=songsFound)
            songsScanned = 0
            cpu_cores = os.cpu_count()
            if cpu_cores >= 2: cpu_cores = int(cpu_cores / 2)
            scanThreads = []
            for i in range(0,cpu_cores):
                songBatch = songPaths[i::cpu_cores]
                iniBatch = iniPaths[i::cpu_cores]
                albumBatch = albumPaths[i::cpu_cores]
                scanThreadN = threading.Thread(target=songScanThread, args=(songBatch,iniBatch,albumBatch,i))
                scanThreadN.start()
                scanThreads.append(scanThreadN)
            for scanner in scanThreads:
                while scanner.is_alive():
                    root.update()
                    # time.sleep(0.01)
        if not cancelling:
            print("Progress: 100%\nParsing complete.")
            if scanErrors > 0: print("%i error(s) in scanning." % scanErrors)
            filter_songs()
        else:
            print("Scan cancelled")

def songScanThread(song_paths, ini_paths, album_paths, chunk=0):
    global songsFound
    global songsScanned
    global scanErrors
    global root
    global scanMeter
    j = 0
    config = configparser.ConfigParser(allow_no_value=True, strict=False, dict_type=CaseInsensitiveDict, interpolation=None)
    for song in song_paths:
        if cancelling: break
        title = ""
        artist = ""
        album = ""
        year = ""
        genre = ""
        charter = ""
        loadingPhrase = ""
        validSong = True
        config.clear()
        if os.path.isfile(ini_paths[j]):
            if ini_paths[j].lower().endswith(".ini"):
                with open(ini_paths[j], 'rb') as cf:
                    configRaw = cf.read()
                    cf.close()
                    if len(configRaw) < 6:
                        validSong = False
                        print("INI error: " + ini_paths[j])
                        scanErrors += 1
                    else:
                        configStr = configRaw.decode("utf-8-sig", errors="replace").replace("\x00","") # .replace('\"', '\\\"')
                        configStr = configStr[configStr.find("["):]
                        
                        configStrIO = io.StringIO(configStr)
                        config.read_file(configStrIO)
                if validSong:
                    if "name" in config["song"]: title = fixstring(config["song"]["name"])
                    if "artist" in config["song"] : artist = fixstring(config["song"]["artist"])
                    if "album" in config["song"] : album = fixstring(config["song"]["album"])
                    if "year" in config["song"] : year = fixstring(config["song"]["year"])
                    if "genre" in config["song"] : genre = fixstring(config["song"]["genre"])
                    if "charter" in config["song"]: charter = fixstring(config["song"]["charter"])
                    if "loading_phrase" in config["song"]: loadingPhrase = fixstring(config["song"]["loading_phrase"])
            elif ini_paths[j].lower().endswith(".sng"):
                sngf = Sng.Load(ini_paths[j])
                if "name" in sngf.meta:             title = fixstring(sngf.meta["name"])
                if "artist" in sngf.meta:           artist = fixstring(sngf.meta["artist"])
                if "album" in sngf.meta:            album = fixstring(sngf.meta["album"])
                if "year" in sngf.meta:             year = fixstring(sngf.meta["year"])
                if "genre" in sngf.meta:            genre = fixstring(sngf.meta["genre"])
                if "charter" in sngf.meta:          charter = fixstring(sngf.meta["charter"])
                if "loading_phrase" in sngf.meta:   loadingPhrase = fixstring(sngf.meta["loading_phrase"])
                for sf in sngf.files:
                    ## Extract album art from `.sng` to cache folder.
                    # Existing cached images will only be replaced with higher resolution, if any
                    # !!Always make sure to limit the size of file names!!
                    disallowedPathChars = r'[<>:"/\\|?*]'
                    if sf.name.startswith("album"):
                        album_paths[j] = "./sngcache/albums/%s - %s" % (re.sub(disallowedPathChars, "_", sngf.meta["artist"])[:50], re.sub(disallowedPathChars, "_", sngf.meta["album"])[:50])
                        if not os.path.exists("./sngcache/albums"):
                            os.makedirs("./sngcache/albums")
                        album_paths[j] += sf.name.replace("album","")
                        oldwidth = 0
                        oldheight = 0
                        if os.path.exists(album_paths[j]):
                            try:
                                oldimg = Image.open(album_paths[j])
                                oldwidth, oldheight = oldimg.size
                            except Exception as e:
                                print(f"Oops! {e}")
                        newimg = Image.open(io.BytesIO(sf.data))
                        newwidth, newheight = newimg.size
                        if newwidth > oldwidth:
                            with open(album_paths[j], "wb") as albumBin:
                                albumBin.write(bytes(sf.data))
                                albumBin.close()
                        break
            # Add song data to the list
            if validSong:
                songdata = (artist, title, album, year, genre, charter, song, album_paths[song_paths.index(song)], loadingPhrase)
                songDataList.append(songdata)
                songsScanned += 1
            # scanTxtVar.set("Scanning... %d" % (songsScanned * 100.0 / songsFound) + "%")
            # scanMeter.configure(value=(songsScanned * 100.0 / songsFound))
            scanMeter.step()
            print("Progress: %d" % (songsScanned * 100.0 / songsFound) + "%  ", end="\r")
        j+=1

def filter_songs(event=None):
    global lastSelectedPath
    global songDataList

    filterMode = filterBy.get().lower() + ""
    query = filterTxt.get().lower().replace(" ","").replace("-","")
    lastSelection = songListBox.item(songListBox.selection())["values"]
    if lastSelection:
        lastSelectedPath = "no_selection"
    lastSelectedIndex = 0
    if len(lastSelection) >= 6:
        lastSelectedPath = lastSelection[6]
        # print(lastSelectedPath)
    sortmode = "Title"
    if len(query) > 0 and not query.isspace():
        for item in songListBox.get_children():
            songListBox.delete(item)
        index = 0
        for entry in songDataList:
            matched = False
            if filterMode == "artist":
                artist = entry[0].lower().replace(" ","").replace("-","")
                if artist.startswith(query):
                    matched = True
            elif filterMode == "title":
                title = entry[1].lower().replace(" ","").replace("-","")
                if title.startswith(query):
                    matched = True
            elif filterMode == "album":
                album = entry[2].lower().replace(" ","").replace("-","")
                if query in album:
                    matched = True
            elif filterMode == "year":
                year = entry[3].replace(" ","").replace("-","")
                if year.endswith(query) or year.startswith(query):
                    matched = True
            elif filterMode == "genre":
                genre = entry[4].lower().replace(" ","").replace("-","")
                if query in genre:  matched = True
            elif filterMode == "charter":
                charter = entry[5].lower().replace(" ","").replace("-","")
                if query in charter:
                    matched = True
            elif filterMode == "any":
                artist = entry[0].lower().replace(" ","").replace("-","")
                title = entry[1].lower().replace(" ","").replace("-","")
                album = entry[2].lower().replace(" ","").replace("-","")
                genre = entry[4].lower().replace(" ","").replace("-","")
                charter = entry[5].lower().replace(" ","").replace("-","")
                results = artist + title + artist + album + genre + charter
                if query in results:    matched = True
            if matched:
                songListBox.insert("","end",values=entry)
                if lastSelectedPath in entry:
                    lastSelectedIndex = index
                index += 1
    else:
        for item in songListBox.get_children():
            songListBox.delete(item)
        index = 0
        for entry in songDataList:
            songListBox.insert("","end",values=entry)
            if lastSelectedPath in entry:
                lastSelectedIndex = index
            index += 1
    
    if filterMode == "artist":      sortmode = "Artist"
    elif filterMode == "album":     sortmode = "Album"
    elif filterMode == "year":      sortmode = "Year"
    elif filterMode == "genre":     sortmode = "Genre"
    elif filterMode == "charter":   sortmode = "Charter"
    treeview_sort_column(songListBox, sortmode, False)
    children = songListBox.get_children()
    if children:
        for child in children:
            if lastSelectedPath in songListBox.item(child)["values"]:
                songListBox.focus(child)
                songListBox.selection_set(child)
                songListBox.see(child)
                songListBox.update()
                break

def rcSongList(event):
    selectedChart = songListBox.selection()
    chartPath = songListBox.set(selectedChart, "Chart Path")
    if len(chartPath) > 0:
        try:
            rcMenuSongList.tk_popup(event.x_root + 5, event.y_root + 5)
        finally:
            rcMenuSongList.grab_release()
def rcAlbumArt(event):
    selectedChart = songListBox.selection()
    albumPath = songListBox.set(selectedChart, "Album Path")
    if os.path.isfile(albumPath):
        try:
            rcMenuAlbumArt.tk_popup(event.x_root + 5, event.y_root + 5)
        finally:
            rcMenuAlbumArt.grab_release()

def rcSongList_Unfocus(event=None):
    rcMenuSongList.unpost()
    rcMenuAlbumArt.unpost()

def openSongFolder():
    selectedChart = songListBox.selection()
    if selectedChart:
        chartPath = songListBox.set(selectedChart, "Chart Path")
        if len(chartPath) > 0:
            if sys.platform == "win32":
                subprocess.Popen(f"explorer.exe /select,\"{os.path.abspath(chartPath)}\"")
            elif sys.platform == "darwin": # Can't test this because I don't have a mac
                try:
                    subprocess.call(["open", "-R",  os.path.abspath(chartPath)])
                except:
                    print("Error: Couldn't open the chart in Finder because Apple.\nThis is a bug, please let Yoshibyl know (as if I could fix it)")
            else:
                subprocess.call(["xdg-open", os.path.dirname(os.path.abspath(chartPath))])

def launchSong(event=None):
    launchThread = threading.Thread(target=launchSongThread)
    launchThread.start()

def launchSongThread():
    global launchCmd
    global chartLaunchPath
    global appcfg
    selectedChart = songListBox.selection()
    chartLaunchPath = songListBox.set(selectedChart, "Chart Path")
    launchCmd = appcfg["general"]["launch_command"]
    launchCmdSplit = launchCmd.split(" ")
    bruh = 0
    for argument in launchCmdSplit:
        if "$fastgh3path" in argument:
            launchCmdSplit[bruh] = launchCmdSplit[bruh].replace("$fastgh3path", appcfg["general"]["fastgh3_path"])
        if "$chart" in argument:
            launchCmdSplit[bruh] = launchCmdSplit[bruh].replace("$chart", chartLaunchPath)
        bruh += 1
    if len(chartLaunchPath) > 0:
        launchBtn.config(state="disabled", text="Loading...")
        fgh3SettingsBtn.config(state="disabled")
        feelingLuckyBtn.config(state="disabled")
        if os.path.isfile(appcfg["general"]["fastgh3_path"]):
            try:
                print(launchCmdSplit)
                print("Loading chart %s" % chartLaunchPath)
                subprocess.call(launchCmd.replace("$fastgh3path", appcfg["general"]["fastgh3_path"]).replace("$chart", chartLaunchPath), shell=True)
            except:
                print("An error occurred trying to launch the chart:\n" + chartLaunchPath)
                tkinter.messagebox.showerror("Error", "An error occurred while attempting to launch.  Check the launch command in Other Settings, and try again.")
        else:
            tkinter.messagebox.showerror("Error", "FastGH3.exe could not be found.  Set it in Other Settings, and try again.")
        launchBtn.config(state="enabled", text="Play Song")
        fgh3SettingsBtn.config(state="enabled")
        feelingLuckyBtn.config(state="enabled")

def launchFastGH3Settings(event=None):
    settingsThread = threading.Thread(target=fgh3SettingsThread)
    settingsThread.start()

def fgh3SettingsThread():
    global launchCmd
    global appcfg
    launchCmd = appcfg["general"]["launch_command"]
    launchCmdSplit = launchCmd.split(" ")
    bruh = 0
    for argument in launchCmdSplit:
        if "$fastgh3path" in argument:
            launchCmdSplit[bruh] = launchCmdSplit[bruh].replace("$fastgh3path", appcfg["general"]["fastgh3_path"])
        if "$chart" in argument:
            launchCmdSplit[bruh] = "-settings"
        bruh += 1
    fgh3SettingsBtn.config(state="disabled", text="Loading settings (be patient)")
    launchBtn.config(state="disabled")
    feelingLuckyBtn.config(state="disabled")
    try:
        print(launchCmdSplit)
        if os.path.isfile(appcfg["general"]["fastgh3_path"]):
            subprocess.call(" ".join(launchCmdSplit), shell=True)
        else:
            tkinter.messagebox.showerror("Error", "FastGH3.exe could not be found.  Set it in Other Settings, and try again.")
        fgh3SettingsBtn.config(state="enabled", text="FastGH3 Settings")
    except:
        print("An error occurred trying to launch FastGH3 settings")
        fgh3SettingsBtn.config(state="enabled", bootstyle="danger", text="Error opening FastGH3")
        tkinter.messagebox.showerror("Error", "An error occurred attempting to launch FastGH3.  Did you set the launch command and FastGH3 path correctly?")
        fgh3SettingsBtn.config(state="enabled", bootstyle="default", text="FastGH3 Settings")
    launchBtn.config(state="enabled")
    feelingLuckyBtn.config(state="enabled")

def updateTheme(event=None):
    themeOption.config(width=5)
    themeVal = themeTxt.get()
    if themeVal == "Dark":
        root.style.theme_use("darkly")
    elif themeVal == "Black":
        root.style.theme_use("cyborg")
    elif themeVal == "Light":
        root.style.theme_use("cosmo")
    # change scrollbar size and row height
    style = ttk.Style(root)
    style.configure("Vertical.TScrollbar", arrowsize=25)
    style.configure("Treeview", font=("Segoe UI",12), rowheight=27)
    style.configure("info.TButton", font=("Segoe UI", 20))
    # make loading phrase box same color as window
    windowBg = style.lookup("TWindow", "background")
    loadingScrTxt.config(font=("Segoe UI",11), background=windowBg, highlightthickness=0)
    # update the theme in config
    appcfg["general"]["app_theme"] = themeVal
    update_config()

def openBrowserFastGH3(event=None):
    webbrowser.open_new_tab("https://github.com/donnaken15/FastGH3/releases")
def openBrowserLauncherRepo(event=None):
    webbrowser.open_new_tab(repoURL)

## SETTINGS DIALOG
class SettingsWindow(tb.Toplevel):
    alive = False
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config(width=640, height=400)
        self.title("Settings")

        self.settNb = tb.Notebook(self, width=715, height=325)
        # Settings Page 1: General
        self.settFrameGeneral = ttk.Frame(self.settNb, width=700, height=300)
        self.settAutoScan = tb.Checkbutton(self.settFrameGeneral, text="Auto-scan song folder on start", variable=autoScanVar, command=self.autoScanToggle, bootstyle="round-toggle")
        self.settAutoScan.grid(row=0, column=0, padx=10, pady=10, columnspan=5)
        self.settFgh3ExeLabel = tb.Label(self.settFrameGeneral, text="FastGH3.exe path: ")
        self.settFgh3ExeEntry = tb.Entry(self.settFrameGeneral, width=40, textvariable=fgh3ExePathVar)
        self.settFgh3ExeLabel.grid(row=1,column=0,padx=10,pady=0, sticky=E)
        self.settFgh3ExeEntry.grid(row=1,column=1,padx=0,pady=0,columnspan=3,sticky=W)
        self.settFgh3BrowseBtn = tb.Button(self.settFrameGeneral, text="Choose file", width=10, command=self.browseForFastGH3exe)
        self.settFgh3BrowseBtn.grid(row=1,column=4,padx=0,pady=0,columnspan=1,sticky=W)
        self.settLaunchCmdLabel = tb.Label(self.settFrameGeneral, text="Launch Command: ")
        self.settLaunchCmdLabel.grid(row=2,column=0,padx=10,pady=10,sticky=E)
        self.settLaunchCmdEntry = tb.Entry(self.settFrameGeneral, width=55, textvariable=launchCmdVar)
        self.settLaunchCmdEntry.grid(row=2,column=1,columnspan=4,sticky=W)
        self.settLaunchVarsInfo = tb.Text(self.settFrameGeneral, width=85, wrap="word", height=7)
        self.settLaunchVarsInfo.insert(1.0, "$fastgh3path : The path to FastGH3.exe\n$chart : The path to the selected song.\n\nTo launch with Proton instead of Wine on Linux, I recommend umu-run.\nIf your guitar isn't working properly with the game, try placing xinput1_3.dll from the GitHub in FastGH3's directory and, if on Linux, add the prefix WINEDLLOVERRIDES=\"xinput1_3=n\"\nSee the README.md for more details.", END)
        self.settLaunchVarsInfo.configure(state="disabled", highlightthickness=0)
        self.settLaunchVarsInfo.grid(row=3,column=0,columnspan=5, padx=10)
        self.settNb.add(self.settFrameGeneral, text="General")
        # Settings page 2: to do later

        # About page
        self.aboutFrame = ttk.Frame(self.settNb, width=700,height=300)
        self.aboutTxt = tb.Text(self.aboutFrame, width=88, wrap="word", height=8)
        self.aboutTxt.insert(1.0, "FastGH3 Launcher by Yoshibyl (Yoshi): https://github.com/Yoshibyl/FastGH3Launcher-python \n\nFastGH3 is a modified version of Guitar Hero III (originally developed by Neversoft and ported to PC by Aspyr) put together by donnaken15 that allows for loading directly into custom songs (charts).  This launcher is designed to make it easier to browse your song library for playable charts in FastGH3, especially on Linux via Wine/Proton.\n\nGet FastGH3 here: https://github.com/donnaken15/FastGH3/releases", END)
        self.aboutTxt.configure(state="disabled", highlightthickness=0)
        self.aboutTxt.grid(row=0,column=0)
        self.aboutGithubFGH3Btn = tb.Button(self.aboutFrame, width=67, text="FastGH3 on GitHub (opens browser)", command=openBrowserFastGH3)
        self.aboutGithubFGH3Btn.grid(row=1,column=0,pady=20)
        self.aboutGithubLauncherBtn = tb.Button(self.aboutFrame, width=67, text="FastGH3 Launcher on GitHub (opens browser)", command=openBrowserLauncherRepo)
        self.aboutGithubLauncherBtn.grid(row=2,column=0,pady=0)
        self.settNb.add(self.aboutFrame, text="About")

        self.settNb.grid(row=0,column=0,columnspan=2)
        self.settCloseBtn = tb.Button(self, text="[Esc]  Save and close", width=40, command=self.destroy, bootstyle="danger")
        self.bind("<Escape>", self.destroy)
        self.settCloseBtn.grid(row=1,column=0,columnspan=2,padx=10,pady=10)

        self.geometry()
        self.resizable(False, False)
        self.focus()
        self.__class__.alive = True
    def autoScanToggle(self):
        appcfg["general"]["auto_scan"] = str(autoScanVar.get())
        update_config()
        # print("Auto scan set: " + str(autoScanVar.get()))
    def browseForFastGH3exe(self, event=None):
        self.newExePath = None
        self.fgh3ParentDir = os.path.dirname(fgh3ExePathVar.get())
        if os.path.isfile(fgh3ExePathVar.get()):
            self.newExePath = tkinter.filedialog.askopenfilename(parent=self, initialdir=self.fgh3ParentDir, filetypes=[("Windows Executables","*.exe")])
        else:
            self.newExePath = tkinter.filedialog.askopenfilename(parent=self, initialdir=self.fgh3ParentDir, filetypes=[("Windows Executables","*.exe")])
        if len(self.newExePath) > 0:
            if os.path.isfile(self.newExePath):
                fgh3ExePathVar.set(self.newExePath)
    def destroy(self, event=None):
        update_config()
        self.__class__.alive = False
        return super().destroy()
# Settings dialog class end, function for opening it below
def openSettingsDialog():
    if not SettingsWindow.alive:
        settWin = SettingsWindow()
# Loading phrase box class (actually created towards the end of the script)
# Code credit (scroll down to the checked answer): https://stackoverflow.com/questions/46081798/automatically-resize-text-widgets-height-to-fit-all-text
# (#CreditTheCreators)
class FlexibleText(tb.Text):
    previous_height = 0
    def insert(self, *args, **kwargs):
        result = tb.Text.insert(self, *args, **kwargs)
        self.reset_height()
        return result
    def reset_height(self):
        height = self.tk.call((self._w, "count", "-update", "-displaylines", "1.0", "end"))
        if height != self.previous_height:
            self.configure(height=height)
            self.update()
            self.previous_height = height
# Function for truncating labels if too long (not working?)
def truncateLabel(event):
    lbl = event.widget
    if not hasattr(lbl, "original_text"):
        lbl.original_text = artistVar.get()
    font = textFont
    txt = lbl.original_text
    maxWidth = infoFrameL.winfo_width()
    # print("Max width %i" % maxWidth)
    actualWidth = font.measure(txt)
    if actualWidth <= maxWidth:
        artistVar.set(txt)
    else:
        while actualWidth > maxWidth and len(txt) > 1:
            txt = txt[:-1]
            actualWidth = font.measure(txt + "...")
            # print(actualWidth)
        artistVar.set(txt)
# Scrolling faster with PageUp/PageDown or Left/Right
def pageUp(event=None):
    children = songListBox.get_children()
    selection = songListBox.selection()
    if children and selection:
        index = songListBox.index(selection)
        index -= 10
        if index < 0: index = 0
        songListBox.focus(children[index])
        songListBox.selection_set(children[index])
        songListBox.update()
        songListBox.see(children[index])
def pageDown(event=None):
    children = songListBox.get_children()
    selection = songListBox.selection()
    if children and selection:
        index = songListBox.index(selection)
        index += 10
        if index >= len(children): index = len(children) - 1
        songListBox.focus(children[index])
        songListBox.selection_set(children[index])
        songListBox.update()
        songListBox.see(children[index])
# random song selection
def selectRandomSong(event=None):
    numSongs = len(songListBox.get_children())
    if numSongs > 1:
        randomIndex = random.randrange(numSongs)
        songListBox.focus_set()
        randSong = songListBox.get_children()[randomIndex]
        songListBox.selection_set(randSong)
        songListBox.see(randSong)
        songListBox.update()
def feelLucky(event=None):
    selectRandomSong()
    launchSong()
# on window close
def onCloseWindow(event=None):
    root.destroy()
    sys.exit()

blankAlbum = Image.new("RGBA", (256,256), (0,0,0,0))

## initialize main window and stuff
root = tb.Window(title="FastGH3 Launcher " + appVersion, themename="darkly")
root.protocol("WM_DELETE_WINDOW", onCloseWindow)

## variables
folderPath = ""
songPaths = []
iniPaths = []
songsFound = 0
songsScanned = 0
scanErrors = 0
titles = []
artists = []
albums = []
albumPaths = []
years = []
genres = []
charters = []
songDataList = []
songDataListBackup = songDataList
lastSelectedPath = ""
launchCmd = ""
chartLaunchPath = ""
isScanning = False
cancelling = False

fgh3ExePathVar = tkinter.StringVar(root, appcfg["general"]["fastgh3_path"])

autoScanVar = tkinter.BooleanVar(root)
scanTxtVar = tkinter.StringVar(root, "Scan Songs")
folderVar = tkinter.StringVar(root, appcfg["general"]["scan_folder"])
launchCmdVar = tkinter.StringVar(root, appcfg["general"]["launch_command"])
filterBy = tkinter.StringVar(root)
filterTxt = tkinter.StringVar(root)
themeTxt = tkinter.StringVar(root)

# copypasta = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus sit amet mauris auctor condimentum vitae sit amet nisi. Aliquam aliquam vitae mauris vel condimentum. Cras maximus urna viverra, blandit nisi id, semper mi. Vestibulum sed magna ex. Quisque magna magna, laoreet eu enim at, commodo rutrum ex. Aliquam lacinia accumsan metus, non tempor sapien varius sed. Praesent fermentum lorem sed velit volutpat varius."
copypasta = ""
songTitleVar = tkinter.StringVar(root, copypasta)
artistVar = tkinter.StringVar(root, copypasta)
albumVar = tkinter.StringVar(root, "Album:  " + copypasta)
genreVar = tkinter.StringVar(root, "Genre:  " + copypasta)
yearTxtVar = tkinter.StringVar(root, "Year:  ")
charterVar = tkinter.StringVar(root, "Charter:  " + copypasta)
loadingPhraseVar = tkinter.StringVar(root, copypasta)

defaultFontFamily = tkinter.font.nametofont('TkDefaultFont').actual()["family"]

## right-click menus
rcMenuSongList = tkinter.Menu(root, tearoff=0)
rcMenuSongList.add_command(label="Open selected song in Explorer", command=openSongFolder)
rcMenuSongList.add_command(label="Load chart", command=launchSong)
rcMenuSongList.bind("<FocusOut>", rcSongList_Unfocus)

rcMenuAlbumArt = tkinter.Menu(root, tearoff=0)
rcMenuAlbumArt.add_command(label="Open album art externally", command=openImageExternally)
rcMenuAlbumArt.bind("<FocusOut>", rcSongList_Unfocus)

## Layout stuff
# row 0
scanFrame = tkinter.Frame(root)
scanBtn = tb.Button(scanFrame,textvariable=scanTxtVar,command=scanBtnClick,width=15)
scanBtn.grid(row=0,column=0,padx=5,pady=0)
scanMeter = tb.Progressbar(scanFrame, bootstyle="success", length=125, maximum=100, value=0)
scanMeter.grid(row=0,column=1)
scanFrame.grid(row=0,column=0,padx=10)

browseFrame = tkinter.Frame(root)
folderEntry = tb.Entry(browseFrame, textvariable=folderVar, width=40)
folderEntry.grid(row=0,column=0)
browseBtn = tb.Button(browseFrame, text="Browse for Songs Folder", command=browseForSongFolder)
browseBtn.grid(row=0,column=1,padx=0,pady=10)
browseFrame.grid(row=0,column=1,columnspan=2)

themeFrame = tkinter.Frame(root, padx=10, pady=10)
themeLbl = tb.Label(themeFrame, text="Theme:  ")
themeOption = tb.OptionMenu(themeFrame, themeTxt, "","Dark","Black","Light", command=updateTheme)
themeTxt.set(appcfg["general"]["app_theme"])
themeLbl.grid(row=0,column=0)
themeOption.grid(row=0,column=1)
themeFrame.grid(row=0, column=3)

# row 1
searchFrameL = tkinter.Frame(root, padx=10, pady=5)
lblFilterSongs = tkinter.Label(searchFrameL, text="Filter Songs: ")
lblFilterSongs.grid()
filterOption = tb.OptionMenu(searchFrameL, filterBy, "", "Any", "Title", "Artist", "Album", "Year", "Genre", "Charter")
filterBy.set("Any")
filterOption.grid(row=0,column=1)
searchFrameL.grid(row=1,column=0,columnspan=2)

searchFrameR = tkinter.Frame(root, padx=10, pady=5)
filterEntry = tb.Entry(searchFrameR, width=60, textvariable=filterTxt)
filterEntry.bind("<Return>", filter_songs)
searchBtn = tb.Button(searchFrameR, text=" Search ", command=filter_songs)
filterEntry.grid(row=0,column=0,columnspan=3)
searchBtn.grid(row=0,column=3)
searchFrameR.grid(row=1,column=2,columnspan=1)

settingsBtn = tb.Button(root, text="Other Settings", width=19, command=openSettingsDialog, bootstyle="secondary")

settingsBtn.grid(row=1, column=3, padx=10, pady=5)

# row 2
albumFrame = tkinter.Frame(root, width=300, height=300)
albumFrame.grid(row=2,column=0, padx=10, pady=10, columnspan=1)
# albumBgImg = ImageTk.PhotoImage(Image.new("RGBA", (300, 300), (0,0,0,67)))
# albumBgLbl = tkinter.Label(albumFrame, width=300, height=300)
# albumBgLbl.configure(image=albumBgImg)
# albumBgLbl.grid(row=0, column=0)
albumResized = blankAlbum
albumPhoto = ImageTk.PhotoImage(blankAlbum)
albumLabel = tkinter.Label(albumFrame, width=300, height=300)
albumLabel.configure(image=albumPhoto)
albumLabel.bind("<Button-3>", rcAlbumArt)
albumLabel.grid(row=0,column=0)

listFrame = tkinter.Frame(root, width=670, height=300, padx=10, pady=10)
listFrame.grid(row=2,column=2, padx=0, pady=0, columnspan=2)
cols = ("Artist", "Title", "Album", "Year", "Genre", "Charter", "Chart Path", "Album Path", "Loading Phrase")
colwidths = (100,250,150,50,80,120,0,0,0)
scrollV = tb.Scrollbar(listFrame, orient="vertical", style="Vertical.TScrollbar")
scrollV.pack(side="right", fill="y")
songListBox = ttk.Treeview(listFrame, columns=cols, show="headings", selectmode="browse", yscrollcommand=scrollV.set, height=10, style="Treeview")
scrollV.config(command=songListBox.yview)
# songListBox.bind("<Prior>", pageUp)
# songListBox.bind("<Next>", pageDown)
songListBox.bind("<Left>", pageUp)
songListBox.bind("<Right>", pageDown)
songListBox.pack()
songListBox.bind("<<TreeviewSelect>>", loadMetadata)
songListBox.bind("<Button-3>", rcSongList)
i = 0
for col in cols:
    songListBox.heading(col, text=col, command=lambda _col=col: \
        treeview_sort_column(songListBox, _col, True))
    songListBox.column(i, minwidth=colwidths[i], width=colwidths[i])
    i+=1

# row 3
textFont = tkinter.font.nametofont("TkDefaultFont")
infoFrameL = tkinter.Frame(root, width=300, height=200)
artistFrame = tkinter.Canvas(infoFrameL, width=300, height=60)
artistLbl = tkinter.Label(artistFrame, textvariable=artistVar, wraplength=256, justify=CENTER, height=2, anchor="n", font=("Segoe UI",14))
artistLbl.pack(fill="x",expand=False)
artistLbl.pack_propagate(False)
artistFrame.grid(row=0,column=0,columnspan=2,sticky=N)
artistFrame.grid_propagate(False)
albumNameLbl = tkinter.Label(infoFrameL, textvariable=albumVar, font=("Segoe UI",10), justify=LEFT, width=40, anchor="w")
albumNameLbl.grid(row=1,column=0,columnspan=2,sticky=W,padx=5)
genreLbl = tkinter.Label(infoFrameL, textvariable=genreVar, font=("Segoe UI",10), justify=LEFT, width=28, anchor="w")
genreLbl.grid(row=2, column=0, sticky=W, padx=5)
yearLbl = tkinter.Label(infoFrameL, textvariable=yearTxtVar, font=("Segoe UI",10), justify=LEFT, width=10, anchor="e")
yearLbl.grid(row=2,column=1,sticky=E,padx=5)
charterLbl = tkinter.Label(infoFrameL, textvariable=charterVar, font=("Segoe UI",10), justify=LEFT, width=40, anchor="w")
charterLbl.grid(row=3,column=0,columnspan=2,sticky=W,padx=5)
infoFrameL.grid(row=3,column=0,sticky=N,padx=5,ipady=5)

infoFrameR = tkinter.Frame(root, height=150)
songTitleFrame = tkinter.Canvas(infoFrameR, width=400, height=35)
songTitleLbl = tkinter.Label(songTitleFrame, textvariable=songTitleVar, wraplength=720, justify=LEFT, height=1, anchor="n", font=("Segoe UI",14))
songTitleLbl.pack(fill="x",expand=False)
songTitleLbl.pack_propagate(False)
songTitleFrame.grid(row=0,column=0,columnspan=1,sticky=N)
songTitleFrame.grid_propagate(False)
loadingFrame = scrolled.ScrolledFrame(infoFrameR,width=760, height=100, autohide=True)
loadingScrTxt = FlexibleText(loadingFrame, width=125, wrap="word")
loadingScrTxt.reset_height()
loadingScrTxt.configure(state="disabled")
loadingScrTxt.pack(padx=30)
loadingFrame.grid(row=1,column=0,pady=0,ipadx=0)
infoFrameR.grid(row=3,column=2,columnspan=2,sticky=N,padx=5,ipady=5)

# bottom row?
bottomFrameL = tkinter.Frame(root)
fgh3SettingsBtn = tb.Button(bottomFrameL, text="FastGH3 Settings", width=37, command=launchFastGH3Settings, bootstyle="secondary")
fgh3SettingsBtn.grid(row=0,column=0,padx=0,pady=5)
openExplorerBtn = tb.Button(bottomFrameL, text="Open Song in File Explorer", width=37, command=openSongFolder, bootstyle="secondary")
openExplorerBtn.grid(row=1,column=0,padx=0,pady=5)
bottomFrameL.grid(row=5,column=0,padx=5,pady=5)
launchBtn = tb.Button(root, text="Play Song", width=30, command=launchSong, bootstyle="info")
launchBtn.grid(row=5,column=2,padx=10,pady=0,ipady=15,columnspan=1)
bottomFrameR = tkinter.Frame(root)
randSongBtn = tb.Button(bottomFrameR, text="Random Song", width=20, command=selectRandomSong)
randSongBtn.grid(row=0,column=0,padx=0,pady=5)
feelingLuckyBtn = tb.Button(bottomFrameR, text="I'm feeling lucky!", width=20, command=feelLucky, bootstyle="success")
feelingLuckyBtn.grid(row=1,column=0,padx=0,pady=5)
bottomFrameR.grid(row=5,column=3,padx=5,pady=5)

# Tooltips
tipTitle = ToolTip(songTitleLbl, text=copypasta, padding=4)
tipArtist = ToolTip(artistLbl, text=copypasta, padding=4)
tipAlbum = ToolTip(albumNameLbl, text=copypasta, padding=4)
tipGenre = ToolTip(genreLbl, text=copypasta, padding=4)
tipYear = ToolTip(yearLbl, text="69420", padding=4)
tipCharter = ToolTip(charterLbl, text=copypasta, padding=4)

root.geometry()
root.resizable(False,False)

# auto scan
def do_auto_scan():
    browseForSongFolder(appcfg["general"]["scan_folder"])
if appcfg["general"].getboolean("auto_scan") and len(appcfg["general"]["scan_folder"]) > 0:
    autoScanVar.set(True)
    root.after(300, do_auto_scan)
autoScanVar.set(appcfg["general"].getboolean("auto_scan"))

# refresh theme
updateTheme()

# main loop
# root.after(100, startGamepadPolling)
root.mainloop()
