import socket, datetime, shutil, subprocess, os, ctypes, winreg, getpass, time, sys

WINRAR_PATH   = r"C:\Program Files\WinRAR\WinRAR.exe"
MIN_GB        = 10
TARGET_DIR    = "update"
DAYS_INACTIVE = 60

ALLOWED_USERS = {
    ""administrator"
}


SOURCE_FILE = None
exe_path = None

def get_script_directory():
    
    if getattr(sys, 'frozen', False):
        
        return os.path.dirname(sys.executable)
    else:
        
        return os.path.dirname(os.path.abspath(__file__))

def read_source_path():
    """Đọc đường dẫn file nguồn từ file source.txt."""
    global SOURCE_FILE
    script_dir = get_script_directory()
    source_txt_path = os.path.join(script_dir, "source.txt")

    try:
        with open(source_txt_path, "r", encoding="utf-8") as f:
            path = f.read().strip()
        if not path:
            print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] ❌ Lỗi: File source.txt trống.")
            return False
        SOURCE_FILE = path
        return True
    except FileNotFoundError:
        print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] ❌ Lỗi: Không tìm thấy file source.txt tại {script_dir}")
        return False
    except Exception as e:
        print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] ❌ Lỗi khi đọc file source.txt: {e}")
        return False


def log(msg):
    
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    
    if not SOURCE_FILE:
        return
        
    try:
        hostname = socket.gethostname().upper()
        
        
        try:
            ip_address = socket.gethostbyname(hostname)
        except socket.gaierror:
            ip_address = "IP-not-found"

        
        log_filename = f"{hostname}-{ip_address}.log"
        
        log_dir  = os.path.join(os.path.dirname(SOURCE_FILE), "upgrade_log")
        os.makedirs(log_dir, exist_ok=True)
        
        with open(os.path.join(log_dir, log_filename), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
>



def check_user():
    try:
        current_user = getpass.getuser().lower()
    except:
        current_user = os.getenv("USERNAME", "unknown").lower()
    if current_user not in ALLOWED_USERS:
        log("❌ User không hợp lệ – dừng lại.")
        return False
    log("✅ User hợp lệ – tiếp tục...")
    return True

# ---------------------------------------------------
def get_windows_version():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
        build, _ = winreg.QueryValueEx(key, "CurrentBuildNumber")
        winreg.CloseKey(key)
        return 11 if int(build) >= 22000 else 10
    except Exception:
        return 10

# ---------------------------------------------------
def check_and_skip_if_win11():
    if get_windows_version() >= 11:
        log("✅ Đã cài Windows 11 – bỏ qua.")
        return True
    return False

# ---------------------------------------------------
def remove_inactive_profiles():
    log(f"🔍 Kiểm tra profile > {DAYS_INACTIVE} ngày không đăng nhập...")
    users_root = r"C:\Users"
    cutoff = datetime.datetime.now() - datetime.timedelta(days=DAYS_INACTIVE)
    skip_dirs = {"All Users", "Default", "Default User", "Public", "desktop.ini"}
    removed = 0
    for item in os.listdir(users_root):
        p = os.path.join(users_root, item)
        if not os.path.isdir(p) or item.lower() in (d.lower() for d in skip_dirs):
            continue
        try:
            last = datetime.datetime.fromtimestamp(os.path.getatime(p))
            if last < cutoff:
                log(f"🗑️  Xóa profile: {item} (truy cập cuối {last:%Y-%m-%d})")
                shutil.rmtree(p, ignore_errors=True)
                removed += 1
            else:
                log(f"✅ Giữ lại profile: {item}")
        except Exception as e:
            log(f"⚠️ Không thể kiểm tra/xóa {item}: {e}")
    if removed:
        log(f"✅ Đã xóa {removed} profile không hoạt động.")

# ---------------------------------------------------
def copy_with_progress(src, dst):
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    total = os.path.getsize(src)
    copied = 0
    buf = 16 * 1024 * 1024
    log(f"📥 Copy {total/1024**3:.1f} GB từ {src}")
    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
        while True:
            chunk = fsrc.read(buf)
            if not chunk:
                break
            fdst.write(chunk)
            copied += len(chunk)
            pct = int(copied / total * 100)
            
    log("📤 Copy hoàn tất.")

# ---------------------------------------------------
def run_setup():
    global exe_path
    if not exe_path:
        log("❌ Không có đường dẫn thực thi"); return
    if not ctypes.windll.shell32.IsUserAnAdmin():
        log("❌ Cần chạy RUN AS ADMINISTRATOR"); return

    
    for d in [r"C:\$WINDOWS.~BT", r"C:\$WINDOWS.~WS", r"C:\Windows.old"]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)

    
    try:
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE,
                              r"SYSTEM\Setup\MoSetup") as key:
            winreg.SetValueEx(key, "AllowUpgradesWithUnsupportedTPMOrCPU",
                              0, winreg.REG_DWORD, 1)
        log("✅ Đã bật AllowUpgradesWithUnsupportedTPMOrCPU")
    except Exception as e:
        log(f"⚠️ Không set registry AllowUpgradesWithUnsupportedTPMOrCPU: {e}")

    setup_exe = None
    for f in os.listdir(exe_path):
        if f.lower() == "setup.exe":
            setup_exe = os.path.join(exe_path, f)
            break
    if not setup_exe:
        log("❌ Không tìm thấy setup.exe"); return

    cmd = (f'"{setup_exe}" /Auto Upgrade /PKey W269N-WFGWX-YVC9B-4J6C9-T83GX '
           '/Eula Accept /MigrateDrivers All /Compat IgnoreWarning /NoReboot '
           '/DynamicUpdate disable /ShowOOBE none /Telemetry disable')
    log("► Đang chạy setup.exe…")
    ret = subprocess.run(cmd, shell=True).returncode
    if ret == 0:
        log("✅ Thành công – máy sẽ khởi động lại sau 30 giây!")
        subprocess.run("shutdown /r /t 30 /f", shell=True)
    else:
        log(f"❌ setup.exe exit code {ret}")

