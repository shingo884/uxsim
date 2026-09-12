"""
オンランプ合流シナリオ 実行用スクリプト

notebooks/01_uxsim_intro_and_onramp_merge.ipynb の Part B と同一のシナリオを
コマンドラインから実行するためのスクリプト。パラメータ実験（merge_priorityや
需要水準を変えて渋滞の有無を比較する等）をノートブックを開かずに素早く回したい場合に使う。

使い方:
    source venv/bin/activate
    python scripts/run_onramp_simulation.py
    python scripts/run_onramp_simulation.py --ramp-flow 0.2 --ramp-priority 0.8
"""

from __future__ import annotations

import argparse

from uxsim import World


def build_and_run(
    mainline_flow: float = 0.55,
    ramp_flow: float = 0.35,
    ramp_priority: float = 0.5,
    downstream_lanes: int = 1,
    tmax: float = 3000,
    random_seed: int = 42,
) -> World:
    """本線1本+オンランプ1箇所の合流シナリオを構築し、シミュレーションを実行して World を返す。

    Parameters
    ----------
    mainline_flow : 本線側のOD需要 [veh/s]
    ramp_flow : オンランプ側のOD需要 [veh/s]（600〜1800sの間だけ発生させる）
    ramp_priority : 合流ノードにおけるオンランプの merge_priority（本線側は1.0固定）
    downstream_lanes : 合流後（本線下流）の車線数。1にするとボトルネックになりやすい
    tmax : シミュレーション総時間 [s]
    random_seed : 乱数シード
    """
    W = World(
        name="onramp_merge",
        deltan=5,
        tmax=tmax,
        print_mode=1, save_mode=1, show_mode=0,
        random_seed=random_seed,
    )

    W.addNode("mainline_orig", 0, 0)
    W.addNode("merge_node", 5, 0)
    W.addNode("dest", 9, 0)
    W.addNode("ramp_orig", 3, -2)

    W.addLink("mainline_up", "mainline_orig", "merge_node",
              length=3000, free_flow_speed=25, number_of_lanes=2, jam_density=0.12,
              merge_priority=1.0)
    W.addLink("ramp", "ramp_orig", "merge_node",
              length=500, free_flow_speed=15, number_of_lanes=1, jam_density=0.12,
              merge_priority=ramp_priority)
    W.addLink("mainline_down", "merge_node", "dest",
              length=4000, free_flow_speed=25, number_of_lanes=downstream_lanes, jam_density=0.12)

    W.adddemand(orig="mainline_orig", dest="dest", t_start=0, t_end=2400, flow=mainline_flow)
    W.adddemand(orig="ramp_orig", dest="dest", t_start=600, t_end=1800, flow=ramp_flow)

    W.exec_simulation()
    return W


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mainline-flow", type=float, default=0.55, help="本線需要 [veh/s]")
    parser.add_argument("--ramp-flow", type=float, default=0.35, help="オンランプ需要 [veh/s]")
    parser.add_argument("--ramp-priority", type=float, default=0.5, help="オンランプのmerge_priority")
    parser.add_argument("--downstream-lanes", type=int, default=1, help="合流後の車線数")
    parser.add_argument("--tmax", type=float, default=3000, help="シミュレーション総時間 [s]")
    args = parser.parse_args()

    W = build_and_run(
        mainline_flow=args.mainline_flow,
        ramp_flow=args.ramp_flow,
        ramp_priority=args.ramp_priority,
        downstream_lanes=args.downstream_lanes,
        tmax=args.tmax,
    )

    W.analyzer.print_simple_stats()

    link_down = W.get_link("mainline_down")
    total_demand = args.mainline_flow + args.ramp_flow
    print()
    print(f"mainline_down capacity : {link_down.capacity:.3f} veh/s")
    print(f"peak total demand      : {total_demand:.3f} veh/s")
    if total_demand > link_down.capacity:
        print("=> 需要が容量を上回っています。渋滞が発生している可能性が高いです。")
    else:
        print("=> 需要は容量以下です。渋滞は発生しにくいはずです。")


if __name__ == "__main__":
    main()
