

## Billboard 2.0  Billboard 1.0 Release


[[The McGill Billboard Project]]









[data/chords/](vscode-webview://1mu2hspelfutqfkvbk2a4b91qutd45etmn6fijfnshg9vfafq57a/playability-billboard-guitar/data/chords/) has 200 salami files, [data/lab_files/](vscode-webview://1mu2hspelfutqfkvbk2a4b91qutd45etmn6fijfnshg9vfafq57a/playability-billboard-guitar/data/lab_files/) has 199 `_full.lab` — so one song has no lab counterpart. Both are renamed by song id (`78_…` ↔ folder `0078`).

One thing to watch: the copies in `playability-billboard-guitar/` are **not** byte-identical to the ones in `data/McGillBillboard/` — they're a different release. Song 78 has `A:maj/2` in the playability copy vs `A:maj/9` in the McGill copy, and the lab segmentation granularity differs. If you mix the two directories you'll get inconsistent bass-degree labels

