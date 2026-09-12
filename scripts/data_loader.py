"""
実データ（ETC2.0プローブデータ等）読み込みモジュール

目的
----
将来、自分が保有するETC2.0プローブデータ（速度・旅行時間の時系列）を読み込み、
UXsimのシミュレーション結果（`W.analyzer.link_traffic_state_to_pandas()` の出力）と
比較・検証できるようにするための拡張ポイント。

現時点ではETC2.0プローブデータの具体的なファイル形式が未確定のため、
このモジュールは「どういう形に正規化すれば比較しやすいか」という
インターフェース（列構成）だけを先に決め、読み込み関数はCSVの雛形を実装している。
実際のデータ形式が分かった時点で `load_etc2_probe_csv()` の中身だけを差し替えれば、
`notebooks/` 側のコードは変更不要で動くように設計している。

正規化後の共通スキーマ（UXsim側のlink_traffic_state_to_pandas()に合わせている）
----------------------------------------------------------------------
- 'link'  : 区間名・リンク名 (str)
- 't'     : 時刻 [s] または timestamp（比較時は経過秒数に変換する）
- 'x'     : 区間内の位置 [m]（区間集計データの場合は区間代表点でよい）
- 'v'     : 速度 [m/s]（ETC2.0データが km/h の場合は変換が必要）
- 'q'     : 交通量 [veh/s]（存在する場合のみ）
- 'source': 'sim' or 'probe' （シミュレーション結果か実データかの区別用）
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# 正規化後の共通列名（UXsimのlink_traffic_state_to_pandas()の列名に合わせる）
NORMALIZED_COLUMNS = ["link", "t", "x", "v", "q", "source"]


def load_etc2_probe_csv(
    csv_path: str | Path,
    link_name: str,
    time_col: str = "timestamp",
    speed_col: str = "speed_kph",
    speed_unit: str = "kph",
    base_time: str | None = None,
) -> pd.DataFrame:
    """ETC2.0プローブデータ（速度・旅行時間の時系列CSV）を読み込み、共通スキーマに正規化する。

    Parameters
    ----------
    csv_path : CSVファイルパス
    link_name : このデータが対応するUXsim側のリンク名（比較時のキーとして使う）
    time_col : CSV内の時刻列名
    speed_col : CSV内の速度列名
    speed_unit : 'kph' (km/h) または 'mps' (m/s)。UXsim側は m/s 基準なので変換する
    base_time : 経過秒数への変換基準時刻（ISO8601文字列）。Noneの場合はCSV内の最小時刻を基準にする

    Returns
    -------
    pd.DataFrame
        列: ['link', 't', 'x', 'v', 'q', 'source']（NORMALIZED_COLUMNS）
        'x' は区間データのため暫定的に0.0を入れている。区間内の位置情報がある場合は
        別途 `x_col` 引数を追加して対応すること（今後の拡張ポイント）。

    Notes
    -----
    実際のETC2.0データのファイル形式（列名・単位・粒度）が分かり次第、
    この関数の読み込み部分（`pd.read_csv` 以降）だけを差し替えれば良い。
    呼び出し側（notebooks等）は NORMALIZED_COLUMNS のスキーマにのみ依存する。
    """
    df_raw = pd.read_csv(csv_path)

    df_raw[time_col] = pd.to_datetime(df_raw[time_col])
    origin = pd.to_datetime(base_time) if base_time is not None else df_raw[time_col].min()
    t_seconds = (df_raw[time_col] - origin).dt.total_seconds()

    speed = df_raw[speed_col].astype(float)
    if speed_unit == "kph":
        speed = speed / 3.6  # km/h -> m/s
    elif speed_unit != "mps":
        raise ValueError(f"unsupported speed_unit: {speed_unit}")

    df_norm = pd.DataFrame({
        "link": link_name,
        "t": t_seconds,
        "x": 0.0,  # 区間代表点。位置情報付きデータが手に入ったら拡張する
        "v": speed,
        "q": pd.NA,
        "source": "probe",
    })
    return df_norm[NORMALIZED_COLUMNS]


def sim_link_state_to_normalized(df_link_traffic_state: pd.DataFrame) -> pd.DataFrame:
    """UXsimの `analyzer.link_traffic_state_to_pandas()` の出力を共通スキーマに変換する。

    Parameters
    ----------
    df_link_traffic_state : W.analyzer.link_traffic_state_to_pandas() の戻り値
        列: ['link', 't', 'x', 'delta_t', 'delta_x', 'q', 'k', 'v']

    Returns
    -------
    pd.DataFrame
        列: NORMALIZED_COLUMNS （'source' は常に 'sim'）
    """
    df_norm = df_link_traffic_state[["link", "t", "x", "v", "q"]].copy()
    df_norm["source"] = "sim"
    return df_norm[NORMALIZED_COLUMNS]


def compare_sim_vs_probe(
    df_sim_normalized: pd.DataFrame,
    df_probe_normalized: pd.DataFrame,
    link_name: str,
) -> pd.DataFrame:
    """シミュレーション結果と実データ(プローブ)の速度時系列を、同一リンクについて突き合わせる。

    実装方針: シミュレーションの時間解像度（`t`）ごとに、最も近い時刻のプローブ速度を
    最近傍で対応付ける単純な実装。時間粒度が大きく異なる場合は、時間ビンでの
    平均化（resample）に変更することを推奨する（今後の拡張ポイント）。

    Returns
    -------
    pd.DataFrame
        列: ['t', 'v_sim', 'v_probe', 'diff'] （diff = v_sim - v_probe）
    """
    df_sim = df_sim_normalized[df_sim_normalized["link"] == link_name].sort_values("t")
    df_probe = df_probe_normalized[df_probe_normalized["link"] == link_name].sort_values("t")

    merged = pd.merge_asof(
        df_sim[["t", "v"]].rename(columns={"v": "v_sim"}),
        df_probe[["t", "v"]].rename(columns={"v": "v_probe"}),
        on="t",
        direction="nearest",
    )
    merged["diff"] = merged["v_sim"] - merged["v_probe"]
    return merged


if __name__ == "__main__":
    print(__doc__)
    print("このスクリプトは単体実行用ではなく、notebooks等からimportして使うモジュールです。")
