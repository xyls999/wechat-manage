"""
测试脚本：测试FastAPI后端的所有功能
"""
import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"

def print_response(title, response):
    """打印响应信息"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    try:
        data = response.json()
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
    except:
        print(f"响应: {response.text}")
    print(f"{'='*60}\n")

def test_auth():
    """测试认证模块"""
    print("\n\n🔐 测试认证模块")
    
    # 1. 注册用户
    register_data = {
        "username": "testuser123",
        "password": "test123456",
        "nickname": "测试用户"
    }
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    print_response("1. 用户注册", response)
    
    if response.status_code == 200:
        token = response.json()["data"]["token"]
        print(f"✅ 注册成功，Token: {token[:50]}...")
        return token
    elif response.status_code == 409:
        # 用户已存在，尝试登录
        print("⚠️ 用户已存在，尝试登录")
        login_data = {
            "username": "testuser123",
            "password": "test123456"
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print_response("登录", response)
        
        if response.status_code == 200:
            token = response.json()["data"]["token"]
            print(f"✅ 登录成功，Token: {token[:50]}...")
            return token
    
    return None

def test_file_operations(token):
    """测试文件操作模块"""
    print("\n\n📁 测试文件操作模块")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. 上传Excel文件
    test_file = "test_data/test_excel.xlsx"
    if not Path(test_file).exists():
        print(f"❌ 测试文件不存在: {test_file}")
        print("请先运行: python create_test_excel.py")
        return
    
    with open(test_file, "rb") as f:
        files = {"file": (test_file, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        response = requests.post(f"{BASE_URL}/files/upload", files=files, headers=headers)
        print_response("1. 上传Excel文件", response)
        
        if response.status_code != 200:
            print("❌ 上传失败")
            return
        
        file_id = response.json()["data"]["fileId"]
        print(f"✅ 上传成功，文件ID: {file_id}")
    
    # 2. 预览原始文件
    response = requests.get(f"{BASE_URL}/files/preview/{file_id}?page=1&pageSize=10", headers=headers)
    print_response("2. 预览原始文件", response)
    
    # 3. 处理文件（按会计月汇总）
    process_data = {"fileId": file_id}
    response = requests.post(f"{BASE_URL}/files/process", json=process_data, headers=headers)
    print_response("3. 处理文件（按会计月汇总）", response)
    
    if response.status_code != 200:
        print("❌ 处理失败")
        return
    
    processed_file_id = response.json()["data"]["processedFileId"]
    summary = response.json()["data"]["summary"]
    print(f"✅ 处理成功，处理后文件ID: {processed_file_id}")
    print(f"📊 汇总信息:")
    print(f"  - 原始行数: {summary['totalRows']}")
    print(f"  - 汇总后行数: {summary['groupedRows']}")
    print(f"  - 汇总列: {', '.join(summary['columns'])}")
    
    # 4. 预览处理后的文件
    response = requests.get(f"{BASE_URL}/files/preview/{processed_file_id}?page=1&pageSize=10", headers=headers)
    print_response("4. 预览处理后的文件", response)
    
    # 5. 获取下载链接
    response = requests.get(f"{BASE_URL}/files/download/{processed_file_id}", headers=headers)
    print_response("5. 获取下载链接", response)
    
    # 6. 下载文件
    response = requests.get(f"{BASE_URL}/files/direct-download/{processed_file_id}", headers=headers)
    if response.status_code == 200:
        output_file = f"test_data/downloaded_{processed_file_id}.xlsx"
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"✅ 文件下载成功: {output_file}")
    else:
        print(f"❌ 文件下载失败: {response.status_code}")
    
    # 7. 获取历史记录
    response = requests.get(f"{BASE_URL}/files/history?type=all&page=1&pageSize=10", headers=headers)
    print_response("7. 获取历史记录", response)
    
    # 8. 获取用户信息
    response = requests.get(f"{BASE_URL}/auth/profile", headers=headers)
    print_response("8. 获取用户信息", response)

def main():
    """主测试函数"""
    print("🚀 开始测试 FastAPI 后端")
    print(f"📍 API地址: {BASE_URL}")
    
    # 测试健康检查
    try:
        response = requests.get("http://localhost:8000/health")
        print_response("健康检查", response)
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        print("请确保服务器已启动: python main.py")
        return
    
    # 测试认证
    token = test_auth()
    if not token:
        print("❌ 认证失败，停止测试")
        return
    
    # 测试文件操作
    test_file_operations(token)
    
    print("\n✅ 所有测试完成!")

if __name__ == "__main__":
    main()
