#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频录制辅助工具
帮助创建专业的视频教程和GIF动画
"""

import os
import sys
import time
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional


class VideoRecorder:
    """视频录制辅助类"""

    def __init__(self, output_dir: str = "assets/videos"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """加载配置文件"""
        config_file = self.output_dir.parent / "video_config.json"
        default_config = {
            "recording": {
                "resolution": "1920x1080",
                "fps": 30,
                "format": "mp4",
                "audio_codec": "aac",
                "video_codec": "libx264",
                "crf": 23
            },
            "processing": {
                "thumbnail_time": "00:00:10",
                "gif_fps": 10,
                "gif_scale": "480"
            },
            "paths": {
                "ffmpeg": "ffmpeg",
                "ffprobe": "ffprobe"
            }
        }

        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        else:
            # 创建默认配置文件
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)

        return default_config

    def create_recording_script(self, tutorial_type: str) -> str:
        """创建录制脚本"""
        scripts = {
            "quickstart": self._create_quickstart_script(),
            "features": self._create_features_script(),
            "troubleshooting": self._create_troubleshooting_script()
        }

        if tutorial_type not in scripts:
            raise ValueError(f"不支持的教程类型: {tutorial_type}")

        script_path = self.output_dir / f"record_{tutorial_type}.bat"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(scripts[tutorial_type])

        return str(script_path)

    def _create_quickstart_script(self) -> str:
        """创建快速开始录制脚本"""
        script = '''@echo off
echo 准备录制5分钟快速启动教程...
echo.

echo 1. 请确保已准备好以下内容：
echo    - 清理桌面，关闭无关程序
echo    - 准备好麦克风和录音设备
echo    - 打开浏览器，准备好GitHub页面
echo.

pause
echo.

echo 2. 开始录制...
echo 录制将进行5分钟，请按照脚本执行操作
echo.

REM OBS Studio录制命令（需要预先配置）
REM obs --startrecording --minimize-to-tray

echo 开始录制教程...
echo 第一步：展示GitHub页面和下载过程 (30秒)
timeout /t 30

echo 第二步：展示文件解压过程 (30秒)
timeout /t 30

echo 第三步：双击启动器，展示检测过程 (60秒)
timeout /t 60

echo 第四步：展示依赖安装过程 (90秒)
timeout /t 90

echo 第五步：展示服务启动和浏览器打开 (60秒)
timeout /t 60

echo 第六步：展示平台功能 (30秒)
timeout /t 30

echo 录制完成！
echo.

echo 3. 停止录制...
REM obs --stoprecording

echo 视频文件已保存到：videos\\quickstart_tutorial.mp4
echo 请运行 python video_recorder.py --process quickstart 来处理视频

pause
'''
        return script

    def _create_features_script(self) -> str:
        """创建功能演示录制脚本"""
        script = '''@echo off
echo 准备录制高级功能演示教程...
echo.

echo 1. 请确保：
echo    - 系统已成功启动
echo    - 浏览器已打开交易平台
echo    - 准备好演示数据

pause
echo.

echo 2. 开始录制功能演示...
echo 录制将进行10分钟

echo 开始录制...
echo 第一部分：策略回测功能 (3分钟)
timeout /t 180

echo 第二部分：数据分析功能 (3分钟)
timeout /t 180

echo 第三部分：性能监控功能 (2分钟)
timeout /t 120

echo 第四部分：配置和设置 (2分钟)
timeout /t 120

echo 录制完成！
echo 视频文件已保存到：videos\\features_demo.mp4

pause
'''
        return script

    def _create_troubleshooting_script(self) -> str:
        """创建故障排除录制脚本"""
        script = '''@echo off
echo 准备录制故障排除指南...
echo.

echo 1. 请准备：
echo    - 常见错误场景
echo    - 解决方案演示

pause
echo.

echo 2. 开始录制故障排除...
echo 录制将进行8分钟

echo 开始录制...
echo 第一个问题：端口被占用 (2分钟)
timeout /t 120

echo 第二个问题：依赖安装失败 (2分钟)
timeout /t 120

echo 第三个问题：服务启动失败 (2分钟)
timeout /t 120

echo 第四个问题：前端构建错误 (2分钟)
timeout /t 120

echo 录制完成！
echo 视频文件已保存到：videos\\troubleshooting_guide.mp4

pause
'''
        return script

    def process_video(self, input_file: str, tutorial_type: str) -> bool:
        """处理视频文件"""
        try:
            input_path = Path(input_file)
            if not input_path.exists():
                print(f"错误：输入文件不存在: {input_file}")
                return False

            # 输出文件路径
            output_path = self.output_dir / f"{tutorial_type}_tutorial.mp4"
            thumbnail_path = self.output_dir / "thumbnails" / f"{tutorial_type}_thumb.jpg"
            thumbnail_path.parent.mkdir(exist_ok=True)

            # 视频压缩和处理
            print(f"正在处理视频: {input_file}")
            cmd = [
                self.config["paths"]["ffmpeg"],
                "-i", str(input_path),
                "-c:v", self.config["recording"]["video_codec"],
                "-crf", str(self.config["recording"]["crf"]),
                "-c:a", self.config["recording"]["audio_codec"],
                "-b:a", "128k",
                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"视频处理失败: {result.stderr}")
                return False

            print(f"视频处理完成: {output_path}")

            # 创建缩略图
            self._create_thumbnail(str(output_path), str(thumbnail_path))

            # 创建GIF预览
            self._create_gif_preview(str(output_path), tutorial_type)

            return True

        except Exception as e:
            print(f"处理视频时出错: {e}")
            return False

    def _create_thumbnail(self, video_file: str, thumbnail_file: str) -> bool:
        """创建视频缩略图"""
        try:
            cmd = [
                self.config["paths"]["ffmpeg"],
                "-i", video_file,
                "-ss", self.config["processing"]["thumbnail_time"],
                "-vframes", "1",
                thumbnail_file
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"缩略图创建成功: {thumbnail_file}")
                return True
            else:
                print(f"缩略图创建失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"创建缩略图时出错: {e}")
            return False

    def _create_gif_preview(self, video_file: str, tutorial_type: str) -> bool:
        """创建GIF预览"""
        try:
            gif_dir = self.output_dir.parent / "gifs"
            gif_dir.mkdir(exist_ok=True)

            gif_file = gif_dir / f"{tutorial_type}_preview.gif"

            # 创建短时间预览GIF（前10秒）
            cmd = [
                self.config["paths"]["ffmpeg"],
                "-i", video_file,
                "-t", "10",
                "-vf", f"fps={self.config['processing']['gif_fps']},scale={self.config['processing']['gif_scale']}:-1:flags=lanczos",
                "-y",
                str(gif_file)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"GIF预览创建成功: {gif_file}")
                return True
            else:
                print(f"GIF预览创建失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"创建GIF预览时出错: {e}")
            return False

    def create_transcript(self, tutorial_type: str) -> str:
        """创建教程文字稿"""
        transcripts = {
            "quickstart": self._get_quickstart_transcript(),
            "features": self._get_features_transcript(),
            "troubleshooting": self._get_troubleshooting_transcript()
        }

        if tutorial_type not in transcripts:
            raise ValueError(f"不支持的教程类型: {tutorial_type}")

        transcript_dir = self.output_dir.parent / "transcripts"
        transcript_dir.mkdir(exist_ok=True)

        transcript_file = transcript_dir / f"{tutorial_type}_transcript.txt"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(transcripts[tutorial_type])

        return str(transcript_file)

    def _get_quickstart_transcript(self) -> str:
        """快速开始教程文字稿"""
        return """量化交易平台5分钟快速启动教程

