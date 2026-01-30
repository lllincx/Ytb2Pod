import os
import json
import subprocess
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import email.utils
import urllib.parse  # 必须引入：用于处理特殊字符 URL

# 预先注册命名空间，防止出现 ns0: 
ITUNES_NS = 'http://www.itunes.com/dtds/podcast-1.0.dtd'
ET.register_namespace('itunes', ITUNES_NS)

# 先上传音频（保持原逻辑）
os.system('ossutil cp . oss://linpod/ -r --include "*.m4a" --force')

# ==========================================
# 第一阶段：基础配置
# ==========================================
BUCKET_NAME = 'linpod'
OSS_PATH = f'oss://{BUCKET_NAME}'
BASE_URL = f'https://{BUCKET_NAME}.oss-cn-shanghai.aliyuncs.com'

LOCAL_DIR = './'
RSS_FILE = 'podcast.xml'
COVER_NAME = 'cover.jpg'

# ==========================================
# 第二阶段：工具函数
# ==========================================
def run_command(cmd):
    try:
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
    print(f"[*] 正在从 OSS 下载 {RSS_FILE}...")
    success, _ = run_command(f"ossutil cp {OSS_PATH}/{RSS_FILE} ./{RSS_FILE} --force")
    
    if success and os.path.exists(RSS_FILE):
        try:
            return ET.parse(RSS_FILE).getroot()
        except:
            pass
            
    rss = ET.Element('rss', {'version': '2.0', 'xmlns:itunes': ITUNES_NS})
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = "LinPod"
    ET.SubElement(channel, 'link').text = BASE_URL
    ET.SubElement(channel, 'description').text = "Podcast by Chauncey"
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
        # 获取文件名：yt-dlp 默认音频文件名通常是 [json文件名去除.info.json] + [后缀]
        audio_filename = file.replace('.info.json', f'.{audio_ext}')
        
        if not os.path.exists(audio_filename):
            continue

        # --- 核心修复：对文件名进行 URL 编码 ---
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
        ET.SubElement(item, 'enclosure', {
            'url': audio_url,
            'length': f_size,
            'type': f'audio/mp4' if audio_ext == 'm4a' else f'audio/{audio_ext}'
        })
        
        duration = meta.get('duration')
        if duration:
            # 修正命名空间写法
            ET.SubElement(item, '{%s}duration' % ITUNES_NS).text = str(int(duration))
        
        updated = True

    return root if updated else None

def main():
    final_root = build_rss()
    
    if final_root is not None:
        xml_str = ET.tostring(final_root, encoding='utf-8')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
        # 移除 minidom 自动生成的额外空行
        pretty_xml = "\n".join([line for line in pretty_xml.splitlines() if line.strip()])
        
        with open(RSS_FILE, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        print(f"[*] 正在上传更新后的 {RSS_FILE} 到 OSS...")
        success, _ = run_command(f"ossutil cp ./{RSS_FILE} {OSS_PATH}/{RSS_FILE} --force")
        if success:
            print(f"[√] 部署成功！")
    else:
        print("[~] 无新内容，无需更新。")

    print(f"RSS Link: {BASE_URL}/{RSS_FILE}")

if __name__ == "__main__":
    main()

# 清理并移动（保持原逻辑）
os.system('rm ./*.json; mkdir -p ~/Music/Podcast/; mv ./*.m4a ~/Music/Podcast/')
