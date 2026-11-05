# BTC-ISMIR19 (vendored)

The model code of BTC, from the official repository:

- **Repository:** [jayg996/BTC-ISMIR19](https://github.com/jayg996/BTC-ISMIR19)
- **Commit:** `2682317be668032e6e4b269ded36adaa2ad57df0`
- **Licence:** MIT; `LICENSE` is the repository's own.
- **Paper:** Park, Choi, Jeon, Kim & Park, ISMIR 2019.

| file | SHA-256 at that commit |
|---|---|
| `btc_model.py` | `b8cc0b66f3e7bc92e9703ea408bce21d8a39b10c3133cb2ab569c285fceb3a27` |
| `utils/transformer_modules.py` | `a68458094e1af876b021d3f955b70f52382c30a818bb51aff908ffec35310ece` |
| `LICENSE` | `7439cc22ff2efee600131dc5d800ab1204d8076a1a815d842a0319782520fc85` |

## Changes from that commit

`LICENSE` is unchanged. There are three changes to the code:

1. **`btc_model.py`:** the import `from utils.hparams import HParams` is
   removed. Only the file's own `__main__` self-test used it, and it needs
   PyYAML.
2. **`btc_model.py`:** that `__main__` self-test is removed.
3. **`utils/transformer_modules.py`, line 30:** `astype(np.float)` becomes
   `astype(float)`. NumPy no longer has the alias. Its own error message
   (NumPy 2.5.4) says *"`np.float` was a deprecated alias for the builtin
   `float`. … use `float` by itself. Doing this will not modify any behavior
   and is safe"*.

The weights, the features and the inference loop are not vendored here. The
weights come from `./download_btc.sh`. The features and the loop are
re-implemented, and cited, in `chord-estimation/btc.py`.
