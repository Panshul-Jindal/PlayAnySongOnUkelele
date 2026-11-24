# lv-chordia heads

lv-chordia's six probability heads for each song, saved before any chord is
named: `<song>.npz`. The layout is in the docstring of
`chord-estimation/lv_chordia_heads.py`.

These files are **not in git**: they are binary, 1–4 MB each, and rebuilt by

```sh
uv run python chord-estimation/lv_chordia_heads.py data/Custom_Songs/<song>/<recording>.wav
```

or as a side effect of `chord-estimation/check_lv_chordia_decoder.py`.
Decode one with `chord-estimation/chord_decoder.py`.
