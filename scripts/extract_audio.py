#!/usr/bin/env python3
"""
从视频文件中提取音频轨道。
用法: python extract_audio.py <video.mp4> [output.wav]
需要安装 ffmpeg（系统级别）或 moviepy（Python 包）。
"""
import sys
import subprocess
from pathlib import Path


def extract_with_ffmpeg(video_path: str, audio_path: str) -> bool:
    """使用 ffmpeg 提取音频"""
    try:
        subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-vn",                 # 不要视频
                "-acodec", "pcm_s16le",  # WAV 格式
                "-ar", "16000",         # 16kHz 采样率（适合语音识别）
                "-ac", "1",             # 单声道
                "-y",                   # 覆盖已有文件
                audio_path
            ],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg 错误: {e.stderr}")
        return False
    except FileNotFoundError:
        return False


def extract_with_moviepy(video_path: str, audio_path: str) -> bool:
    """使用 moviepy 提取音频"""
    try:
        from moviepy import VideoFileClip  # moviepy 2.x
    except ImportError:
        try:
            from moviepy.editor import VideoFileClip  # moviepy 1.x
        except ImportError:
            print("moviepy 未安装。请安装: pip install moviepy")
            return False

    try:
        clip = VideoFileClip(video_path)
        audio = clip.audio
        if audio is None:
            print("错误: 视频中没有音频轨道")
            clip.close()
            return False
        audio.write_audiofile(audio_path, codec="pcm_s16le", fps=16000)
        audio.close()
        clip.close()
        return True
    except Exception as e:
        print(f"moviepy 错误: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("用法: python extract_audio.py <video.mp4> [output.wav]")
        sys.exit(1)

    video_path = sys.argv[1]
    if not Path(video_path).exists():
        print(f"错误: 文件不存在 — {video_path}")
        sys.exit(1)

    # 默认输出路径
    if len(sys.argv) > 2:
        audio_path = sys.argv[2]
    else:
        audio_path = str(Path(video_path).with_suffix(".wav"))

    print(f"正在从 {video_path} 提取音频...")

    # 优先尝试 ffmpeg
    success = extract_with_ffmpeg(video_path, audio_path)
    if not success:
        print("ffmpeg 不可用，尝试 moviepy...")
        success = extract_with_moviepy(video_path, audio_path)

    if success:
        size_mb = Path(audio_path).stat().st_size / (1024 * 1024)
        print(f"音频已提取: {audio_path} ({size_mb:.1f} MB)")
    else:
        print("错误: 无法提取音频。请安装 ffmpeg 或 moviepy。")
        print("  ffmpeg: https://ffmpeg.org/download.html")
        print("  moviepy: pip install moviepy")
        sys.exit(1)


if __name__ == "__main__":
    main()
