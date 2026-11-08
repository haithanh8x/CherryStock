# AWS SSO cache sync (Confluence → `~/.aws/sso/cache`)

Tải `cache.zip` từ trang Confluence **Notes** rồi ghi đè vào `C:\Users\ADMIN\.aws\sso\cache`.

## Cách hoạt động

| Bước | Việc gì | Ai làm |
|---|---|---|
| 1 | Đăng nhập Atlassian (`haithanh8x.atlassian.net`) | `acli` (Atlassian CLI) |
| 2 | Mở Chrome bằng profile thật `Default` (`haithanh8x@gmail.com`) kèm DevTools protocol | PowerShell |
| 3 | Mở trang Confluence, tải attachment `cache.zip` | Playwright (`playwright-core`) qua CDP |
| 4 | Giải nén, backup, ghi đè toàn bộ file vào `~/.aws/sso/cache` | PowerShell |

> **Lưu ý:** `acli` hiện chỉ có lệnh cho Jira/Admin/Rovo Dev, **không có lệnh Confluence**.
> Vì vậy `acli` được dùng cho bước đăng nhập, còn file đính kèm được tải bằng chính
> session Chrome đã đăng nhập (không cần API token, không cần copy cookie).

## Yêu cầu

- Windows + PowerShell 5.1 trở lên
- Node.js 18+ (`node -v`)
- Google Chrome đã đăng nhập `haithanh8x@gmail.com` ở profile `Default`
- `acli` (script tự cài qua `winget` nếu thiếu)

## Chạy

```powershell
cd C:\Github\CherryStock\scripts\ops\aws-sso-cache-sync
.\Sync-AwsSsoCache.ps1
```

Lần đầu chạy, nếu session Atlassian đã hết hạn, script sẽ mở cửa sổ Chrome và chờ bạn
đăng nhập (tối đa `-LoginTimeoutMin`, mặc định 5 phút). Các lần sau chạy hoàn toàn tự động
miễn là Chrome vẫn còn mở.

## Tham số

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `-PageUrl` | trang Notes (pageId 22413313) | Trang Confluence nguồn |
| `-Attachment` | `cache.zip` | Tên file đính kèm |
| `-TargetDir` | `C:\Users\ADMIN\.aws\sso\cache` | Thư mục đích |
| `-ChromeProfile` | `Default` | Profile Chrome (haithanh8x@gmail.com) |
| `-CdpPort` | `9222` | Cổng DevTools |
| `-LoginTimeoutMin` | `5` | Thời gian chờ đăng nhập |
| `-AcliTimeoutSec` | `120` | Thời gian chờ `acli jira auth login --web` |
| `-SkipAcli` | | Bỏ qua bước đăng nhập `acli` |
| `-NoBackup` | | Không backup thư mục cache cũ |
| `-NoCloseChrome` | | Không tự đóng Chrome đang chạy |
| `-CloseChromeAfter` | | Đóng Chrome sau khi xong |
| `-KeepTemp` | | Giữ file zip và thư mục giải nén |
| `-IncludeMacMetadata` | | Giữ cả `__MACOSX`, `.DS_Store`, `._*` (mặc định bỏ qua) |

## Xử lý archive

- Nếu zip bọc mọi thứ trong một thư mục duy nhất (ví dụ `cache/`), script dùng chính thư mục
  đó làm gốc và copy **nội dung bên trong** vào `-TargetDir` (không tạo `cache\cache\`).
- Mặc định bỏ qua metadata macOS (`__MACOSX/`, `.DS_Store`, `._*`).
- File trùng tên bị ghi đè; file không có trong zip được giữ nguyên.

## Ghi chú kỹ thuật

- **acli `--web` cần mở được trình duyệt.** Khi Chrome automation (cổng 9222) đang chạy,
  Windows không mở được URL mới vì profile đang bị khóa, nên script **bỏ qua** bước acli và
  ghi cảnh báo. Bước tải file vẫn chạy bình thường bằng session Chrome.
  Muốn acli thật sự đăng nhập: đóng Chrome rồi chạy `acli jira auth login --web` trong
  terminal, hoặc dùng API token (`--site/--email/--token`).
- **Chrome 136+** từ chối `--remote-debugging-port` khi dùng user-data-dir mặc định.
  Script tạo junction `%LOCALAPPDATA%\chrome-cdp-profile` → `...\Google\Chrome\User Data`
  để Chrome coi đó là đường dẫn khác nhưng vẫn dùng đúng profile và cookie hiện có.
- Nếu Chrome đang chạy **không** bật DevTools, script sẽ đóng Chrome (graceful, sau 10s
  thì force) rồi mở lại. Dùng `-NoCloseChrome` nếu không muốn điều này.
- Script để Chrome chạy tiếp sau khi xong để lần sau tái sử dụng session; dùng
  `-CloseChromeAfter` nếu muốn đóng.
- Cổng DevTools chỉ lắng nghe trên `127.0.0.1`, nhưng bất kỳ process local nào cũng điều
  khiển được trình duyệt khi cổng này mở. Đóng Chrome khi không dùng nếu bạn cần chặt hơn.
- Backup cache cũ nằm ở `%LOCALAPPDATA%\aws-sso-cache-sync\backup-<timestamp>`.
