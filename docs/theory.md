# UXsim 理論メモ — Newell追従モデル・Incremental Node Model・基本図

このドキュメントは、UXsim (https://github.com/toruseo/UXsim) が内部で使っている
交通流理論を、実際のソースコード (`uxsim/uxsim.py`) との対応関係が分かる形でまとめたものです。
`notebooks/` の実験と合わせて読むことで、「シミュレーション結果として画面に出てくる渋滞が、
どういう数式・仮定から生まれているのか」を追えるようにすることを目的としています。

参考文献（UXsim公式READMEの Acknowledgments より）:
- Newell (2002) "A simplified car-following theory: a lower order model"
- Yperman (2011) "The Link Transmission Model for Dynamic Network Loading" 系譜の Incremental Node Model (Tampère et al., 2011)
- Dynamic User Optimum型の経路選択モデル (Han and Heydecker, 2000ほか)

---

## 1. 基本図（Fundamental Diagram）— すべての土台

交通流理論では、ある地点・区間における
- 密度 k [veh/m]（単位長さあたりの車両台数）
- 流率 q [veh/s]（単位時間あたりの通過台数）
- 速度 v [m/s]（v = q/k）

の関係を表す q-k 曲線を **基本図（Fundamental Diagram, FD）** と呼びます。
UXsimは最も単純で扱いやすい **三角形基本図（triangular FD）** を採用しています。

直感的なイメージ:
- 車がまばら（低密度）なときは、みんな自由流速度 `u` [m/s] で走れる → `q = u・k` の右上がり直線
- 車が増えて密度が上がると、ある密度（臨界密度 `k_star`）を境に、逆に流率が下がり始める
  （渋滞になるとみんなブレーキを踏むので、単位時間の通過台数はむしろ減る）
- 渋滞側では、密度が上がるほど流率が下がる右下がり直線。この直線の傾きの絶対値を
  **渋滞波速度（backward wave speed）`w`** と呼ぶ。渋滞の"しっぽ"はこの速度で上流に伝播する。

```
  q (流率)
  ^
  |        /\
  |       /  \
  |      /    \        傾き -w （渋滞側、右下がり）
  | 傾き u     \
  |    /        \
  |   /          \
  +--+------------+---> k (密度)
  0        k_star      kappa (ジャム密度)
```

三角形基本図は3つのパラメータだけで決まります:
- `u` = 自由流速度 (free_flow_speed)
- `kappa` = ジャム密度 (jam_density)：これ以上車が詰められない密度（渋滞で完全停止時の密度）
- `w` = 渋滞波速度：`w = 1 / (tau * kappa)`

これらから、
- 容量（最大流率）: `capacity = u*w*kappa / (u+w)`
- 臨界密度: `k_star = capacity / u`

が一意に決まります。

### コードとの対応

`uxsim/uxsim.py` の `Link.__init__` (`class Link`) で、`addLink()` に渡した
`free_flow_speed`, `jam_density`, `number_of_lanes` から、上記のFDパラメータが
そのまま計算されています（該当箇所を抜粋・要約）:

```python
s.u = free_flow_speed
s.kappa = jam_density
s.tau = s.W.REACTION_TIME / s.number_of_lanes   # 車線あたりの反応時間
s.w = 1 / s.tau / s.kappa                        # 渋滞波速度
s.capacity = s.u * s.w * s.kappa / (s.u + s.w)   # 容量（三角形FDの頂点のq値）
s.delta = 1 / s.kappa                            # 1台あたりのジャム時車頭間隔 [m/veh]
s.k_star = s.capacity / s.u                      # 臨界密度
```

つまり `W.addLink(..., free_flow_speed=20, jam_density=0.2, number_of_lanes=1)` と
書いた瞬間に、そのリンクの三角形基本図（＝渋滞のしやすさ、容量、渋滞伝播速度）が
すべて決定されています。`reaction_time`（World生成時のデフォルト1秒）は
車線あたりの反応時間 `tau` を通じて `w` に効いてくるので、
「反応時間が長い（不注意な運転）ほど渋滞波が速く伝わる＝渋滞が悪化しやすい」
という直感とも整合しています。

`notebooks/` では `link_traffic_state_to_pandas()` の結果からリンク内の
`k`（密度）・`q`（流率）・`v`（速度）を取り出し、実際にこの三角形の形が
再現されているかを可視化して確認します。

---

## 2. Newellの簡略化追従モデル（Newell's simplified car-following model）

### 直感

前の車にどこまで近づけるかを考えます。Newellモデルの発想はとてもシンプルです：

> 「自分は、"少し前の時刻に前の車がいた位置"から一定の車間距離を保った位置までしか進めない」

これを数式で書くと、時刻 `t` の自分の位置を `x(t)`、前の車の位置を `x_leader(t)` として、

```
x(t + τ) = min( x(t) + u・τ ,  x_leader(t) - δ )
```

- 第1項 `x(t) + u・τ`：誰もいなければ自由流速度 `u` でそのまま進む
- 第2項 `x_leader(t) - δ`：前の車から車間距離 `δ`（ジャム時車頭間隔）以上は詰められない

この2つのうち小さい方（＝より手前の位置）が実際の次の位置になります。
これは見た目以上に強力なモデルで、実は先述の三角形基本図と数学的に等価であることが
知られています（`δ = 1/kappa` かつ `w = δ/τ` の関係で結びついている）。
つまり「車間距離を守って走る」という追従行動のミクロなルールと、
「渋滞が波として上流に伝わる」というマクロな現象は、Newellモデルの中では
同じ1つの式の裏表になっています。

### コードとの対応

`uxsim/uxsim.py` の `Vehicle.carfollow()` がまさにこの式そのものです:

```python
def carfollow(s):
    s.x_next = s.x + s.link.u * s.W.DELTAT          # 自由流で進んだ場合の位置
    if s.leader != None:
        x_cong = s.leader.x - s.link.delta_per_lane * s.W.DELTAN  # 車間制約による上限位置
        if x_cong < s.x:
            x_cong = s.x
        if s.x_next > x_cong:
            s.x_next = x_cong                        # 車間制約が効く場合はこちらを採用
```

- `s.link.u` … そのリンクの自由流速度（上の理論の `u`）
- `s.link.delta_per_lane` … ジャム時車頭間隔（上の理論の `δ`。プラトゥーンサイズ`DELTAN`台分をまとめて計算）
- `s.leader` … 1台前の車（プラトゥーン）への参照

UXsimは計算を軽くするため、車両を`deltan`台ずつまとめた「プラトゥーン」単位で
シミュレーションします（`World(deltan=5, ...)` の `5`）。これにより1台1台を
律儀に解く必要がなくなり、大規模ネットワークでも高速に計算できます
（これがREADMEにある「6万台を30秒でシミュレーション」を実現する仕組みの一つです）。

### なぜこのモデルで渋滞が「自然に」発生するのか

Newellモデルには信号や合流のような明示的な「ブレーキ命令」は含まれていません。
それでも、下流の容量が不足すると、前の車がなかなか進めない
→ `x_cong` が伸びない → 自分も詰まる、という連鎖が car-following の式だけで
自動的に発生し、それが `w` の速度で上流に伝播していきます。
`notebooks/` のオンランプ合流実験では、この「上流への渋滞伝播」を
時空間図（x-t図）で目視できるようにしています。

---

## 3. Incremental Node Model（合流・分岐のモデル）

### 直感

Newellモデルは1本のリンクの中での追従挙動を決めますが、
ノード（交差点・合流点・分岐点）では「複数のリンクから来た車を、
下流リンクの限られた容量にどう配分するか」という別の問題が発生します。
これを解くのが Incremental Node Model (INM, Tampère et al., 2011) です。

UXsimでの合流のイメージ（オンランプ合流や車線減少など）:

1. 各流入リンクは、自分の送り出し容量 `capacity_out` の範囲でしか車を送れない
2. 下流リンクは、自分の受け入れ容量 `capacity_in` の範囲でしか車を受け取れない
3. 双方の制約を満たす範囲で、複数の流入リンクが競合する場合は
   `merge_priority`（合流優先率）に比例した確率・比率で配分する

たとえば本線の `merge_priority=1.0`、オンランプの `merge_priority=0.3` なら、
下流に余裕がある限りは両方とも問題なく流せますが、
下流容量が不足し始めると、本線:オンランプ ≈ 1.0 : 0.3 の比率で
順番に車が送り込まれるようになります（＝本線優先の実務的な合流ルールに対応）。

### コードとの対応

`uxsim/uxsim.py` の `Node.transfer()` が該当箇所です。要点を抜粋すると:

```python
# 受け入れ側（下流リンク）に空きがあり、かつ流入容量にも余裕がある場合のみ候補
if (... outlink.capacity_in_remain >= s.W.DELTAN and s.flow_capacity_remain >= s.W.DELTAN):
    vehs = [veh for veh in s.incoming_vehicles
            if veh.route_next_link == outlink
            and veh.link.capacity_out_remain >= s.W.DELTAN]   # 送り出し側にも余裕が必要
    ...
    merge_priorities = np.array([veh.link.merge_priority for veh in vehs])
    veh = s.W.rng.choice(vehs, p=merge_priorities/sum(merge_priorities))  # 優先率に応じて選択
```

つまり、
- `capacity_out_remain`（送り出し容量の残り）
- `capacity_in_remain`（受け入れ容量の残り）
- `merge_priority`（優先率）

の3つが揃って初めて、どの車がどのタイミングでノードを通過できるかが決まります。
これは信号交差点でもロータリーでも単純な合流でも同じロジックで扱われており、
`Node.signal_control()` が信号による通行可否の制約を追加で加えるだけ、
という構造になっています（＝ノードモデルは「容量制約＋優先度」という
1つの枠組みに統一されている）。

`notebooks/` のオンランプ合流実験では、`merge_priority` を変えることで
本線とランプの取り合いのバランスがどう変わるか、下流容量がボトルネックに
なったときにどちらが先に渋滞し始めるかを確認します。

---

## 4. 動的利用者均衡（Dynamic User Optimum, DUO）

### 直感

Newellモデル＋INMは「与えられた経路をどう車が流れるか」を決める仕組みですが、
現実のドライバーは渋滞していれば別の経路を選びます。UXsimはこれを、
各車が過去の旅行時間の実績を見ながら経路選択を更新していく
**逐次的な動的利用者均衡（Dynamic User Optimum, DUO）** の近似解法で表現しています。

考え方はゲーム理論の「均衡」に近く、
- 全員が「今分かっている情報で一番早そうな経路」を選び続けると
- やがて「どの経路を選んでも所要時間がほぼ同じになる」状態（＝均衡）に収束する

というものです。UXsimではこれを厳密に解くのではなく、
シミュレーションを繰り返しながら経路選択確率を更新する近似的な方法
（`RouteChoice` クラス、`route_pref_update()`）で実現しています。

本プロジェクトの最初の教材（Y字ネットワーク・オンランプ）では単一経路のみを
扱うためDUOの効果は前面に出ませんが、`W.duo_update_time` や
`route_choice_principle` 等のパラメータを変えると、複数経路がある
ネットワークで経路選択がどう収束するかを確認できます（発展課題）。

---

## 5. 信号制御（`notebooks/02_signal_control.ipynb` 対応）

信号は、上記のIncremental Node Model（容量制約＋優先度で「誰が通れるか」を決める仕組み）
とは独立した、もう1枚の制約レイヤーとして実装されています。

`W.addNode(..., signal=[g1, g2, ...])` の `signal` は各フェーズの青時間 [s] のリストで、
合計がサイクル長になります。`W.addLink(..., signal_group=k)` で、そのリンクがどのフェーズ
（`k`）で青になるかを指定します。あるタイムステップでノードの `signal_phase` が `k` のとき、
`signal_group` に `k` を含むリンクだけが `Node.transfer()`（INM）の対象候補になり、
それ以外のリンクは（容量に余裕があっても）通行不可として扱われます。

直感的には「INMが"誰が優先的に通れるか"を決め、信号が"そもそも今このリンクは通行可能か"
という前段のフィルタをかける」という2層構造です。これにより、信号交差点も無信号の合流も
ロータリーも、同じ `Node.transfer()` のロジックで統一的に扱えます。

飽和交通流率の考え方は、三角形基本図の `capacity` に青時間比率を掛けたものとして
近似できます:

```
実効容量 ≈ capacity × (green_time / cycle_length)
```

複数の信号が連続する区間では、`signal_offset`（信号の位相のずれ）を上流からの走行時間に
合わせて設定することで、車列が止まらずに通過できる「系統制御（グリーンウェーブ）」を
再現できます。

---

## 6. マクロ基本図 MFD（`notebooks/04_grid_network_and_mfd.ipynb` 対応）

第1節の三角形基本図（FD）は「1本のリンク」の密度・流率・速度の関係でした。
これをネットワーク全体（グリッドやエリア）に拡張し、エリア内の平均密度と平均流率を
プロットしたものが **マクロ基本図（Macroscopic Fundamental Diagram, MFD）** です。

`Analyzer.compute_mfd()` は、対象リンク群について
- `tn` (total travel distance、走行台数×距離の積算)
- `dn` (total travel time、走行台数×時間の積算)
- `an` (エリア×時間の積、正規化のための分母)

から `K_AREA`（平均密度）・`Q_AREA`（平均流率）を計算し、
`Analyzer.macroscopic_fundamental_diagram()` でプロットします。

個々のリンクのFDは三角形（直線2本）ですが、ネットワーク全体のMFDは、リンクごとの
渋滞の起き方・伝播のタイミングがずれるため、なめらかな山型の曲線になり、
過密になるほど「ネットワーク全体の処理能力そのものが落ちる」現象（グリッドロックに近い
状態）が現れます。都市の交通管制（エリア流入制御など）は、この曲線の高密度側の
崩壊を避けるための施策と位置づけられます。

---

## 7. 動的システム最適 DSO と Price of Anarchy（`notebooks/05_due_vs_dso.ipynb` 対応）

第4節のDUO/DUEは「各車両が自分の旅行時間を最小化する」自己中心的な均衡でした。
これに対し **動的システム最適（Dynamic System Optimum, DSO）** は、各車両が
「自分の旅行時間 + 自分が他の車に与える外部性（混雑コスト）」を最小化するように
経路を選ぶと仮定した、社会的に最も効率的な配分です。

`uxsim.DTAsolvers.SolverDUE` / `SolverDSO_D2D` は、いずれも
「経路選択を1日ずつ更新し、定常状態に収束させる（day-to-day dynamics）」という
同じアルゴリズムの骨格を使い、評価するコスト関数（私的費用のみ か、外部性込みか）
だけを変えたものです（詳細はモジュールのdocstringにある参考文献を参照）。

両者の総旅行時間（Total Travel Time, TTT）の比を

```
Price of Anarchy (PoA) = TTT_DUE / TTT_DSO
```

とすると、PoAは「みんなが自分本位に経路選択することで、社会的最適からどれだけ
非効率になるか」を表す指標になります。`merge_priority`（合流優先度）、信号のオフセット、
`congestion_pricing`（課金）は、いずれも現実の交通システムがDUEをDSOに近づけようとする
政策手段として理解できます。

---

## 8. まとめ：交通工学の理論とUXsimコードの対応関係

| 理論 | 何を決めるか | 対応するコード |
|---|---|---|
| 基本図（三角形FD） | 1つのリンクの「密度→流率→速度」の関係、容量、渋滞波速度 | `Link.__init__` の `u, kappa, w, capacity, delta` |
| Newell追従モデル | リンク内で車がどう進むか（ミクロな挙動）。基本図と数学的に等価 | `Vehicle.carfollow()` |
| Incremental Node Model | ノードで複数リンクの車をどう配分するか（合流・分岐） | `Node.transfer()` |
| 信号制御 | INMの上に「今このリンクは通行可能か」の制約を追加 | `Node.signal_phase`, `Link.signal_group` |
| 動的利用者均衡（DUO/DUE） | 複数経路がある場合に、車がどう経路を学習・選択するか | `RouteChoice`, `DTAsolvers.SolverDUE` |
| マクロ基本図（MFD） | ネットワーク全体の平均密度と平均流率の関係 | `Analyzer.compute_mfd()` |
| 動的システム最適（DSO） | 外部性まで考慮した、社会的に最適な経路配分 | `DTAsolvers.SolverDSO_D2D` |

基本図とNewellモデルが「リンクの中の渋滞」を、INMと信号制御が「ノードでの取り合いと
通行可否」を、DUO/DUEとDSOが「経路選択とその社会的効率性」を担当しており、
この構造がUXsimの `W.exec_simulation()` 1ステップの中で繰り返し実行されることで、
ネットワーク全体の交通流が再現されています。MFDは、これらミクロな挙動の積み重ねが
ネットワークスケールでどう見えるかを要約したものです。

対応する演習ノートブック: 信号制御→`notebooks/02_signal_control.ipynb`、
DUO→`notebooks/03_multipath_duo.ipynb`、MFD→`notebooks/04_grid_network_and_mfd.ipynb`、
DUE/DSO→`notebooks/05_due_vs_dso.ipynb`。

---

## 参考：実データとの比較に向けて

将来ETC2.0プローブデータ（速度・旅行時間の時系列）と比較する際は、
- 実データの「区間平均速度・旅行時間」は、UXsim側では
  `Link.average_speed(t)` / `link_traffic_state_to_pandas()` の `v` 列
  （Edieの一般化定義に基づく空間平均速度）に対応します。
- 実データの「地点通過台数（q）」は `link_traffic_state_to_pandas()` の `q` 列、
  もしくは `link_cumulative_to_pandas()` の累積台数の差分に対応します。

比較の際は、実データがどの区間・どの時間解像度で集計されたものかを確認し、
UXsim側も `link_traffic_state_to_pandas()` の `delta_t` / `delta_x`
（Edie状態量集計の時空間解像度、`W.EULAR_DT` 等で調整可能）を揃えることが
重要です。この対応関係は `scripts/data_loader.py` と合わせて拡張していきます。
