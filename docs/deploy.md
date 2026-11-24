# Hosting the app on a server

The app (`app.py`) can run on one GPU server and be used from any phone or
laptop on the same network: testers need only a browser. This is how it runs
on the AI-CoE server, on the college network.

**Access:** campus network only, by address and port: `http://192.168.50.208:7860`.
The server has no public address; that keeps the recordings and the tabs'
lyrics on campus. (Reaching it from outside would need a tunnel, e.g.
Cloudflare Tunnel, and the college's permission.)

## 0. Check the server can host it

```bash
python3 deploy/server_check.py --port 8000
```

It reports the GPUs, checks the internet sites the app needs, and serves a
test page: open the address it prints from a phone on campus Wi-Fi. Done on
2026-11-24 **[ORIGINAL]**: 4 × RTX 6000 Ada (48 GB), 132 GB memory, 286 GB
free disk; all sites reachable; the test page opened from a phone and a
laptop on campus Wi-Fi.

## 1. Install (once)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh        # uv, the package manager (installs Python 3.13 itself)
cd ~/Ukelele/PlayAnySongOnUkelele
uv sync                                                 # ~6 GB: PyTorch with CUDA, models' libraries
./download_chordsdb.sh                                  # the ukulele chord chart
```

On Linux the project installs PyTorch's CUDA 12.6 build (`pyproject.toml`), which
needs an NVIDIA driver ≥ 560; the server's is 575. Check it sees the GPUs:

```bash
uv run python -c "import torch; print(torch.cuda.is_available(), torch.cuda.device_count())"
```

## 2. Try it

```bash
CUDA_VISIBLE_DEVICES=1 uv run python app.py --host 0.0.0.0 --port 7860
```

- `models on cuda; 2 song(s) at a time` should appear.
- Open `http://192.168.50.208:7860` from a phone or laptop on campus.
- `CUDA_VISIBLE_DEVICES=1` puts it on the second GPU; `nvidia-smi` shows
  which are free.
- The first song downloads the models (Whisper `small.en`, Demucs `htdemucs`,
  under 1 GB) once.

Stop with Ctrl+C.

## 3. Keep it running

As a systemd *user* service, so it starts at boot and restarts if it stops:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/playalong.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now playalong
loginctl enable-linger $USER     # keep it running after logout; may need sudo, or ask the admin
```

Edit `~/.config/systemd/user/playalong.service` first if the repository is
not in `~/Ukelele/PlayAnySongOnUkelele`, or to pick another GPU.

| task | command |
|---|---|
| status | `systemctl --user status playalong` |
| logs, live | `journalctl --user -u playalong -f` |
| restart | `systemctl --user restart playalong` |
| stop | `systemctl --user stop playalong` |

Without systemd: run step 2 inside `tmux new -s playalong`, then detach with Ctrl+B D.

## 4. Update to the latest code

```bash
cd ~/Ukelele/PlayAnySongOnUkelele
git pull
uv sync
systemctl --user restart playalong
```

## Options

| option | default | meaning |
|---|---|---|
| `--host` | `127.0.0.1` | `0.0.0.0` to accept every device on the network |
| `--port` | 7860 | |
| `--concurrency` | 2 on a GPU, 1 on a CPU | songs processed at once; the rest wait in a queue |
| `--keep-days` | 7 | runs older than this are deleted, uploaded recordings included |
| `--password` | none | ask for a password (user name `ukulele`) |
| `PLAYALONG_DEVICE` | auto | force `cpu`, or `cuda:N` |

## What uses the GPU

Demucs (vocal separation), Whisper (word times, float16) and lv-chordia (chord
evidence) run on the GPU when PyTorch sees one (`common/devices.py`); the rest
is light. If Whisper cannot start on the GPU it falls back to the CPU and says
so in the log.

## If something goes wrong

| symptom | likely cause |
|---|---|
| the page does not open from a phone | not on the campus network; or the app started without `--host 0.0.0.0`; or a firewall: `sudo ufw allow 7860` |
| `models on cpu` | PyTorch does not see the GPU: check step 1's command, and `nvidia-smi` |
| "Could not read that tab" | Ultimate Guitar refused the request, or the link is not a tab page |
| uploads fail with `PermissionError: /tmp/gradio/…` | fixed in the app: another user's Gradio owned the shared `/tmp/gradio`; uploads now go to `data/preprocessed/gradio-tmp/` (or set `GRADIO_TEMP_DIR`) |
| `git pull` refuses: "local changes … would be overwritten" in `results/` | older versions of the app wrote songs' results into the tracked `results/`; discard them with `git checkout -- results/` and pull again. The app now writes to `data/preprocessed/app-results/` (git-ignored) |
| port already in use | another program on 7860: use `--port 7861` (and in the service file) |
