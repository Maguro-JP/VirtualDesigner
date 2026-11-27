# CHANGELOG

## v1.0.0 — 2026-11-27

- VirtualDesigner の最初のリリース。アバター・空間・道具の3つを設計できる道具として実装。
- `vd_common.py` を追加：3対象で共有する色の検証（#RRGGBB、カスタム色対応）、肌・髪・瞳のパレット、背景（単色 / グラデーション / 柄）の生成。
- `avatar_core.py` を追加：仕様 `virtualdesigner.avatar.v1` の検証・正規化と SVG 生成。顔の形 4 種類、髪型 12 種類（前髪と後ろ髪の2層）、目の形 5 種類、眉 4 種類、鼻 4 種類、口 6 種類、髭 4 種類、眼鏡 3 種類、耳飾り 3 種類、帽子 4 種類、髪飾り 3 種類、服 6 種類。プリセット 6 件、seed 付きランダム生成。
- `item_core.py` を追加：仕様 `virtualdesigner.item.v1` と、空間と共有する部品ライブラリ（18 種類・4 カテゴリ）。模様 3 種類、プリセット 7 件、seed 付きランダム生成。
- `space_core.py` を追加：仕様 `virtualdesigner.space.v1` の検証・正規化と SVG 生成。壁の柄 5 種類、床の柄 4 種類、窓・ドアの配置、照明 4 種類（夜は窓が夜空に、ランプが発光）、家具の配置（位置・奥行き・大きさ・反転・色、最大 30 個）。プリセット 4 件、seed 付きランダム生成。
- `server.py` を追加：localhost（127.0.0.1:8770）専用サーバー。対象ごとの描画（`POST /api/avatar|space|item?format=svg`）、検証（`POST /api/validate?target=`）、プリセット（`GET /api/presets`）、ランダム（`GET /api/random?target=&seed=`）。
- `index.html` を追加：日本語のシングルページ UI。3タブ（アバター / 空間 / 道具）、パーツ選択、パレット＋自由な色指定、ライブプレビュー、プリセット、ランダム、JSON 保存・読み込み、SVG / PNG（256・512・1024）保存、localStorage への設定保存。
- AtelIer の拡張を追加（`atelier_extension/`）：3タブのダイアログで各 core をそのまま使い、プレビューを見ながら SVG / PNG で保存できる。`install.ps1` で拡張一式と各 core を `C:\ProgramData\AtelIer\extensions\VirtualDesigner\` へ入れる。
- テストを追加：各 core の全選択肢の描画と差分、色の検証、プリセット、ランダム、エスケープ、サーバーのスモーク、拡張の形と本体の置き場読み込み（load_dropins）。
