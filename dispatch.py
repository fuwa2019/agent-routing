#!/usr/bin/env python3
"""按任务卡把任务派给 Codex / agy(Gemini) / Claude CLI。

用法:
  python3 dispatch.py new <路径.md> [--id T1]   从模板生成任务卡
  python3 dispatch.py run <卡.md> [<卡.md> ...] [--dry-run] [--parallel]
  python3 dispatch.py models                     列出本机可用模型

只用标准库，mac / Windows 通用。每次运行在 <cwd>/.agent-runs/ 下写一份 json 日志。
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "templates" / "task-card.md"
EFFORTS = {"low", "medium", "high", "xhigh", "max", "ultra"}
TOOLS = {"codex", "agy", "claude"}

COMMON_RULES = """[通用约束]
- 工作目录：{cwd}。若其中有 AGENTS.md 或 CLAUDE.md，先读并遵守；它们优先于本任务卡。
- 模式：{mode_text}
- 不显示或写出密码、Token、Cookie、私钥、.env 内容。
- 不连接远程服务器、不启动长时间计算、不安装依赖，除非下面的任务明确要求。
- 用中文写结论；引用代码写 file:line；不确定的事实标出依据而不是猜测。
- 你的最后一条消息就是交付物，会被原样保存到 {output}。
"""
MODE_TEXT = {
    "read": "只读。不要创建、修改或删除任何文件。",
    "write": "可写。只改本任务涉及的文件；不 git commit、不切换分支、不 push。最后一条消息列出改了哪些文件、做了哪些验证、还剩什么。",
}


def parse_card(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        sys.exit(f"{path}: 缺少 frontmatter")
    _, head, body = text.split("---", 2)
    meta: dict[str, str] = {}
    for line in head.splitlines():
        line = line.split(" #", 1)[0].rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, _, val = line.partition(":")
        meta[key.strip()] = val.strip()
    return meta, body.strip()


def split_list(val: str) -> list[str]:
    return [x.strip() for x in val.split(",") if x.strip()]


def is_git(path: Path) -> bool:
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
                       capture_output=True, text=True)
    return r.returncode == 0


def git_head(path: Path) -> str | None:
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() or None


def ensure_excluded(repo: Path) -> None:
    """把 .agent-runs/ 加进本地 .git/info/exclude（不改 .gitignore、不进提交）。"""
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-common-dir"],
                       capture_output=True, text=True)
    if r.returncode:
        return
    gd = Path(r.stdout.strip())
    if not gd.is_absolute():
        gd = repo / gd
    ex = gd / "info" / "exclude"
    ex.parent.mkdir(parents=True, exist_ok=True)
    cur = ex.read_text(encoding="utf-8") if ex.exists() else ""
    if ".agent-runs/" not in cur.split():
        ex.write_text(cur.rstrip("\n") + "\n.agent-runs/\n", encoding="utf-8")


def validate(card: Path, meta: dict) -> list[str]:
    errs = []
    for k in ("id", "tool", "model", "mode", "output"):
        if not meta.get(k):
            errs.append(f"缺少字段 {k}")
    if meta.get("tool") and meta["tool"] not in TOOLS:
        errs.append(f"tool 必须是 {sorted(TOOLS)}")
    if meta.get("mode") and meta["mode"] not in MODE_TEXT:
        errs.append("mode 必须是 read 或 write")
    if meta.get("effort") and meta["effort"] not in EFFORTS:
        errs.append(f"effort 必须是 {sorted(EFFORTS)}")
    if meta.get("worktree") and meta.get("tool") != "codex":
        errs.append("worktree 只用于 codex")
    for dep in split_list(meta.get("depends", "")):
        dpath = (card.parent / dep).resolve()
        if not dpath.exists():
            errs.append(f"前置任务卡不存在: {dep}")
            continue
        dmeta, _ = parse_card(dpath)
        dcwd = (dpath.parent / dmeta.get("cwd", ".")).resolve()
        if not (dcwd / dmeta.get("output", "")).exists():
            errs.append(f"前置任务 {dmeta.get('id')} 的交付物还没有: {dmeta.get('output')}")
    return errs


def build(card: Path, meta: dict, body: str, dry: bool) -> tuple[list[str], Path, Path, str]:
    cwd = (card.parent / meta.get("cwd", ".")).resolve()
    run_cwd = cwd
    if meta.get("worktree"):
        wt = (cwd / meta["worktree"]).resolve()
        if not wt.exists() and not dry:
            if not is_git(cwd):
                sys.exit(f"{card}: cwd 不是 git 仓库，不能建 worktree")
            subprocess.run(["git", "-C", str(cwd), "worktree", "add", "-b",
                            f"agent/{meta['id']}", str(wt)], check=True)
        run_cwd = wt
    output = (cwd / meta["output"]).resolve()
    inputs = split_list(meta.get("inputs", ""))
    prompt = COMMON_RULES.format(cwd=run_cwd, mode_text=MODE_TEXT[meta["mode"]], output=output)
    if inputs:
        prompt += "\n[输入]\n" + "\n".join(f"- {cwd / i}" for i in inputs) + "\n"
    prompt += f"\n[任务 {meta['id']}]\n{body}\n"

    tool, model, effort, mode = meta["tool"], meta["model"], meta.get("effort", ""), meta["mode"]
    if tool == "codex":
        cmd = ["codex", "exec", "-m", model, "--skip-git-repo-check",
               "-s", "read-only" if mode == "read" else "workspace-write",
               "-C", str(run_cwd), "-o", str(output)]
        if effort:
            cmd += ["-c", f"model_reasoning_effort={effort}"]
        if run_cwd != cwd:
            cmd += ["--add-dir", str(cwd)]
        cmd.append(prompt)
    elif tool == "agy":
        cmd = ["agy", "-p", prompt, "--model", model, "--output-format", "text",
               "--mode", "plan" if mode == "read" else "accept-edits"]
        if effort and not model.rsplit("-", 1)[-1] in EFFORTS:
            cmd += ["--effort", effort]
    else:  # claude
        cmd = ["claude", "-p", prompt, "--model", model,
               "--permission-mode", "plan" if mode == "read" else "acceptEdits"]
        if effort:
            cmd += ["--effort", effort]
    return cmd, run_cwd, output, prompt


def run_one(card: Path, dry: bool) -> int:
    meta, body = parse_card(card)
    errs = validate(card, meta)
    if errs and not dry:
        print(f"[{card.name}] 拒绝运行:\n  " + "\n  ".join(errs))
        return 2
    cmd, run_cwd, output, prompt = build(card, meta, body, dry)
    shown = [c if c != prompt else f"<prompt {len(prompt)} 字>" for c in cmd]
    if dry:
        print(f"== {meta.get('id')} ({card.name})")
        if errs:
            print("  校验问题: " + "; ".join(errs))
        print("  cwd: " + str(run_cwd))
        print("  cmd: " + " ".join(shown))
        print("  ---- prompt ----\n" + prompt)
        return 0
    if not shutil.which(cmd[0]):
        print(f"[{meta['id']}] 找不到命令 {cmd[0]}")
        return 127
    output.parent.mkdir(parents=True, exist_ok=True)
    log_dir = (card.parent / meta.get("cwd", ".")).resolve() / ".agent-runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    if is_git(run_cwd):
        ensure_excluded(run_cwd)
    start = dt.datetime.now()
    print(f"[{meta['id']}] {meta['tool']} {meta['model']} 开始 {start:%H:%M:%S}")
    try:
        r = subprocess.run(cmd, cwd=run_cwd, capture_output=True, text=True,
                           timeout=int(meta.get("timeout") or 3600), stdin=subprocess.DEVNULL)
        code, out, err = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        code, out, err = 124, (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), "timeout"
    if meta["tool"] != "codex" and out:
        output.write_text(out, encoding="utf-8")
    end = dt.datetime.now()
    stamp = f"{start:%Y%m%d-%H%M%S}-{meta['id']}"
    (log_dir / f"{stamp}.stderr.txt").write_text(err or "", encoding="utf-8")
    log = {
        "id": meta["id"], "card": str(card.resolve()), "tool": meta["tool"], "model": meta["model"],
        "effort": meta.get("effort", ""), "mode": meta["mode"], "cwd": str(run_cwd),
        "git_head": git_head(run_cwd), "output": str(output), "output_exists": output.exists(),
        "exit_code": code, "start": start.isoformat(timespec="seconds"),
        "end": end.isoformat(timespec="seconds"), "seconds": round((end - start).total_seconds()),
        "cmd": shown,
    }
    (log_dir / f"{stamp}.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    status = "完成" if code == 0 and output.exists() else "失败"
    print(f"[{meta['id']}] {status} exit={code} {log['seconds']}s → {output}")
    return code if code else (0 if output.exists() else 1)


def cmd_models() -> None:
    print("== Codex（模型目录，由环境变量 CODEX_MODEL_CATALOG 指定 json 文件）")
    env = os.environ.get("CODEX_MODEL_CATALOG", "")
    cat = Path(env).expanduser() if env else None
    if cat and cat.exists():
        d = json.loads(cat.read_text(encoding="utf-8"))
        for m in d.get("models", d if isinstance(d, list) else []):
            lv = [x.get("effort") for x in m.get("supported_reasoning_levels", [])]
            print(f"  {m.get('slug'):24} {'/'.join(lv)}")
    else:
        print("  未设置或找不到 CODEX_MODEL_CATALOG，回退到 codex 自带说明（可运行 codex --help 查看，或自行设置该环境变量）")
    print("== agy")
    if shutil.which("agy"):
        subprocess.run(["agy", "models"])
    print("== claude\n  claude-opus-5-5 / claude-sonnet-5-5 / claude-haiku-5-5（--effort low..max）")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="sub", required=True)
    n = sub.add_parser("new")
    n.add_argument("path")
    n.add_argument("--id", default="T1")
    r = sub.add_parser("run")
    r.add_argument("cards", nargs="+")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--parallel", action="store_true", help="并行运行（只用于互不依赖、互不写同一文件的卡）")
    sub.add_parser("models")
    a = ap.parse_args()

    if a.sub == "models":
        cmd_models()
    elif a.sub == "new":
        p = Path(a.path)
        if p.exists():
            sys.exit(f"{p} 已存在，不覆盖")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(TEMPLATE.read_text(encoding="utf-8").replace("id: T1", f"id: {a.id}", 1)
                     .replace("out/T1.md", f"out/{a.id}.md", 1), encoding="utf-8")
        print(f"已生成 {p}")
    else:
        cards = [Path(c) for c in a.cards]
        if a.parallel and not a.dry_run:
            writers = [c for c in cards if parse_card(c)[0].get("mode") == "write"]
            if len(writers) > 1:
                sys.exit("并行时最多一张 write 卡（同一组文件只能有一个写手）")
            with cf.ThreadPoolExecutor(len(cards)) as ex:
                codes = list(ex.map(lambda c: run_one(c, False), cards))
        else:
            codes = []
            for c in cards:
                codes.append(run_one(c, a.dry_run))
                if codes[-1] and not a.dry_run:
                    print("前一张卡失败，后面的不再运行")
                    break
        sys.exit(max(codes) if codes else 0)


if __name__ == "__main__":
    main()