# ---------------------------------------------------
def main():
    global exe_path
    
    if not read_source_path():
        time.sleep(10) 
        return

    if not check_user():
        return
    if check_and_skip_if_win11():
        return

    if not os.path.isfile(SOURCE_FILE):
        log(f"❌ Không truy cập được file nguồn: {SOURCE_FILE}"); return

    # Chọn ổ đích
    dest_drive = None
    for d in ["D", "E", "F", "G", "H"]:
        p = f"{d}:\\"
        if not os.path.exists(p):
            continue
        try:
            free = shutil.disk_usage(p).free // 1024**3
            if free >= MIN_GB:
                dest_drive = p
                log(f"✅ Chọn ổ {d} – còn {free} GB")
                break
            else:
                log(f"Đã kiểm tra ổ {d} – còn {free} GB – không đủ")
        except Exception as e:
            log(f"⚠️ Lỗi kiểm tra ổ {d}: {e}")
    if not dest_drive:
        log("❌ Không có ổ nào đủ dung lượng"); return

    target_path = os.path.join(dest_drive, TARGET_DIR)
    os.makedirs(target_path, exist_ok=True)
    dest_file   = os.path.join(target_path, os.path.basename(SOURCE_FILE))
    exe_path    = target_path

    
    try:
        c_free = shutil.disk_usage("C:\\").free // 1024**3
        if c_free < 20:
            log(f"📉 Ổ C còn {c_free} GB – dọn profile > {DAYS_INACTIVE} ngày")
            remove_inactive_profiles()
        else:
            log(f"📈 Ổ C còn {c_free} GB – bỏ qua dọn profile")
    except Exception as e:
        log(f"⚠️ Không kiểm tra được ổ C: {e}")
        remove_inactive_profiles()

    copy_with_progress(SOURCE_FILE, dest_file)

    log("📦 Giải nén...")
    subprocess.run([WINRAR_PATH, "x", "-o+", dest_file, target_path + "\\"],
                   check=True, shell=True)
    log("✅ Giải nén xong")

    run_setup()

# ---------------------------------------------------
if __name__ == "__main__":
    main()