[开场 - 0:00-0:30]
大家好！今天我将为大家演示如何在5分钟内启动完整的量化交易平台。
不需要任何编程知识，只需几个简单的步骤，您就能拥有专业的交易分析环境。

[步骤1：下载和安装 - 0:30-1:30]
首先，访问我们的GitHub页面，点击下载按钮获取最新版本。
下载完成后，解压文件到您喜欢的位置。
解压后，您会看到one-click-launcher文件夹，这就是我们需要的全部文件。

[步骤2：首次启动 - 1:30-3:00]
现在，双击launcher.py文件启动系统。系统会自动检测您的环境配置。
系统正在检查您的Python、Node.js等依赖环境。
如果检测到缺少依赖，系统会自动为您安装。
请耐心等待安装过程，这可能需要几分钟时间。
进度条会显示当前的安装状态。

[步骤3：系统验证 - 3:00-4:00]
太好了！所有服务都已成功启动。
您可以看到数据库、后端API、前端界面都已就绪。
系统会自动在浏览器中打开交易平台界面。
现在您可以开始使用专业的量化交易功能了。

[步骤4：功能展示 - 4:00-4:30]
让我快速展示几个主要功能：
- 策略回测：测试您的交易策略
- 数据分析：查看市场数据和趋势
- 性能监控：实时监控系统运行状态

[结尾 - 4:30-5:00]
恭喜！您已经成功启动了量化交易平台。
现在可以开始您的量化交易之旅了。如果遇到问题，
请查看README.md文件或联系我们的技术支持。

谢谢观看！
"""

    def _get_features_transcript(self) -> str:
        """功能演示文字稿"""
        return """量化交易平台高级功能演示

[介绍]
大家好！在这个视频中，我将为大家详细介绍量化交易平台的高级功能。

