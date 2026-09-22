# 看图猜成语视频 · idiom-puzzle-video

一个 Codex Skill：把四字成语制作成包含原创谜面、倒计时、提示、答案揭晓和轻音乐的竖屏短视频。

## 效果与能力

- 默认 1080×1920、24 fps、16 秒，导出 H.264/AAC MP4 和 JPG 封面。
- 前 11 秒猜题，后 5 秒揭晓；猜题与答案时长可配置。
- 暖米色背景、立体静物谜面，统一栏目风格。
- 倒计时数字与问号按实际字形边界水平、垂直居中。
- 内置 5 段不同旋律、速度和音色的原创 BGM：轻快拨弦、俏皮木琴、温柔琴键、好奇节拍、暖调律动。默认随机选曲，无口播。
- BGM 默认以 -18 LUFS 为目标统一响度，再混合较轻的倒计时提示音。配置 `bgm_lufs` 可在 -24 到 -12 之间调节。
- 默认不在画面底部叠加“AI 生成画面”字样；发布时仍需按平台规则声明 AI 生成内容。
- 提供“五谷丰登”“十全十美”“马到成功”三份示例配置。

技能由 Codex 编排审题、图片生成和渲染。Python 脚本只负责把已有谜面图片合成为视频，不会独立调用图像生成模型。

## 安装到 Codex

将本仓库克隆到 Codex 的技能目录下，文件夹名称保持为 `idiom-puzzle-video`：

```bash
git clone https://github.com/Clearleaves/idiom-puzzle-video.git ~/.codex/skills/idiom-puzzle-video
```

如果设置了 `CODEX_HOME`，改用其下的 `skills/idiom-puzzle-video`。已有同名目录时请先备份并比较内容，不要直接覆盖。

## 使用

在可用的 Codex 会话中说：

```text
用 $idiom-puzzle-video 做一期“五谷丰登”，生成原创谜面并导出竖屏视频和封面。
```

也可以说：

```text
用 $idiom-puzzle-video 换一个没做过的成语，保留上一期风格，制作下一期。
```

自动生成原创图片需要运行环境提供图像生成工具；也可以提供已有的 9:16 谜面图片。默认工作流不发布到任何社交账号。

## 单独运行渲染脚本

需要 Python 3.10+、中文字体，以及 FFmpeg。依赖中的 `imageio-ffmpeg` 可以提供 FFmpeg 可执行文件。

建议在独立工作目录的虚拟环境中安装依赖：

```bash
python -m venv .venv
# 激活虚拟环境后执行：
python -m pip install -r <skill-dir>/scripts/requirements.txt
python <skill-dir>/scripts/render_video.py --image puzzle.png --config <skill-dir>/assets/shiquanshimei.json --output-dir outputs --work-dir work/render
```

Windows 默认使用微软雅黑。其他系统或自定义字体：

```bash
python <skill-dir>/scripts/render_video.py --image puzzle.png --config episode.json --output-dir outputs --work-dir work/render --font /path/to/chinese-font.ttf --font-bold /path/to/chinese-bold.ttf
```

更多配置参见 [配置说明](references/config.md)，图像构图参见 [提示词模板](references/image-prompt.md)。已有成片默认不会被覆盖，需更换配置的 `filename` 或明确传入 `--overwrite`。

### 随机配乐与指定曲目

技能先运行 `python <skill-dir>/scripts/bgm.py --pick`，将随机返回的曲目 ID 写入当期 `bgm_id`。也可省略 `bgm_id`，由渲染器自动随机选取。知道上一期曲目时，用 `--previous <id>` 或配置 `previous_bgm_id` 排除上一首；没有历史信息时允许随机重复。

指定 `bgm_id` 可固定使用 `bright_pluck`、`playful_marimba`、`gentle_keys`、`curious_clock` 或 `warm_bounce`。生成报告记录实际曲目和响度设置。五段 WAV 随技能提供，正常渲染无需联网取歌；`scripts/bgm.py --build` 可按内置乐谱重建音频素材。

## 文件结构

```text
SKILL.md                  技能入口与工作流
agents/openai.yaml        Codex 显示信息
assets/                   示例题目配置
references/               配置与图像提示词说明
scripts/render_video.py   视频渲染器
scripts/requirements.txt  Python 依赖
```

## 检查与限制

脚本会完整解码视频、确认音视频流，并输出检查报告。仍应人工检查谜面顺序、文字、答案和代表帧。谐音谜题可能存在声调差异或歧义，不应当作严格的语文教学标准。画面中的 AI 提示不代替发布平台要求的内容声明。

图像、输出成片和临时文件放在本次任务工作区；不随技能仓库提交。当前渲染器固定为竖屏 1080P，其他画幅、口播和复杂动画需要扩展。
