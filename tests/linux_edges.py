"""Linux installer tests, including real PTYs and deterministic race injection."""
import errno
import os
from pathlib import Path
import pty
import select
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
FAILURES = []
TOTAL = 0


def run_case(name, code):
    global TOTAL
    TOTAL += 1
    with tempfile.TemporaryDirectory(prefix="gg-edge-") as directory:
        env = dict(os.environ, GG_BIN_DIR=directory + "/bin")
        Path(env["GG_BIN_DIR"]).mkdir()
        env["PATH"] = env["GG_BIN_DIR"] + ":/usr/bin:/bin"
        result = subprocess.run(
            ["bash", "-c", "set -eu\n" + code, "edge", str(ROOT), directory],
            env=env, cwd=directory, text=True, capture_output=True, timeout=20,
        )
        if result.returncode:
            FAILURES.append(name)
            print(f"FAIL {name}: {result.stdout}{result.stderr}", flush=True)
        else:
            print(f"PASS {name}", flush=True)


def interactive(name, occupied_vv, reply):
    global TOTAL
    TOTAL += 1
    with tempfile.TemporaryDirectory(prefix="gg-tty-") as directory:
        env = dict(os.environ, GG_BIN_DIR=directory + "/bin", PATH="/usr/bin:/bin")
        Path(env["GG_BIN_DIR"]).mkdir()
        code = 'root=$1; set --; alias gg="echo FOREIGN"; '
        if occupied_vv:
            code += 'alias vv="echo FOREIGN"; '
        code += 'source "$root/install.sh"'
        master, slave = pty.openpty()
        process = subprocess.Popen(
            ["bash", "--noprofile", "--norc", "-c", code, "tty", str(ROOT)],
            stdin=slave, stdout=slave, stderr=slave, env=env,
        )
        os.close(slave)
        output = b""
        sent = False
        deadline = time.monotonic() + 15
        try:
            while time.monotonic() < deadline:
                readable, _, _ = select.select([master], [], [], 0.1)
                if readable:
                    try:
                        data = os.read(master, 65536)
                    except OSError as error:
                        if error.errno == errno.EIO:
                            break
                        raise
                    if not data:
                        break
                    output += data
                    if b"Choose a name" in output and not sent:
                        os.write(master, (reply + "\n").encode())
                        sent = True
                if process.poll() is not None and not readable:
                    break
            if process.poll() is None:
                raise AssertionError("TTY prompt timeout")
            text = output.decode(errors="replace")
            assert sent, text
            assert ("suggested: vv" in text) == (not occupied_vv), text
            if reply:
                assert process.returncode == 0, text
                assert Path(env["GG_BIN_DIR"], reply).is_symlink(), text
            else:
                assert process.returncode != 0, text
                assert not list(Path(env["GG_BIN_DIR"]).iterdir()), text
            print(f"PASS {name}", flush=True)
        except Exception as error:
            FAILURES.append(name)
            print(f"FAIL {name}: {error}", flush=True)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            os.close(master)


