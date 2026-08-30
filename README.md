# yt2feishu

Turn a YouTube URL into a clean Markdown transcript, with an optional Feishu Docs upload step.

This is the first local MVP:

- Reads YouTube metadata and caption tracks with `yt-dlp`
- Prefers manual subtitles, then auto-generated captions
- Supports JSON3 and VTT caption formats
- Writes a Markdown note with source metadata and timestamped transcript
- Optionally calls `feishu-cli` to import the Markdown into Feishu Docs

## Requirements

Install `yt-dlp` so the command is available on PATH. For current YouTube support, prefer the default extra because it includes the EJS helper package used by modern `yt-dlp`:

```powershell
pip install -r requirements.txt
```

For Feishu upload, install and configure `feishu-cli` separately.
See [FEISHU_SETUP.md](FEISHU_SETUP.md) for the setup flow.

## Usage

Check local dependencies first:

```powershell
python -m yt2feishu --doctor
```

Start the local prototype page:

```powershell
python -m yt2feishu.web
```

On Windows, you can also run:

```powershell
.\scripts\start-web.ps1
```

Then open:

```text
http://127.0.0.1:8765
```

```powershell
python -m yt2feishu "https://www.youtube.com/watch?v=VIDEO_ID" --out-dir notes
```

Preferred languages can be changed:

```powershell
python -m yt2feishu "https://www.youtube.com/watch?v=VIDEO_ID" --langs zh-Hans,zh-Hant,zh,en
```

If YouTube asks yt-dlp to sign in or confirm you are not a bot, pass browser cookies:

```powershell
python -m yt2feishu "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-from-browser chrome
```

If yt-dlp asks for a JavaScript runtime, install or enable one and pass it through:

```powershell
python -m yt2feishu "https://www.youtube.com/watch?v=VIDEO_ID" --js-runtimes node --remote-components ejs:github
```

Upload to Feishu after writing Markdown:

```powershell
python -m yt2feishu "https://www.youtube.com/watch?v=VIDEO_ID" --upload --feishu-verbose
```

The upload command currently shells out to:

```powershell
feishu-cli doc import <markdown_path> --title <title>
```

## Current Scope

This version intentionally does not download video/audio. If a video has no captions, the command exits with a clear error. ASR fallback can be added later with Whisper or Feishu Minutes.
