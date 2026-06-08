import urllib.request
import json
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
BASE = "http://localhost:8765"

print("=== 诊断开始 ===")

# 1. 测试 /api/config/status
print("\n1) /api/config/status:")
try:
    req = urllib.request.Request(BASE + "/api/config/status")
    resp = urllib.request.urlopen(req)
    d = json.loads(resp.read())
    print(f"   configured={d.get('configured')}, model={d.get('model')}, has_api_key={d.get('has_api_key')}")
except Exception as e:
    print(f"   失败: {e}")

# 2. 登录 1111
print("\n2) 登录 1111:")
login_data = json.dumps({"username": "1111", "password": "1111"}).encode()
req = urllib.request.Request(
    BASE + "/api/users/login",
    method="POST",
    data=login_data,
    headers={"Content-Type": "application/json"},
)
try:
    resp = urllib.request.urlopen(req)
    d = json.loads(resp.read())
    token = d.get("token", "")
    print(f"   成功: username={d.get('username')}, token={'OK' if token else 'MISSING'}")
except Exception as e:
    print(f"   失败: {e}")
    token = ""

if token:
    # 3. 查看1111的agents
    print("\n3) 查看agents.json中1111的agent:")
    with open("data/agents.json", "r", encoding="utf-8") as f:
        agents = json.load(f)
    for k, v in agents.items():
        if v.get("user_id") == "1111":
            print(f"   {k}: persona_id={v.get('persona_id')}, agent_id={v.get('agent_id')}")

    # 4. 以1111身份查消息 (用已删除的sunny)
    print("\n4) GET /api/messages?persona_id=sunny (1111 - 已删除的agent):")
    req = urllib.request.Request(
        BASE + "/api/messages?persona_id=sunny",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        resp = urllib.request.urlopen(req)
        d = json.loads(resp.read())
        msgs = d.get("messages", [])
        agent = d.get("agent")
        print(f"   消息数={len(msgs)}, agent={'存在' if agent else '不存在'}")
    except Exception as e:
        print(f"   失败: {e}")

    # 5. 以1111身份查消息 (用正确的clingy)
    print("\n5) GET /api/messages?persona_id=clingy (1111 - 正确agent):")
    req = urllib.request.Request(
        BASE + "/api/messages?persona_id=clingy",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        resp = urllib.request.urlopen(req)
        d = json.loads(resp.read())
        msgs = d.get("messages", [])
        agent = d.get("agent")
        print(f"   消息数={len(msgs)}, agent={'存在' if agent else '存在'}")
        if msgs:
            print(f"   最新消息: {msgs[-1].get('content', '')[:80]}...")
    except Exception as e:
        print(f"   失败: {e}")

    # 6. 检查1111_clingy消息文件
    print("\n6) 检查1111_clingy消息文件:")
    for k, v in agents.items():
        if v.get("user_id") == "1111" and v.get("persona_id") == "clingy":
            agent_id = v.get("agent_id")
            msg_file = f"data/messages/{agent_id}.json"
            import os
            if os.path.exists(msg_file):
                with open(msg_file, "r", encoding="utf-8") as f:
                    msgs = json.load(f)
                print(f"   {msg_file}: {len(msgs)} 条消息")
                if msgs:
                    print(f"   最新: {msgs[-1].get('content', '')[:80]}...")
            else:
                print(f"   {msg_file}: 文件不存在!")
            break
else:
    print("\n跳过需要token的测试")

# 7. 检查 1111_sunny 是否残留
with open("data/agents.json", "r", encoding="utf-8") as f:
    agents = json.load(f)
print(f"\n7) 1111_sunny 残留检查: {'存在' if '1111_sunny' in agents else '不存在'} ✅")

print()
print("如果用户 localStorage 中 sr_last_persona = sunny:")
print("→ 登录后会以 persona_id=sunny 调 loadMessages")
print("→ 1111_sunny 被删除 → 返回空消息!")
print("→ 用户看到: 聊天记录消失")

print("\n=== 诊断结束 ===")