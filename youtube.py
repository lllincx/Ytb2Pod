import subprocess
import json
import os

# 配置参数
WATCH_LATER_URL = "https://www.youtube.com/playlist?list=WL"
# 获取当前脚本的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 拼接成绝对地址
HISTORY_FILE = os.path.join(SCRIPT_DIR, "history.txt")
COOKIES_FROM = "safari"

def get_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_history(video_id):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{video_id}\n")

def fetch_playlist():
    print("正在获取『稍后再看』列表...")
    cmd = [
        "yt-dlp",
        "--proxy", "192.168.31.233:7890",             # 强制不使用代理
        "--flat-playlist",
        "--get-title",
        "--get-id",
        "--get-url",
        "--print", "%(title)s|%(id)s|%(webpage_url)s", # 单行输出防止错位
        "--cookies-from-browser", COOKIES_FROM,
        "--extractor-args", "youtubetab:skip=authcheck", # 跳过额外的身份校验
        WATCH_LATER_URL
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    
    # 检查标准错误输出
    if result.returncode != 0:
        print(f"读取失败，请检查网络或 Safari 权限。错误: {result.stderr}")
        return []

    lines = result.stdout.strip().split('\n')
    videos = []
    for line in lines:
        if '|' in line:
            parts = line.split('|')
            videos.append({"title": parts[0], "id": parts[1], "url": parts[2]})
    return videos

def filter_videos(videos):
    history = get_history()
    # 初次过滤已下载的
    pending = [v for v in videos if v['id'] not in history]
    
    while True:
        print("\n--- 待下载列表 ---")
        for idx, v in enumerate(pending):
            print(f"[{idx}] {v['title']} (ID: {v['id']})")
        
        user_input = input("\n请输入不想下载的编号（空格分隔，直接回车开始下载）: ").strip()
        if not user_input:
            break
        
        try:
            exclude_indices = [int(i) for i in user_input.split()]
            pending = [v for i, v in enumerate(pending) if i not in exclude_indices]
        except ValueError:
            print("错误：请输入有效的数字编号。")
            
    return pending

def download_audio(video_list):
    print(f"\n准备下载 {len(video_list)} 个音频...")
    for v in video_list:
        print(f"正在下载: {v['title']}")
        cmd = [
            "yt-dlp",
            "--proxy", "192.168.31.233:7890",        # 同样强制禁用代理
            "-f", "ba[ext=m4a]/ba",
            "--extract-audio",
            "--write-info-json",
            "--audio-format", "m4a",
            "--cookies-from-browser", COOKIES_FROM,
            "-o", f"{SCRIPT_DIR}/%(title)s.%(ext)s", # 建议下载到脚本同级目录
            v['url']
        ]
        subprocess.run(cmd)
        save_history(v['id'])

if __name__ == "__main__":
    all_videos = fetch_playlist()
    final_list = filter_videos(all_videos)
    if final_list:
        download_audio(final_list)
    else:
        print("没有需要下载的视频。")
