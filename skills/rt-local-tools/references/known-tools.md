# Known Tool Hints

Quick hints for common tool locations and install methods. These are **not exhaustive** — they're starting points to speed up the search. The canonical source of truth is always `config/local-tools.json` once a tool is registered.

## Debuggers

| Tool | Windows | Linux | macOS | Install |
|------|---------|-------|-------|---------|
| cdb | `C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe` | N/A | N/A | Install Windows SDK (Debugging Tools component) |
| lldb | N/A | `/usr/bin/lldb`, `/usr/local/bin/lldb` | `/usr/bin/lldb`, Xcode command line tools | `sudo pacman -S lldb` (Arch), `sudo apt install lldb` (Debian), `xcode-select --install` (macOS) |
| gdb | `C:\msys64\usr\bin\gdb.exe` | `/usr/bin/gdb` | `/usr/local/bin/gdb` | `sudo pacman -S gdb` (Arch), `sudo apt install gdb` (Debian), `brew install gdb` (macOS) |

## .NET Diagnostic Tools

| Tool | Check | Install |
|------|-------|---------|
| dotnet-dump | `dotnet tool list -g` | `dotnet tool install -g dotnet-dump` |
| dotnet-trace | `dotnet tool list -g` | `dotnet tool install -g dotnet-trace` |
| dotnet-counters | `dotnet tool list -g` | `dotnet tool install -g dotnet-counters` |
| dotnet-monitor | `dotnet tool list -g` | `dotnet tool install -g dotnet-monitor` |
| dotnet-sos | `dotnet tool list -g` | `dotnet tool install -g dotnet-sos` |
| dotnet-symbol | `dotnet tool list -g` | `dotnet tool install -g dotnet-symbol` |
| dotnet-stack | `dotnet tool list -g` | `dotnet tool install -g dotnet-stack` |

Global dotnet tools are typically at `~/.dotnet/tools/` (Linux/macOS) or `%USERPROFILE%\.dotnet\tools\` (Windows).

## Analysis Tools

| Tool | Windows | Linux | macOS | Install |
|------|---------|-------|-------|---------|
| objdump | MSYS2/MinGW | `/usr/bin/objdump` | `/usr/bin/objdump` | Part of binutils |
| readelf | MSYS2/MinGW | `/usr/bin/readelf` | N/A | Part of binutils |
| nm | MSYS2/MinGW | `/usr/bin/nm` | `/usr/bin/nm` | Part of binutils |

## Build Tools

| Tool | Check | Notes |
|------|-------|-------|
| dotnet | `dotnet --version` | Should be in PATH on any dev machine |
| msbuild | `msbuild -version` | Usually via Visual Studio on Windows; `dotnet msbuild` elsewhere |
| cmake | `cmake --version` | `sudo pacman -S cmake` (Arch), `sudo apt install cmake` (Debian) |
