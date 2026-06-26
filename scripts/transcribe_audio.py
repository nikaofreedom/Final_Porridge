#!/usr/bin/env python3
"""
将音频文件转写为文字。需要提供 OpenAI API 兼容的接口或是本地 Whisper。
用法: python transcribe_audio.py <audio.wav> [--provider openai|whisper|google]
"""
import sys
import json
from pathlib import Path


def transcribe_with_whisper(audio_path: str, model_size: str = "medium") -> dict:
    """使用本地 OpenAI Whisper 进行转写"""
    try:
        import whisper
    except ImportError:
        print("请安装 openai-whisper: pip install openai-whisper")
        return {"error": "whisper 未安装"}

    print(f"正在加载 Whisper 模型 ({model_size})...")
    model = whisper.load_model(model_size)

    print("正在转写，请稍候...")
    result = model.transcribe(
        audio_path,
        language="zh",           # 中文为主
        verbose=False,
        task="transcribe"
    )

    # 提取段落级别的分段
    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 1),
            "end": round(seg["end"], 1),
            "text": seg["text"].strip()
        })

    return {
        "full_text": result["text"].strip(),
        "segments": segments,
        "language": result.get("language", "zh")
    }


def transcribe_with_openai(audio_path: str, api_key: str, base_url: str = None) -> dict:
    """使用 OpenAI API 进行转写（也兼容各种中转站）"""
    try:
        from openai import OpenAI
    except ImportError:
        print("请安装 openai: pip install openai")
        return {"error": "openai 包未安装"}

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            language="zh"
        )

    segments = []
    for seg in transcript.segments if hasattr(transcript, 'segments') else []:
        segments.append({
            "start": round(seg.start, 1),
            "end": round(seg.end, 1),
            "text": seg.text.strip()
        })

    return {
        "full_text": transcript.text.strip(),
        "segments": segments,
        "language": transcript.language if hasattr(transcript, 'language') else "zh"
    }


def detect_key_points(text: str) -> list[str]:
    """自动检测音频中提到"重点""必考""重要""注意""关键"的句子"""
    keywords = ["重点", "必考", "重要", "一定要记住", "关键是",
                "注意", "核心", "考点", "记下来", "考试", "会考"]
    sentences = text.replace("！", "。").replace("？", "。").replace("，", "。").split("。")
    key_sentences = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        for kw in keywords:
            if kw in s and s not in key_sentences:
                key_sentences.append(f"★ [{kw}] {s}")
                break
    return key_sentences


def main():
    if len(sys.argv) < 2:
        print("用法: python transcribe_audio.py <audio.wav> [--provider local|openai] [--output result.json]")
        sys.exit(1)

    audio_path = sys.argv[1]
    if not Path(audio_path).exists():
        print(f"错误: 文件不存在 — {audio_path}")
        sys.exit(1)

    provider = "local"
    output_path = None
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == "--provider" and i + 1 < len(sys.argv):
            provider = sys.argv[i + 1]
        elif arg == "--output" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    print(f"正在转写音频: {audio_path} (provider={provider})")

    if provider == "openai":
        import os
        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", None)
        if not api_key:
            print("错误: 请设置 OPENAI_API_KEY 环境变量")
            sys.exit(1)
        result = transcribe_with_openai(audio_path, api_key, base_url)
    else:
        result = transcribe_with_whisper(audio_path)

    if "error" in result:
        print(f"转写失败: {result['error']}")
        sys.exit(1)

    # 检测重点句子
    key_points = detect_key_points(result.get("full_text", ""))
    result["key_points"] = key_points
    result["key_point_count"] = len(key_points)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {output_path}")

    print(f"\n=== 转写结果 ===")
    print(f"语言: {result.get('language', 'unknown')}")
    print(f"段落数: {len(result.get('segments', []))}")
    print(f"检测到重点句子: {len(key_points)} 处")
    print(f"\n--- 全文 ---")
    print(result["full_text"][:2000])
    if len(result["full_text"]) > 2000:
        print(f"\n... (共 {len(result['full_text'])} 字，仅显示前 2000)")

    if key_points:
        print(f"\n--- 自动识别的重点 ---")
        for kp in key_points:
            print(kp)


if __name__ == "__main__":
    main()
