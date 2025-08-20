#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tải file từ link Nextcloud public (không đăng nhập)
và chia sẻ thư mục lưu file cho nhóm Windows.
Yêu cầu: chạy PowerShell / CMD với quyền Administrator.
"""

import os
import sys
import time
import requests
import win32security
import win32net
import win32netcon

# ========== NGƯỜI DÙNG CHỈNH SỬA 4 DÒNG NÀY ==========
DIRECT_DOWNLOAD_URL = "https://cloud.example.com/index.php/s/AbCdEf/download?path=/&files=win11.rar"
SAVE_FOLDER         = r"C:\folder"
SHARE_NAME          = "lol"      # Tên chia sẻ xuất hiện trong \\PC-NAME\lol
GROUP_NAME          = "lol"      # Nhóm cục bộ / domain muốn cấp quyền
# =======================================================

FILE_NAME = os.path.basename(DIRECT_DOWNLOAD_URL.split("files=")[-1])
LOCAL_PATH = os.path.join(SAVE_FOLDER, FILE_NAME)

# ------------------------------------------------------------
# 1. Tải file từ link public (không cần đăng nhập)
# ------------------------------------------------------------
def download_file(url: str, dest: str) -> None:
    """Tải file qua HTTP(S) với progress bar đơn giản."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    print(f"[INFO] Bắt đầu tải: {url}")
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = downloaded / total * 100
                        print(f"\r[DOWNLOAD] {percent:6.2f} %  {downloaded >> 20} MB / {total >> 20} MB", end="")
        print("\n[INFO] Tải xong ->", dest)

# ------------------------------------------------------------
# 2. Tạo chia sẻ Windows và cấp quyền NTFS cho nhóm
# ------------------------------------------------------------
def create_or_update_share(folder: str, share: str, group: str) -> None:
    """Tạo share Windows (ghi đè nếu đã tồn tại)."""
    info = {
        "netname": share,
        "type": win32netcon.STYPE_DISKTREE,
        "remark": "Auto-share by Python",
        "permissions": 0,
        "max_uses": -1,
        "path": folder,
    }
    try:
        win32net.NetShareAdd(None, 2, info)
        print(f"[SHARE] Đã tạo share: {share}")
    except win32net.error as e:
        if e.winerror == 2118:  # NERR_ShareExists
            win32net.NetShareDel(None, share)
            win32net.NetShareAdd(None, 2, info)
            print(f"[SHARE] Đã ghi đè share: {share}")
        else:
            raise

    # Cấp quyền NTFS Full Control cho nhóm
    sd = win32security.GetFileSecurity(folder, win32security.DACL_SECURITY_INFORMATION)
    dacl = sd.GetSecurityDescriptorDacl()
    sid, _, _ = win32security.LookupAccountName(None, group)
    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, win32security.FILE_ALL_ACCESS, sid)
    sd.SetSecurityDescriptorDacl(1, dacl, 0)
    win32security.SetFileSecurity(folder, win32security.DACL_SECURITY_INFORMATION, sd)
    print(f"[PERM] Đã cấp quyền Full Control cho nhóm: {group}")

# ------------------------------------------------------------
# 3. Main
# ------------------------------------------------------------
def main() -> None:
    try:
        download_file(DIRECT_DOWNLOAD_URL, LOCAL_PATH)
        create_or_update_share(SAVE_FOLDER, SHARE_NAME, GROUP_NAME)
        print("[DONE] Tất cả hoàn tất!")
    except Exception as exc:
        print("[ERROR]", exc, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Kiểm tra quyền admin đơn giản trên Windows
    if not (os.name == "nt" and sys.getwindowsversion()):
        print("[WARN] Hệ điều hành không phải Windows hoặc không lấy được build.")
    try:
        import win32api
    except ImportError:
        print("[ERROR] Thiếu pywin32. Cài: pip install pywin32")
        sys.exit(1)

    print("[INFO] Kiểm tra quyền Administrator...")
    # Cách kiểm tra nhanh
    try:
        win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32security.TOKEN_ALL_ACCESS)
    except:
        print("[ERROR] Vui lòng chạy script với quyền Administrator (Run as Administrator).")
        sys.exit(1)

    main()
