# AtelIer の拡張としてつなぐ決まり

VirtualDesigner は、ペイントソフト AtelIer（Maguro-JP/AtelIer）の拡張として載る。VirtualDesigner が何をする道具かは、まだ決まっていない。
ここに書くのは、つなぎ方の決まりだけ。中身が決まるまで、拡張のコード・メニューの項目・画面は作らない
（押しても何も起きない入口を利用者に出さないため）。

## 3 つの入口（AtelIer の拡張・単体のアプリ・ほかの AI サービスから使う口）

VirtualDesigner は AtelIer のために設計するが、単体のアプリとしても動き、ほかの AI サービスからも使えるように設計する。
使われ方ごとに中身を作り分けると同じ処理が何か所にも分かれて直し漏れが出るので、中身は 1 つにして入口だけを分ける。

| 層 | 中身 |
|---|---|
| 中身の処理 | UI に頼らない部品（Python の関数・クラス）。窓・メニュー・AtelIer を読み込まない |
| 入口 1: AtelIer の拡張 | `extension.json` とメニュー（下の「extension.json の形」と「置き場」） |
| 入口 2: 単体のアプリ | 自分のウィンドウと Setup.exe。AtelIer が無くても起動する |
| 入口 3: ほかの AI サービスから使う口 | MCP のサーバーと、コマンドで呼べる口。中身の処理をそのまま呼ぶ |

- 置き場と設定は、どの入口から使っても同じにする。入口ごとに置き場を持つと、同じ人の設定や作った物が入口ごとに分かれるため
- 言葉の模型は共通の置き場 `C:\LLM` に置く
- AtelIer が無くても動き、AtelIer があれば拡張として載る。中身の処理（`virtual_designer` の下の UI に頼らない部品）は AtelIer を読み込まない
- 中身が決まるまで、どの入口も作らない（押しても何も起きない入口を出さないため）
- 次は私の推測: ほかの AI サービスから使う口は MCP のサーバー（標準入出力で話す形）にし、コマンドの口は `python -m virtual_designer <操作>` で JSON を返す形にして、2 つが同じ操作の一覧を使う。単体のアプリの Setup.exe は自分の Python を持ち、AtelIer の拡張として入れるときだけ AtelIer の Python で動かす（下の「インストーラーの連携」は拡張として入れるときの決まり）

## AtelIer の側の一覧

AtelIer は一緒に開発するデザイナーを `atelier/extension_catalog.py` に並べている。VirtualDesigner の行は次の通り。

| 欄 | 値 |
|---|---|
| name | `VirtualDesigner` |
| repo | `Maguro-JP/VirtualDesigner` |
| dropin（拡張の置き場の名前） | `virtual_designer` |
| installer | `False`（Release に Setup.exe が出たら AtelIer の側で True にする） |

## extension.json の形

```json
{"module": "virtual_designer.extension", "attr": "EXTENSION", "path": "."}
```

- `module`: import する名前。`attr` はその中の、`name`（文字）と `attach(window)` を持つ物か、引数なしで作れるクラス（既定は `EXTENSION`）
- `path`: sys.path に足す所。`<置き場>\virtual_designer\` からの道（既定は `.`）。AtelIer はここを sys.path の後ろに足すので、AtelIer と同じ名前のモジュールは AtelIer の物が先に読まれる。拡張の中は `virtual_designer` の下の名前で読む
- ほかの鍵（`version` など）は AtelIer は読まない。置いておいてよい
- 読めない拡張は、AtelIer が stderr に理由を出して飛ばす。本体とほかの拡張は止まらない
- 拡張は AtelIer の窓の公開している口（メニューバー、`file_menu` と `file_extension_anchor`、`studio_hooks`、`add_mode` など。AtelIer の `docs/STRUCTURE.md` の「拡張が使う窓の口」）にだけ足す。依存の向きは「拡張 → AtelIer」だけにする

## 置き場

```
C:\ProgramData\AtelIer\extensions\virtual_designer\extension.json
C:\ProgramData\AtelIer\extensions\virtual_designer\virtual_designer\__init__.py ...
```

- AtelIer は起動のときに、置き場の下の `extension.json` のあるフォルダーだけを読む（`atelier/extensions.py` の `load_dropins`）。置き場に無ければ、AtelIer には何も出ない
- AtelIer の Python は AtelIer の Setup.exe の中にあり、pip で入れられない。拡張の依存（AtelIer の Python に無い物）は `virtual_designer\` の中に一緒に置く
- 開発中は entry points の `atelier.extensions` の組でも読める（`pip install -e .` で AtelIer と同じ Python に入れたとき）

## インストーラーの連携

- AtelIer が入っているかは `HKLM\Software\AtelIer` の `InstallDir` で見る。あれば `%ProgramData%\AtelIer\extensions\virtual_designer\` に拡張を置き、無ければ AtelIer の置き場には何もしない
- アンインストールでは、自分の置いた `virtual_designer\` だけを消す。`extensions` を丸ごと消さない
- AtelIer の Setup.exe の選べる部品「VirtualDesigner も入れる（ネットから取る）」は、このリポジトリの最新の Release から名前に `Setup` を含む `.exe` を取り、`/S` で静かに入れる。だから Setup.exe は `/S` で窓を出さずに入り、終わりの番号 0 で成功を返す形にする。Release が無い間は、AtelIer の側で選べる部品に出さない
- Python 本体と PySide6 などは入れない（AtelIer の Python で動く）

## AtelIer の版との合わせ方

- 拡張は AtelIer の窓の口だけに頼る。口の名前と形は AtelIer の `docs/STRUCTURE.md` に書いてあり、変わるときはそこが直る
- AtelIer の版は `HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\AtelIer` の `DisplayVersion` で読める。要る口の無い古い版なら、インストーラーで知らせる
- 口が無いときに AtelIer を落とさないよう、`attach` の中で `getattr` で確かめてから足す（AtelIer は `attach` の失敗を stderr に出して窓を開く）

## 参照する形

Maguro-JP/CharacterDesigner のブランチ `claude/FIX-atelier-extension-20261121` の `packaging/character_designer/`
（`build.sh`、`bundle_list.py`、`installer.nsi`）が、置き場に拡張を入れる Setup.exe の組み方の見本。
Maguro-JP/FashionDesigner の `packaging/fashion_designer/` も同じ形。
AtelIer の側の詳しい決まりは、AtelIer の `docs/knowledge/integration.md` の「インストーラーどうしの連携」。
