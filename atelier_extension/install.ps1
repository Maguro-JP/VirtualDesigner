# VirtualDesigner の AtelIer 拡張を、拡張の置き場へ入れる
# 置き場: C:\ProgramData\AtelIer\extensions\VirtualDesigner\（本体の load_dropins が読む）
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dst = Join-Path $env:ProgramData "AtelIer\extensions\VirtualDesigner"
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item (Join-Path $PSScriptRoot "*") $dst -Recurse -Force
Copy-Item (Join-Path $root "vd_common.py") $dst -Force
Copy-Item (Join-Path $root "avatar_core.py") $dst -Force
Copy-Item (Join-Path $root "item_core.py") $dst -Force
Copy-Item (Join-Path $root "space_core.py") $dst -Force
Write-Host "VirtualDesigner 拡張を $dst に入れました。AtelIer を起動すると「バーチャルデザイン」のメニューが出ます。"
