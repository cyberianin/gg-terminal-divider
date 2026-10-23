# Original rendering fixtures

Captured from the original `gg` at commit
`4c20cc36b7692137d727169e76574a023976cd8d`, before the command-name changes.
Each file contains exact stdout, including leading and trailing newlines:
`--no-color -w 32 -s STYLE -l LAYOUT -a ALIGN STATUS`.

`bash tests/regression.sh` compares the current executable against these files.
The test never reads Git history and never regenerates its own expectations.
Change fixtures only after explicitly reviewing an intended rendering change.
