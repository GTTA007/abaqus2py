# Abaqus 2021 服务器/本地后处理分工

## 目录结构
- `server/export_abaqus_data.py`：在服务器上运行，读取 `job.odb` 并导出 CSV。
- `local/plot_results.py`：在本地运行，读取 CSV 并绘图。

## 1) 服务器端（Abaqus 环境）
进入 `server/` 后执行：

```bash
abaqus python export_abaqus_data.py -- \
  --odb /path/to/job.odb \
  --step Step-1 \
  --node-set NSET_LOAD \
  --disp-u U2 \
  --reaction-rf RF2 \
  --frame -1 \
  --out-dir /path/to/export
```

说明：
- `--node-set`：用于统计该节点集上的位移均值和反力总和。
- `--disp-u`：位移分量，常见 `U1/U2/U3`。
- `--reaction-rf`：反力分量，常见 `RF1/RF2/RF3`。
- `--frame -1`：最后一帧应力云图；也可写成 `0,1,2...`。

导出文件：
- `load_displacement.csv`
- `stress_cloud.csv`

## 2) 传回本地
建议：

```bash
scp user@server:/path/to/export/*.csv ./data/
```

## 3) 本地绘图
先安装依赖：

```bash
pip install pandas matplotlib
```

执行：

```bash
python local/plot_results.py --input-dir ./data --out-dir ./figures --plane xy
```

输出：
- `figures/load_displacement.png`
- `figures/stress_cloud_xy.png`

## 推荐分工
- 服务器只做 `odb -> csv`，避免在服务器安装复杂绘图库。
- 本地只做 `csv -> 图`，便于反复调样式和对比工况。

## 4) 一个 `.cae` 多个 job 的批量流程（Windows 服务器）
新增脚本：
- `server/write_all_inp.py`：把 `.cae` 里的所有 job 批量导出成 `.inp`
- `server/run_all.bat`：按 `.inp` 串行运行（前一个完成后再跑下一个）

### 4.1 批量导出 `.inp`
在 Abaqus Command 中执行：

```bat
abaqus cae noGUI=write_all_inp.py -- --cae D:\abaqus_runs\project.cae --out-dir D:\abaqus_runs\inp
```

执行后，`D:\abaqus_runs\inp` 下会生成：
- `Job-1.inp`
- `Job-2.inp`
- ...

### 4.2 串行后台跑所有 `.inp`
把 `run_all.bat` 放到 `D:\abaqus_runs\inp`，然后：

```bat
cd /d D:\abaqus_runs\inp
set ABAQUS_CPUS=8
run_all.bat
```

说明：
- `run_all.bat` 会遍历当前目录所有 `*.inp` 并串行执行。
- 任一 job 失败时，脚本会停止并返回错误码。
