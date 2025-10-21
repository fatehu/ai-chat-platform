# -*- coding: utf-8 -*-
# smtp_test_env.py
# 优化版：QQ邮箱SMTP测试脚本，处理QUIT异常，添加重试机制

import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
import ssl
import os
import sys
from dotenv import load_dotenv
import traceback
import time

# =============================================================
# 步骤 1: 加载环境变量
# =============================================================
load_dotenv()

# =============================================================
# 步骤 2: 从环境变量读取配置
# =============================================================
try:
    SENDER_ADDRESS = os.getenv("EMAIL_SENDER_ADDRESS")
    SENDER_PASSWORD = os.getenv("EMAIL_SENDER_PASSWORD")  # 授权码，非密码
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
    RECIPIENT_ADDRESS = "1605502591@qq.com"  # 请替换为有效收件人邮箱

    if not all([SENDER_ADDRESS, SENDER_PASSWORD, SMTP_SERVER]):
        print("❌ 错误: .env 文件中的 EMAIL_SENDER_ADDRESS, EMAIL_SENDER_PASSWORD 或 SMTP_SERVER 未设置。")
        sys.exit(1)

except ValueError:
    print("❌ 错误: SMTP_PORT 配置值必须是整数。")
    sys.exit(1)


def send_test_email(
    sender: str,
    password: str,
    recipient: str,
    server: str,
    port: int,
    max_attempts: int = 3
) -> bool:
    """
    QQ邮箱SMTP发送测试，优化版：处理QUIT异常，添加重试机制。
    """
    subject: str = "Agent 邮件功能测试"
    body: str = "恭喜！此邮件证明您的 Agent 邮件发送功能已正常工作。"
    
    for attempt in range(1, max_attempts + 1):
        try:
            print("=" * 60)
            print(f"尝试 {attempt}/{max_attempts}")
            print(f"SMTP 配置: {server}:{port}")
            print(f"发件人: {sender}")
            print(f"收件人: {recipient}")
            print("=" * 60)
            print("尝试连接并发送...（调试模式已启用）")
            
            # SSL上下文：强制TLS 1.2
            context: ssl.SSLContext = ssl.create_default_context()
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            
            # 使用SMTP_SSL连接，添加超时
            smtp_server = smtplib.SMTP_SSL(server, port, context=context, timeout=30)
            smtp_server.set_debuglevel(1)  # 启用调试日志
            print("✅ SSL 连接成功建立。")
            
            # 登录
            smtp_server.login(sender, password)
            print("✅ 登录认证成功。")

            # 构造邮件
            message = MIMEText(body, 'plain', 'utf-8')
            message['From'] = formataddr(["Agent Test", sender])
            message['To'] = recipient
            message['Subject'] = subject

            # 发送邮件
            smtp_server.sendmail(sender, [recipient], message.as_string())
            print(f"✅ 邮件发送成功到 {recipient}（使用sendmail）。")
            
            # 尝试正常关闭连接，忽略QUIT异常
            try:
                smtp_server.quit()
            except smtplib.SMTPResponseException as quit_e:
                print(f"⚠️ QUIT 命令异常: {quit_e}，但邮件已发送成功，可忽略。")
            
            return True

        except smtplib.SMTPAuthenticationError:
            print("❌ 错误: 登录认证失败。请检查授权码（非QQ密码）和邮箱地址。确保SMTP服务已开启。")
            return False
        except smtplib.SMTPConnectError:
            print(f"❌ 错误: 无法连接到 {server}:{port}。检查端口、网络或防火墙（允许465端口）。")
        except smtplib.SMTPServerDisconnected:
            print("❌ 错误: 服务器意外断开。可能为网络问题或QQ反垃圾限制。")
        except ssl.SSLError as e:
            print(f"❌ 错误: SSL 握手失败: {e}。尝试端口587 + STARTTLS。")
        except Exception as e:
            print(f"❌ 发生未知错误: {e}")
            print("详细Traceback:")
            traceback.print_exc()
        
        if attempt < max_attempts:
            print(f"⚠️ 尝试失败，将在3秒后重试...")
            time.sleep(3)
        else:
            print(f"❌ 达到最大重试次数 {max_attempts}，发送失败。")
            return False

if __name__ == "__main__":
    send_test_email(
        SENDER_ADDRESS,
        SENDER_PASSWORD,
        RECIPIENT_ADDRESS,
        SMTP_SERVER,
        SMTP_PORT
    )