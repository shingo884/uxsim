# UXsim交通流シミュレーション学習プロジェクト

[UXsim](https://github.com/toruseo/UXsim) を使って交通流シミュレーションの基礎理論
（Newellの簡略化追従モデル、Incremental Node Model、動的利用者均衡）を実践的に学ぶための
プロジェクトです。将来的には、保有するETC2.0プローブデータ（速度・旅行時間の時系列）と
シミュレーション結果を比較・検証する方向に発展させます。

## セットアップ

UXsimはPython 3.10以上が必要です。

```bash
# Python 3.10+ が必要（例: Homebrewで導入する場合）
brew install python@3.12

# 仮想環境の作成
/usr/local/opt/python@3.12/bin/python3.12 -m venv venv
source venv/bin/activate

# 依存パッケージのインストール
pip install -r requirements.txt
# もしくは
pip install -e .
```

Jupyter Notebookを開く:

```bash
source venv/bin/activate
jupyter notebook notebooks/
```

## ディレクトリ構成

```
.
├── notebooks/    学習用Jupyter notebook（教育プログラム、Day1〜Day9-10）
│   ├── 01_uxsim_intro_and_onramp_merge.ipynb
│   ├── 02_signal_control.ipynb
│   ├── 03_multipath_duo.ipynb
│   ├── 04_grid_network_and_mfd.ipynb
│   ├── 05_due_vs_dso.ipynb
│   ├── 06_taxi_dispatch.ipynb
│   ├── 07_policy_evaluation.ipynb
│   ├── 08_real_network_and_data.ipynb
│   └── 09_capstone_project.ipynb
├── scripts/      実行用スクリプト
│   ├── run_onramp_simulation.py   オンランプ合流シナリオのCLI実行版
│   └── data_loader.py             実データ(ETC2.0プローブ等)読み込み・比較用の雛形
├── data/         実データ配置用
│   ├── raw/        生データ
│   └── processed/  加工済みデータ
├── docs/         学習メモ・理論まとめ
│   └── theory.md   基本図・Newell追従モデル・INM・信号制御・MFD・DUE/DSOの理論メモ
├── requirements.txt
└── pyproject.toml
```

## 教育プログラム（集中1〜2週間、交通流理論の基礎を前提とした演習形式）

基礎理論を理解済みの前提で、UXsimでの実装・応用に集中したカリキュラムです。
各Dayは「学習目標 → 動作する最小例(Part A) → 演習(Part B, TODO形式) → 考察(Part C)」の
構成になっています。

| Day | Notebook | テーマ | 対応する理論 |
|---|---|---|---|
| 1 | `01_uxsim_intro_and_onramp_merge.ipynb` | UXsim入門・オンランプ合流 | 三角形基本図・Newell追従モデル・Incremental Node Model |
| 2 | `02_signal_control.ipynb` | 信号交差点 | 飽和交通流率・青時間配分・系統制御(オフセット) |
| 3 | `03_multipath_duo.ipynb` | 複数経路と動的利用者均衡 | 動的利用者均衡（DUO） |
| 4 | `04_grid_network_and_mfd.ipynb` | グリッドネットワークとMFD | マクロ基本図（Macroscopic Fundamental Diagram） |
| 5 | `05_due_vs_dso.ipynb` | DUE vs DSO | Price of Anarchy・動的システム最適配分 |
| 6 | `06_taxi_dispatch.ipynb` | タクシー配車アルゴリズム比較 | マッチング理論・供給と需要のバランス |
| 7 | `07_policy_evaluation.ipynb` | 施策評価（Before/After） | 料金施策（congestion pricing）・容量変更の効果評価 |
| 8 | `08_real_network_and_data.ipynb` | 実道路網の取り込み | OSMImporter、実データ比較への橋渡し |
| 9-10 | `09_capstone_project.ipynb` | キャプストーンプロジェクト | 自分で設定した政策課題の評価・レポート作成 |

進め方:

1. `docs/theory.md` で該当Dayの理論的背景を確認する
2. 対応するノートブックをPart A→B→Cの順に実行・演習する（Jupyterのカーネルは
   セットアップ時に `python -m ipykernel install --user --name uxsim-venv` で
   本プロジェクトのvenvをカーネル登録しておくと迷わない）
3. `scripts/run_onramp_simulation.py` でパラメータ（需要水準・merge_priority・車線数）を
   変えた実験をノートブックの外から素早く回す
4. 実データが手に入り次第、`scripts/data_loader.py` を拡張して `data/raw/` のCSVを読み込み、
   シミュレーション結果と比較する（Day 8 が橋渡し）

進捗はNotionでも管理しています:
- [UXsim交通流シミュレーション学習プロジェクト](https://app.notion.com/p/3d093d6c7a6b81c2a4a7ff567911ab56)（Day 1のセットアップ状況・理論メモのチェックリスト）
- [教育プログラム カリキュラム一覧](https://app.notion.com/p/3d793d6c7a6b80f99263c625fe9a8fc6)（Day 1〜9-10のロードマップ）

（いずれもプライベートページとして作成済みです。共有・移動が必要な場合はご指示ください）
