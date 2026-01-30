import os
import json
import subprocess
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import email.utils
import urllib.parse

# 预先注册命名空间
ITUNES_NS = 'http://www.itunes.com/dtds/podcast-1.0.dtd'
ET.register_namespace('itunes', ITUNES_NS)
os.system('rclone copy . linpod:linpod/json --include "*.json" -P')
os.system('rclone copy . linpod:linpod --include "*.m4a" -P')
# ==========================================
# 第一阶段：基础配置 (已修改为 Cloudflare/rclone)
# ==========================================
# rclone 的配置格式为 "远程配置名:桶名"
RCLONE_REMOTE = 'linpod:linpod' 
# 你的自定义域名
BASE_URL = 'https://linpod.lllincx.cn'

LOCAL_DIR = './'
RSS_FILE = 'podcast.xml'
COVER_NAME = 'linpod.jpg'

# ==========================================
# 第二阶段：工具函数
# ==========================================
def run_command(cmd):
    try:
        # rclone 报错通常会输出到 stderr，这里一并捕获
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout
    except Exception as e:
        return False, str(e)

def format_date(date_str):
    try:
        dt = datetime.strptime(date_str, '%Y%m%d')
        return email.utils.format_datetime(dt)
    except:
        return email.utils.format_datetime(datetime.now())

# ==========================================
# 第三阶段：RSS 核心逻辑
# ==========================================
def get_existing_rss():
    print(f"[*] 正在从 Cloudflare 下载 {RSS_FILE}...")
    success, _ = run_command(f"rclone copyto {RCLONE_REMOTE}/{RSS_FILE} ./{RSS_FILE}")
    
    if success and os.path.exists(RSS_FILE):
        try:
            return ET.parse(RSS_FILE).getroot()
        except:
            pass
            
    # --- 核心修复：移除 'xmlns:itunes': ITUNES_NS ---
    # ET.register_namespace 会自动处理命名空间声明
    rss = ET.Element('rss', {'version': '2.0'}) 
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = "LinPod"
    ET.SubElement(channel, 'link').text = BASE_URL
    ET.SubElement(channel, 'description').text = "Podcast by Chauncey"
    ET.SubElement(channel, 'language').text = "zh-cn"
    # 丰富 channel 信息
    ET.SubElement(channel, '{%s}author' % ITUNES_NS).text = "Chauncey"
    ET.SubElement(channel, '{%s}image' % ITUNES_NS, {'href': f"{BASE_URL}/{COVER_NAME}"})
    return rss

def build_rss():
    root = get_existing_rss()
    channel = root.find('channel')
    existing_guids = {item.find('guid').text for item in channel.findall('item') if item.find('guid') is not None}
    
    updated = False
    # 遍历所有 json 文件
    for file in os.listdir(LOCAL_DIR):
        if not file.endswith('.info.json'):
            continue
            
        with open(file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
            
        v_id = meta.get('id')
        if v_id in existing_guids:
            continue

        print(f"[+] 发现新节目: {meta.get('title')}")
        audio_ext = meta.get('ext', 'm4a')
        # 获取文件名：yt-dlp 默认生成的音频文件名（去除 .info.json 加上后缀）
        audio_filename = file.replace('.info.json', f'.{audio_ext}')
        
        if not os.path.exists(audio_filename):
            print(f"[!] 找不到对应的音频文件: {audio_filename}")
            continue

        # --- 处理特殊字符和中文文件名 ---
        # 仅对文件名部分进行编码，BASE_URL 保持原样
        encoded_filename = urllib.parse.quote(audio_filename)
        audio_url = f"{BASE_URL}/{encoded_filename}"
        
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = meta.get('title')
        ET.SubElement(item, 'guid', {'isPermaLink': 'false'}).text = v_id
        ET.SubElement(item, 'description').text = meta.get('description', '')
        ET.SubElement(item, 'pubDate').text = format_date(meta.get('upload_date'))
        ET.SubElement(item, '{%s}author' % ITUNES_NS).text = meta.get('uploader', 'Chauncey')
        
        # 媒体附件
        f_size = str(os.path.getsize(audio_filename))
        mime_type = 'audio/mp4' if audio_ext == 'm4a' else f'audio/{audio_ext}'
        ET.SubElement(item, 'enclosure', {
            'url': audio_url,
            'length': f_size,
            'type': mime_type
        })
        
        # 持续时间
        duration = meta.get('duration')
        if duration:
            ET.SubElement(item, '{%s}duration' % ITUNES_NS).text = str(int(duration))
        
        # 封面图（如果 json 里有 thumbnail，优先使用，否则用全局封面）
        # 这里默认使用全局封面以保持简洁
        ET.SubElement(item, '{%s}image' % ITUNES_NS, {'href': f"{BASE_URL}/{COVER_NAME}"})

        updated = True

    return root if updated else None

def main():
    final_root = build_rss()
    
    if final_root is not None:
        xml_str = ET.tostring(final_root, encoding='utf-8')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
        # 移除空行并写入
        pretty_xml = "\n".join([line for line in pretty_xml.splitlines() if line.strip()])
        
        with open(RSS_FILE, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        print(f"[*] 正在上传更新后的 {RSS_FILE} 到 Cloudflare...")
        # 使用 rclone copyto 覆盖上传
        success, err = run_command(f"rclone copyto ./{RSS_FILE} {RCLONE_REMOTE}/{RSS_FILE}")
        if success:
            print(f"[√] 部署成功！")
        else:
            print(f"[×] 上传失败: {err}")
    else:
        print("[~] 无新内容，无需更新。")

    print(f"RSS Link: {BASE_URL}/{RSS_FILE}")

if __name__ == "__main__":
    main()
	
os.system('rm ./*.json; mv ./*.m4a ~/Music/Podcast/')
