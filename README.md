# BuckshotRouletteClairvoyance

Press Q to check the bullets.

Steps:
Use GodotPCKExplorer, Extract all & rip pack from the game executable, copy code into the extracted \scripts\ShellSpawner.gd, then pack & embed the code back and it's done, enjoy.

游戏恶魔轮盘赌的透视，按Q查看枪內子弹

https://github.com/DmitriySalnikov/GodotPCKExplorer

使用GodotPCKExplorer解包，代码贴到 \scripts\ShellSpawner.gd 中重新打包即可

## Extended Q / E / combined variants

The original `ShellSpawner.gd` snippet above is preserved. The additional modules provide three independently buildable variants for the inspected **Steam v2.2.0 hotfix 6 / GodotSteam 4.1.1** executable:

| Variant | Q | E |
|---|---|---|
| `q` | Direct remaining shell order; singleplayer and multiplayer host | Not included |
| `e` | Not included | Probability Vision, based only on legitimately obtained information |
| `combined` | Direct order | Independent probability HUD; Q does not add knowledge to E |

Q is a direct-answer feature. E is a separate conditional-probability feature. The combined variant is therefore not a non-cheating MOD as a whole. Use multiplayer modifications only in private games with the other players' agreement.

### Build from your own game

Python 3.11+ is required. No complete game executable, extracted original game script, Steam DLL, backup, credential, or installation receipt is distributed here.

```powershell
python -B .\CombinedVision\tools\build_variants.py `
  --source 'C:\Games\Buckshot Roulette\Buckshot Roulette.vanilla.exe' `
  --variant combined `
  --output '.\build\combined\Buckshot Roulette.QE.exe' `
  --report '.\build\combined\build-verification.json' `
  --runtime-dir '.\build\combined\ProbabilityVision'
```

Use `--variant q` or `--variant e` and **different output/report paths** for independent builds/backups. Inputs are read-only; existing outputs are rejected. Only the exact inspected vanilla SHA256 is supported:

```text
df2f8a31bd469438a1a29f831945ccea7b26963ab735f73b32936792207b1663
```

Other versions must be inspected and ported, not bypassed by removing the version guard. This is a resource patch built with the game's original engine, not an unverified BepInEx/GDWeave integration.

See [Probability Vision](ProbabilityVision/README.md) for the information boundary, probability model, real hook locations, configuration and tests. See [Q/E coexistence](CombinedVision/README.md) for isolated displays, public-source builds, installation and validation guidance.

### 中文概要

新增 Q 单独版、E 单独版和 Q+E 共存版，原项目的两份文件保留。Q 显示真实弹序约3秒，多人仅支持房主；E 默认关闭，按 E 显隐，只记录公开数量、合法手机/放大镜提示以及射击/啤酒/逆转器事件。

两套显示和状态互不传递：即使 Q 已显示下一发答案，E 也不会因此变成100%或新增 Known。组合版使用不同提示层、错开的默认位置，并保留 Q 给直接查看。

源码可从用户自有的原版 EXE 构建三个版本，不依赖不可公开分发的预先修改版 EXE。仓库不包含原游戏、完整提取脚本或个人备份。详细测试步骤见各模块的 README。
