"""Learn the 16.20 packet formats unattended: every packet id of the replay through server/pkt_schema.py
(learn on the longest sample, then check, then many), several at a time.

    python tools/batch_learn16.py [workers, default 5] [--retry] [id ...]

One line per id is appended to data/exe1620/codec/batch_learn.txt; each learner's own output goes to
data/exe1620/codec/learn<id>.log. Ids that already have a <id>.tree.json are skipped, so the run can be
stopped and started again. Needs no running game (works from the snapshot of tools/snapshot16.py).
"""
import concurrent.futures, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODEC = os.path.join(ROOT, "data", "exe1620", "codec")
SCHEMA = os.path.join(ROOT, "server", "pkt_schema.py")
ENV = dict(os.environ, BA_PATCH="1620", PKT_LONGEST="1", PYTHONIOENCODING="utf-8")


def last_line(args, timeout):
    try:
        p = subprocess.run([sys.executable, SCHEMA] + args, env=ENV, capture_output=True, text=True, timeout=timeout,
                           cwd=ROOT)
        lines = [l for l in (p.stdout + p.stderr).splitlines() if l.strip()]
        return lines[-1][:160] if lines else "(no output)"
    except subprocess.TimeoutExpired:
        return f"timeout after {timeout} s"


def one(pid):
    t0 = time.time()
    tree = os.path.join(CODEC, f"{pid}.tree.json")
    if not os.path.exists(tree):
        with open(os.path.join(CODEC, f"learn{pid}.log"), "w", encoding="utf-8") as log:
            try:
                subprocess.run([sys.executable, SCHEMA, "learn", str(pid)], env=ENV, stdout=log, stderr=subprocess.STDOUT,
                               timeout=3 * 3600, cwd=ROOT)
            except subprocess.TimeoutExpired:
                log.write("\ntimeout\n")
    if not os.path.exists(tree):
        log_lines = open(os.path.join(CODEC, f"learn{pid}.log"), encoding="utf-8", errors="replace").read().splitlines()
        line = f"{pid} | NOT LEARNT | {(log_lines[-1] if log_lines else '')[:160]}"
    else:
        line = f"{pid} | {last_line(['check', str(pid), '40'], 1800)} | {last_line(['many', str(pid), '2000'], 3600)}"
    line += f" | {time.time() - t0:.0f} s"
    with open(os.path.join(CODEC, "batch_learn.txt"), "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line


def main():
    args = sys.argv[1:]
    retry = '--retry' in args      # forget the ids that were not learnt (or failed a check) and try them again
    args = [a for a in args if a != '--retry']
    workers = int(args.pop(0)) if args else 5
    os.makedirs(CODEC, exist_ok=True)
    if args:
        ids = [int(a) for a in args]
    else:
        ids = [int(l.split()[0]) for l in open(os.path.join(ROOT, "data", "exe1620", "emu_check.txt")).read().splitlines()[1:]]
    done = set()
    path = os.path.join(CODEC, "batch_learn.txt")
    if os.path.exists(path):
        lines = [l for l in open(path, encoding="utf-8") if l.strip()]
        if retry:
            good = lambda l: "NOT LEARNT" not in l and "Error" not in l and "DIFFERENT" not in l and ", 0 not encodable, 0 not read" in l
            lines = [l for l in lines if good(l)]
            open(path, "w", encoding="utf-8").writelines(lines)
        done = {int(l.split()[0]) for l in lines}
    ids = [i for i in ids if i not in done]
    print(f"{len(ids)} ids to learn, {workers} at a time", flush=True)
    with concurrent.futures.ThreadPoolExecutor(workers) as ex:
        for line in ex.map(one, ids):
            print(line, flush=True)


if __name__ == "__main__":
    main()