run_case("native links and multiple names", r'''
bash "$1/install.sh" --command gg --non-interactive
bash "$1/install.sh" --command vv --non-interactive
[[ -L $GG_BIN_DIR/gg && -L $GG_BIN_DIR/vv ]]
[[ $(readlink "$GG_BIN_DIR/gg") == "$(readlink "$GG_BIN_DIR/vv")" ]]
cmp <(gg --no-color -w 32 STATUS) <(vv --no-color -w 32 STATUS)
bash "$1/install.sh" --command gg --uninstall
vv --no-color -w 32 STATUS >/dev/null
''')
run_case("width endpoints and exact title fit", r'''
for width in 8 500; do
    result=$(bash "$1/gg" --no-color --style ascii -w "$width")
    [[ ${#result} == $((width + 1)) ]]
    printf -v title '%*s' "$((width - 4))" ''
    bash "$1/gg" --no-color -w "$width" "$title" >/dev/null
    if bash "$1/gg" --no-color -w "$width" "${title}X" >/dev/null 2>&1; then exit 1; fi
done
''')
run_case("dangling foreign link preserved", r'''
ln -s "$2/missing" "$GG_BIN_DIR/vv"
if bash "$1/install.sh" --command vv --non-interactive; then exit 1; fi
[[ $(readlink "$GG_BIN_DIR/vv") == "$2/missing" ]]
''')
run_case("check names has no side effects", r'''
source "$1/install.sh" --check-names >/dev/null
[[ -z $(find "$GG_BIN_DIR" -mindepth 1 -print -quit) ]]
''')
run_case("permission denied fails cleanly", r'''
chmod 500 "$GG_BIN_DIR"
if bash "$1/install.sh" --command vv --non-interactive; then exit 1; fi
[[ -z $(find "$GG_BIN_DIR" -mindepth 1 -print -quit) ]]
chmod 700 "$GG_BIN_DIR"
''')
run_case("hashed foreign executable conflict", r'''
printf '#!/bin/bash\necho foreign\n' > "$2/foreign"
chmod +x "$2/foreign"
hash -p "$2/foreign" vv
if source "$1/install.sh" --command vv --non-interactive; then exit 1; fi
[[ ! -e $GG_BIN_DIR/vv ]]
''')
for kind in ("file", "directory"):
    run_case(f"destination {kind} appears before ln", r'''
mkdir "$2/mock"
printf '#!/bin/bash\n' > "$2/mock/ln"
''' + (r'''printf 'printf foreign > "$GG_BIN_DIR/vv"\n' >> "$2/mock/ln"
''' if kind == "file" else r'''printf 'mkdir "$GG_BIN_DIR/vv"\n' >> "$2/mock/ln"
''') + r'''
printf 'exec /usr/bin/ln "$@"\n' >> "$2/mock/ln"
chmod +x "$2/mock/ln"
if PATH="$2/mock:$PATH" bash "$1/install.sh" --command vv --non-interactive; then exit 1; fi
''' + (r'''[[ $(cat "$GG_BIN_DIR/vv") == foreign ]]
''' if kind == "file" else r'''[[ -z $(find "$GG_BIN_DIR/vv" -mindepth 1 -print -quit) ]]
'''))
run_case("interrupted copy preserves installed generator", r'''
bash "$1/install.sh" --command vv --non-interactive >/dev/null
before=$(sha256sum "$GG_BIN_DIR/.gg-divider/gg")
mkdir "$2/mock"
printf '#!/bin/bash\nprintf BROKEN > "${@: -1}"\nexit 1\n' > "$2/mock/cp"
chmod +x "$2/mock/cp"
if PATH="$2/mock:$PATH" bash "$1/install.sh" --command vv --non-interactive; then exit 1; fi
[[ $(sha256sum "$GG_BIN_DIR/.gg-divider/gg") == "$before" ]]
''')
run_case("concurrent installs leave complete shared files", r'''
for i in 1 2 3 4 5 6; do
    name=gg
    if ((i % 2 == 0)); then name=vv; fi
    bash "$1/install.sh" --command "$name" --non-interactive >"$2/log-$i" 2>&1 &
done
wait
current=$(cat "$GG_BIN_DIR/.gg-divider/current")
cmp "$1/gg" "$GG_BIN_DIR/.gg-divider/$current/gg"
cmp "$1/gg-names.sh" "$GG_BIN_DIR/.gg-divider/$current/gg-names.sh"
[[ -L $GG_BIN_DIR/gg && -L $GG_BIN_DIR/vv ]]
gg --no-color -w 32 STATUS >/dev/null
vv --no-color -w 32 STATUS >/dev/null
[[ -z $(find "$GG_BIN_DIR/.gg-divider" -name '.update.*' -print -quit) ]]
''')
for point in ("before", "after"):
    run_case(f"SIGKILL {point} release commit preserves a complete pair", r'''
mkdir "$2/src" "$2/mock"
cp "$1/gg" "$1/gg-names.sh" "$1/gg-launcher.sh" "$1/install.sh" "$2/src/"
sed -i '2a _gg_test_release=A' "$2/src/gg"
sed -i '/^_gg_enable_function() {/a\    [[ ${_gg_test_release:-} == A ]] || return 91' "$2/src/gg-names.sh"
bash "$2/src/install.sh" --command vv --non-interactive >/dev/null
old=$(cat "$GG_BIN_DIR/.gg-divider/current")
sed -i 's/_gg_test_release=A/_gg_test_release=B/' "$2/src/gg"
sed -i 's/== A/== B/' "$2/src/gg-names.sh"
cat > "$2/mock/mv" <<'MOCK'
#!/bin/bash
if [[ ${@: -1} == "$GG_BIN_DIR/.gg-divider/current" ]]; then
    if [[ $CRASH_AT == after ]]; then /usr/bin/mv "$@" || exit; fi
    kill -KILL "$PPID"
    exit 137
fi
exec /usr/bin/mv "$@"
MOCK
chmod +x "$2/mock/mv"
''' + f'export CRASH_AT={point}\n' + r'''
if PATH="$2/mock:$PATH" bash "$2/src/install.sh" --command vv --non-interactive; then exit 1; fi
new=$(cat "$GG_BIN_DIR/.gg-divider/current")
if [[ $CRASH_AT == before ]]; then
    [[ $new == "$old" ]]; expected=A
else
    [[ $new != "$old" ]]; expected=B
fi
source "$GG_BIN_DIR/.gg-divider/gg" --function vv
[[ $_gg_test_release == "$expected" ]]
vv --no-color -w 32 STATUS >/dev/null
[[ -f $GG_BIN_DIR/.gg-divider/$old/gg-names.sh ]]
bash "$2/src/install.sh" --command vv --non-interactive >/dev/null
source "$GG_BIN_DIR/.gg-divider/gg" --function vv
[[ $_gg_test_release == B ]]
''')
run_case("source pins its release across a concurrent update", r'''
mkdir "$2/src"
cp "$1/gg" "$1/gg-names.sh" "$1/gg-launcher.sh" "$1/install.sh" "$2/src/"
sed -i '2a _gg_test_release=A' "$2/src/gg"
sed -i '/^_gg_enable_function() {/a\    [[ ${_gg_test_release:-} == A ]] || return 91' "$2/src/gg-names.sh"
# Pause only readers, after loading the generator but before loading policy.
sed -i '/^    source .*gg-names.sh/i\    if [[ -n ${GG_TEST_GATE:-} ]]; then touch "$GG_TEST_GATE.ready"; while [[ ! -e $GG_TEST_GATE.go ]]; do sleep 0.01; done; fi' "$2/src/gg"
bash "$2/src/install.sh" --command vv --non-interactive >/dev/null
GG_TEST_GATE=$2/gate bash -c 'set -e; source "$1" --function vv; [[ $_gg_test_release == A ]]; vv --no-color -w 32 STATUS >/dev/null' reader "$GG_BIN_DIR/.gg-divider/gg" &
reader=$!
for i in {1..200}; do [[ ! -f $2/gate.ready ]] || break; sleep 0.01; done
[[ -f $2/gate.ready ]]
sed -i 's/_gg_test_release=A/_gg_test_release=B/' "$2/src/gg"
sed -i 's/== A/== B/' "$2/src/gg-names.sh"
bash "$2/src/install.sh" --command vv --non-interactive >/dev/null
touch "$2/gate.go"
wait "$reader"
source "$GG_BIN_DIR/.gg-divider/gg" --function vv
[[ $_gg_test_release == B ]]
''')
run_case("legacy installation migrates without changing legacy policy", r'''
home=$GG_BIN_DIR/.gg-divider
mkdir "$home"
cp "$1/gg" "$home/gg"
cp "$1/gg-names.sh" "$home/gg-names.sh"
chmod +x "$home/gg"
printf 'gg-terminal-divider-v1\n' > "$home/owner"
ln -s "$home/gg" "$GG_BIN_DIR/vv"
before=$(sha256sum "$home/gg-names.sh")
bash "$1/install.sh" --command vv --non-interactive >/dev/null
[[ $(sha256sum "$home/gg-names.sh") == "$before" ]]
cmp "$1/gg-launcher.sh" "$home/gg"
source "$home/gg" --function vv
vv --no-color -w 32 STATUS >/dev/null
''')
run_case("selected release survives update and uninstall before first open", r'''
mkdir "$2/src" "$2/mock"
cp "$1/gg" "$1/gg-names.sh" "$1/gg-launcher.sh" "$1/install.sh" "$2/src/"
sed -i '/^_gg_generate() {/a\    printf "RELEASE-A\\n"' "$2/src/gg"
bash "$2/src/install.sh" --command vv --non-interactive >/dev/null
old=$(cat "$GG_BIN_DIR/.gg-divider/current")
cat > "$2/mock/bash" <<'MOCK'
#!/bin/bash
if [[ $1 == "$GG_BIN_DIR/.gg-divider/"version.??????/gg ]]; then
    touch "$GG_TEST_GATE.ready"
    while [[ ! -e $GG_TEST_GATE.go ]]; do sleep 0.01; done
fi
exec /usr/bin/bash "$@"
MOCK
chmod +x "$2/mock/bash"
GG_TEST_GATE=$2/gate PATH="$2/mock:$PATH" /usr/bin/bash "$GG_BIN_DIR/.gg-divider/gg" --no-color -w 32 STATUS > "$2/output" &
reader=$!
for i in {1..200}; do [[ ! -f $2/gate.ready ]] || break; sleep 0.01; done
[[ -f $2/gate.ready ]]
sed -i 's/RELEASE-A/RELEASE-B/' "$2/src/gg"
bash "$2/src/install.sh" --command vv --non-interactive >/dev/null
bash "$2/src/install.sh" --command vv --uninstall
[[ -f $GG_BIN_DIR/.gg-divider/$old/gg && -f $GG_BIN_DIR/.gg-divider/$old/gg-names.sh ]]
touch "$2/gate.go"
wait "$reader"
grep -q RELEASE-A "$2/output"
''')
run_case("generator updates preserve installed v1 launcher", r'''
mkdir "$2/src"
cp "$1/gg" "$1/gg-names.sh" "$1/gg-launcher.sh" "$1/install.sh" "$2/src/"
bash "$2/src/install.sh" --command vv --non-interactive >/dev/null
home=$GG_BIN_DIR/.gg-divider
before=$(sha256sum "$home/gg")
inode=$(stat -c '%d:%i' "$home/gg")
sed -i '/^_gg_generate() {/a\    printf "NEW-GENERATOR\\n"' "$2/src/gg"
printf '\n# Policy update compatible with launcher protocol v1.\n' >> "$2/src/gg-names.sh"
bash "$2/src/install.sh" --command vv --non-interactive >/dev/null
[[ $(sha256sum "$home/gg") == "$before" && $(stat -c '%d:%i' "$home/gg") == "$inode" ]]
[[ $(vv --no-color -w 32 STATUS) == *NEW-GENERATOR* ]]
source "$home/gg" --function vv
[[ $(vv --no-color -w 32 STATUS) == *NEW-GENERATOR* ]]
''')
interactive("TTY accepts checked vv", False, "vv")
interactive("TTY both occupied, manual xx", True, "xx")
interactive("TTY cancel changes nothing", False, "")
print(f"Linux edges: {TOTAL - len(FAILURES)}/{TOTAL} passed", flush=True)
raise SystemExit(bool(FAILURES))
