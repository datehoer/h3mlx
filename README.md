# H3 MLX

`h3mlx` 是面向 AI Agent 和本地用户的 MiniMax H3 Apple Silicon 运行项目。它复用
外部纯 MLX `mlx-h3` 推理引擎，提供固定配置、环境诊断、可审计生成记录和音视频验收。

项目源自一次已经完成的真实运行：Apple M1 Max 32 GB 使用 2-bit 文本编码器、
4-bit DiT 和 Turbo LoRA，生成 `640x352 / 243 帧 / 6 步` 的 10.125 秒原生音频视频，
总耗时 33.4 分钟。完整记录在
[`cases/2026-08-26-spiderman-nyc`](cases/2026-08-26-spiderman-nyc/README.md)。

## 它与 h3lite 的关系

本项目参考 h3lite 的 Agent-first 工作方式：先诊断、再规划、记录每次运行、最后验收。
两者后端不同：

| 项目 | 已验证平台 | 推理后端 |
| --- | --- | --- |
| h3lite | Windows + NVIDIA | ComfyUI / CUDA |
| h3mlx | macOS + Apple Silicon | `mlx-h3` / MLX / Metal |

本项目没有混用 ComfyUI 模型、节点或工作流，也不同于 `mmh3turbo`。

## 外部 MLX 运行时

本项目不复制推理引擎源码。当前操作配置使用
[`datehoer/mlx-h3`](https://github.com/datehoer/mlx-h3) fork 的默认
`h3mlx-local-profile` 分支；它在上游 `appautomaton/mlx-h3` 基础上保留了本机
2-bit/4-bit 权重所需的 compact-quantization 元数据兼容，以及经过实机验证的
进程/系统 swap 关联保护：

```sh
git clone https://github.com/datehoer/mlx-h3.git
```

当前 profile 头提交为 `d5d1791`。模型权重仍需单独存放，并通过
`h3mlx.local.toml` 引用；不要放入任一 Git 仓库。

## 当前机器一分钟开始

本机已经生成了被 Git 忽略的 `h3mlx.local.toml`，不需要再次填写路径：

```sh
git clone https://github.com/datehoer/h3mlx.git
cd h3mlx
cp h3mlx.example.toml h3mlx.local.toml
# Edit h3mlx.local.toml with local runtime, model, output, and run paths.
./bin/h3mlx doctor
./bin/h3mlx show-config
```

先做不启动模型的命令预览：

```sh
./bin/h3mlx generate \
  --prompt "A red ball rolls across a concrete floor with natural rolling sound." \
  --preset smoke \
  --name red-ball \
  --dry-run
```

实际生成 5.167 秒预览：

```sh
./bin/h3mlx generate \
  --prompt-file /absolute/path/to/prompt.txt \
  --preset preview \
  --name my-preview
```

生成已经验证过的 10.125 秒规格：

```sh
./bin/h3mlx generate \
  --prompt-file /absolute/path/to/prompt.txt \
  --preset final10 \
  --name my-final
```

不需要运行 `source .venv/bin/activate`。封装器会直接调用配置中外部运行时的
`.venv/bin/mlx-h3`。

## 每次运行会留下什么

生成产物写到配置的 `output_dir`。审计资料写到独立的 `run_dir/<run-id>/`：

```text
run-id/
├── prompt.txt
├── run.log
├── manifest.json
└── verification.json
```

`manifest.json` 保存有效参数、模型路径、起止时间、返回码和输出位置；
`verification.json` 检查 H.264 视频、24 FPS、AAC、32 kHz 双声道、尺寸、时长和
SHA-256。现有输出不会被覆盖。

查看最近运行或验收已有视频：

```sh
./bin/h3mlx status
./bin/h3mlx verify /absolute/path/to/result.mp4 \
  --width 640 --height 352 --frames 243
```

## 配置档

| 档位 | 画布 | 帧数 | 时长 | 步数 | 用途 |
| --- | ---: | ---: | ---: | ---: | --- |
| `smoke` | 512x288 | 22 | 0.917 秒 | 4 | 检查全链路 |
| `preview` | 640x352 | 124 | 5.167 秒 | 4 | 默认内容预览 |
| `final10` | 640x352 | 243 | 10.125 秒 | 6 | 已验证长视频 |

`final10` 在当前 M1 Max 上观察到 DiT 约 30.4 分钟、Video VAE 136 秒、Audio VAE
3.5 秒，总计 33.4 分钟。实际耗时会随序列长度、系统负载、提示词 tokens 和系统版本
变化。

## 项目边界

- 权重不存入本仓库，只通过本地配置引用。
- 2-bit 文本编码器可能优先影响复杂提示词遵循度。
- 当前 Turbo LoRA 是社区 `4step EMA ckpt850`。已验证 6 步能够完成，但这不代表它
  是所有提示词的质量最优组合。
- 技术验收只能证明媒体结构健康；人物一致性、动作顺序和声音语义仍要人工观看、收听。
- 模型权重受 MiniMax H3 Community License Agreement 及相应 LoRA 许可约束，本项目
  本身不重新授予模型使用权。

更多信息见 [`references/architecture.md`](references/architecture.md)、
[`references/verified-profile.md`](references/verified-profile.md) 和
[`references/troubleshooting.md`](references/troubleshooting.md)。
