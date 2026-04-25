# RedFlag golden fixtures

Each subdir is named for a RedFlag ID and holds at least two files:

- `positive.yaml` — patient findings that SHOULD trigger the RedFlag
- `negative.yaml` — patient findings that SHOULD NOT trigger it

Both share this shape:

```yaml
red_flag: RF-...                      # echo of the RF being tested
findings:
  some_lab_value: 12.5
  some_boolean_marker: true
  ...
expected_fires: true | false          # whether RF.trigger should evaluate True
```

`tests/test_redflag_fixtures.py` discovers every subdir, loads the named
RedFlag YAML from `knowledge_base/hosted/content/redflags/`, and calls
`evaluate_redflag_trigger` against the fixture's `findings`. The test
fails if `expected_fires` doesn't match the engine's evaluation.

This is the smallest possible unit per RedFlag — it exercises the
trigger predicate only, not Algorithm walking. Algorithm-level golden
tests still live in `tests/test_*_engine.py` per disease.

## Why this layout

- One folder per RF makes coverage trivially countable: `count(folders) == n_RFs_with_tests`
- Fixtures are pure data, no Python — clinicians can hand-author or review them
- Test discovery is automatic; adding a new RF + fixtures requires zero edits to the test file