[第一部分：策略回测功能 - 3分钟]
策略回测是平台的核心功能之一。
您可以创建自定义的交易策略，系统会基于历史数据进行回测分析。
支持多种技术指标和交易规则。
回测结果包含详细的收益分析、风险指标和交易记录。

[第二部分：数据分析功能 - 3分钟]
平台提供了强大的数据分析工具。
您可以导入市场数据，进行技术分析和基本面分析。
支持多种图表类型和指标展示。
数据可以导出为Excel或CSV格式进行进一步分析。

[第三部分：性能监控功能 - 2分钟]
实时监控系统性能和交易状态。
包括服务器状态、数据库连接、API响应时间等关键指标。
当出现异常时，系统会自动告警并提供解决方案。

[第四部分：配置和设置 - 2分钟]
平台提供了丰富的配置选项。
您可以自定义交易参数、风险控制规则、界面主题等。
所有配置都会实时保存，确保您的设置不会丢失。

[总结]
以上就是量化交易平台的主要功能介绍。
每个功能都经过精心设计，既专业又易用。
希望这些工具能帮助您在量化交易领域取得成功！

谢谢观看！
"""

    def _get_troubleshooting_transcript(self) -> str:
        """故障排除指南文字稿"""
        return """量化交易平台故障排除指南

[介绍]
大家好！在这个视频中，我将为大家演示如何解决使用平台时可能遇到的常见问题。

[问题1：端口被占用 - 2分钟]
当您看到"端口已被占用"的错误时，通常是因为其他程序正在使用相同的端口。
解决方法：
1. 打开命令行工具，输入"netstat -ano | findstr :3000"查看端口占用情况
2. 结束占用端口的进程，或者使用自定义端口启动
3. 启动命令示例：python launcher.py --frontend-port 3001

[问题2：依赖安装失败 - 2分钟]
如果依赖安装失败，可能的原因有：
1. 网络连接问题
2. 权限不足
3. 防火墙阻止

解决方法：
1. 检查网络连接，确保能访问包管理器
2. 以管理员权限运行启动器
3. 临时关闭防火墙或添加防火墙例外

[问题3：服务启动失败 - 2分钟]
服务启动失败通常是因为：
1. 配置文件错误
2. 系统资源不足
3. 依赖服务未启动

解决方法：
1. 检查config目录下的配置文件
2. 确保有足够的内存和磁盘空间
3. 手动启动依赖服务（如Redis、PostgreSQL）

[问题4：前端构建错误 - 2分钟]
前端构建错误可能由以下原因引起：
1. Node.js版本不兼容
2. 依赖包损坏
3. 磁盘空间不足

解决方法：
1. 检查Node.js版本，确保是18.x或更高版本
2. 删除node_modules和package-lock.json，重新安装依赖
3. 清理磁盘空间

[总结]
以上就是常见问题的解决方法。
如果遇到其他问题，请查看详细的故障排除文档或联系技术支持。
我们的团队随时为您提供帮助！

谢谢观看！
"""

    def generate_tutorial_package(self, tutorial_type: str) -> Dict[str, str]:
        """生成完整的教程包"""
        try:
            result = {
                "script": self.create_recording_script(tutorial_type),
                "transcript": self.create_transcript(tutorial_type),
                "status": "准备就绪"
            }

            print(f"教程包生成成功: {tutorial_type}")
            print(f"录制脚本: {result['script']}")
            print(f"文字稿: {result['transcript']}")

            return result

        except Exception as e:
            print(f"生成教程包失败: {e}")
            return {"status": "失败", "error": str(e)}


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="视频录制辅助工具")
    parser.add_argument("--create-script", choices=["quickstart", "features", "troubleshooting"],
                       help="创建录制脚本")
    parser.add_argument("--process", choices=["quickstart", "features", "troubleshooting"],
                       help="处理视频文件")
    parser.add_argument("--input", help="输入视频文件路径")
    parser.add_argument("--create-transcript", choices=["quickstart", "features", "troubleshooting"],
                       help="创建文字稿")
    parser.add_argument("--package", choices=["quickstart", "features", "troubleshooting"],
                       help="生成完整教程包")

    args = parser.parse_args()

    recorder = VideoRecorder()

    if args.create_script:
        script_path = recorder.create_recording_script(args.create_script)
        print(f"录制脚本已创建: {script_path}")

    elif args.process and args.input:
        success = recorder.process_video(args.input, args.process)
        if success:
            print("视频处理完成")
        else:
            print("视频处理失败")

    elif args.create_transcript:
        transcript_path = recorder.create_transcript(args.create_transcript)
        print(f"文字稿已创建: {transcript_path}")

    elif args.package:
        package = recorder.generate_tutorial_package(args.package)
        print("教程包生成完成")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()