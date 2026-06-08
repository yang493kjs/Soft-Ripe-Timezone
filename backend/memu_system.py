# -*- coding: utf-8 -*-
"""MemU 记忆系统 - 长期语义记忆、情节记忆、过程记忆"""
import os
import json
import uuid
import threading
from datetime import datetime, timedelta

import settings
from settings import MEMU_DATA_DIR, _get_local_embed_model, logger
from utils_json import parse_llm_json


class MemUMemorySystem:

    def __init__(self, agent_id: str, user_id: str):
        self.agent_id = agent_id
        self.user_id = user_id
        self.memory_dir = os.path.join(MEMU_DATA_DIR, agent_id, user_id)
        os.makedirs(self.memory_dir, exist_ok=True)

        self.categories_dir = os.path.join(self.memory_dir, "categories")
        self.memories_dir = os.path.join(self.memory_dir, "memories")
        self.meta_file = os.path.join(self.memory_dir, "meta.json")

        self.episodic_dir = os.path.join(self.memory_dir, "episodic")
        self.procedural_file = os.path.join(self.memory_dir, "procedural.json")

        for d in [self.categories_dir, self.memories_dir, self.episodic_dir]:
            os.makedirs(d, exist_ok=True)

        self.meta = self._load_json(self.meta_file, self._default_meta())
        self._pending = []
        self._pending_lock = threading.Lock()
        self._flush_lock = threading.Lock()

    def _default_meta(self):
        return {
            "total_exchanges": 0,
            "last_flush": None,
            "categories": {},
            "conflict_log": []
        }

    def _load_json(self, path, default):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return default

    def _save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get_embedding(self, text: str):
        model = _get_local_embed_model()
        if model and model is not False:
            try:
                result = model.encode(text, normalize_embeddings=True)
                return result.tolist()
            except Exception as e:
                print(f"[MemU Local Embed Error] {e}")

        if settings.client is None:
            return None
        try:
            resp = settings.client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return resp.data[0].embedding
        except Exception as e:
            print(f"[MemU API Embed Error] {e}")
            return None

    @staticmethod
    def _cosine_similarity(a: list, b: list):
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = (sum(x * x for x in a)) ** 0.5
        norm_b = (sum(y * y for y in b)) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def add_exchange(self, user_msg: str, ai_msg: str):
        self._store_episodic(user_msg, ai_msg)

        with self._pending_lock:
            self._pending.append({
                "role": "user",
                "content": user_msg,
                "timestamp": datetime.now().isoformat()
            })
            self._pending.append({
                "role": "assistant",
                "content": ai_msg,
                "timestamp": datetime.now().isoformat()
            })
            self.meta["total_exchanges"] += 1
            self._save_json(self.meta_file, self.meta)

            if len(self._pending) >= 6:
                threading.Thread(target=self._flush_in_background, daemon=True).start()

    def _flush_in_background(self):
        if not self._flush_lock.acquire(blocking=False):
            return
        try:
            self._do_flush()
        finally:
            self._flush_lock.release()

    def flush_sync(self):
        with self._flush_lock:
            self._do_flush()

    def _do_flush(self):
        if settings.client is None:
            logger.warning("[MemU] client未初始化，跳过flush")
            return
        with self._pending_lock:
            pending = self._pending[-10:]
            self._pending = []
            if not pending:
                return

        exchanges_text = ""
        for i, item in enumerate(pending):
            role = item["role"]
            content = item.get("content", "")
            exchanges_text += f"({role}) {content}\n"

        categories_context = self._get_category_summaries()

        old_category_names = list(categories_context.keys()) if categories_context else []

        prompt = f"""你是一个AI记忆管理助手。你需要根据最新的对话来更新长期记忆。

已有的记忆分类：
{json.dumps(categories_context, ensure_ascii=False, indent=2) if categories_context else "无"}

最近的对话：
{exchanges_text}

请分析对话并输出JSON，只输出JSON不要其他内容：
{{
  "categories": {{
    "分类名": {{"summary": "该分类的一两句话总结", "priority": 5, "decay_rate": 0.01}}
  }},
  "new_memories": [
    {{"category": "分类名", "content": "记忆内容", "type": "fact/event/feeling", "importance": 1-10}}
  ],
  "outdated_ids": ["需要移除的旧记忆ID"],
  "conflicts": [
    {{"old_id": "旧记忆ID", "new_content": "更新后内容", "reason": "冲突原因"}}
  ]
}}

分类建议（根据对话内容自动创建或更新）：
- 如果对话涉及用户的个人信息（工作、学校、兴趣爱好），创建"用户基本信息"
- 如果涉及用户当前状态（心情、忙碌程度等），创建"用户状态"
- 如果涉及你和用户的关系（好感、阶段等），创建"关系状态"
- 每个分类下保留最核心的记忆，old memories如果没有矛盾不必标记为outdated
- importance含义：10=绝对不能忘，7=重要，5=普通，3=次要，1=可遗忘
- type含义：fact=客观事实，event=发生的事件，feeling=情感相关

注意：
1. 输出的categories只包含需要更新/新建的分类。不需要更新的分类不用输出。
2. 不要凭空创建用户信息（比如年龄、星座、工作等），除非对话中明确提到。
3. 输出的记忆要简洁，每条不超过30字。"""

        try:
            resp = settings.client.chat.completions.create(
                model=settings.current_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            content = resp.choices[0].message.content.strip()
            result = parse_llm_json(content)
            self._apply_llm_result(result)
            self.meta["last_flush"] = datetime.now().isoformat()
            self._save_json(self.meta_file, self.meta)
        except Exception as e:
            print(f"[MemU Flush Error] {e}")

    def get_categories(self) -> dict:
        result = {}
        if os.path.exists(self.categories_dir):
            for fname in os.listdir(self.categories_dir):
                if fname.endswith(".json"):
                    cat_name = fname[:-5]
                    cat_file = os.path.join(self.categories_dir, fname)
                    cat_data = self._load_json(cat_file, {})
                    result[cat_name] = {
                        "summary": cat_data.get("summary", ""),
                        "priority": cat_data.get("priority", 5),
                        "memory_count": len(cat_data.get("memories", [])),
                        "decay_rate": cat_data.get("decay_rate", 0.01),
                    }
        return result

    def get_status(self) -> dict:
        return {
            "total_exchanges": self.meta.get("total_exchanges", 0),
            "last_flush": self.meta.get("last_flush"),
            "pending_count": len(self._pending),
            "categories_count": len(self.meta.get("categories", {})),
            "conflicts": len(self.meta.get("conflict_log", [])),
        }

    def _get_category_summaries(self) -> dict:
        result = {}
        if os.path.exists(self.categories_dir):
            for fname in os.listdir(self.categories_dir):
                if fname.endswith(".json"):
                    cat_name = fname[:-5]
                    cat_file = os.path.join(self.categories_dir, fname)
                    cat_data = self._load_json(cat_file, {})
                    entry = {
                        "summary": cat_data.get("summary", ""),
                        "priority": cat_data.get("priority", 5),
                        "memory_count": len(cat_data.get("memories", [])),
                    }
                    memories = cat_data.get("memories", [])
                    if cat_data.get("memory_count", 0) > 0 and not memories:
                        entry["memories"] = [
                            {"id": m.get("id", ""), "content": m.get("content", ""),
                             "created_at": m.get("created_at", "")}
                            for m in sorted(cat_data.get("_all_memories", []),
                                            key=lambda x: x.get("importance", 5), reverse=True)[:100]
                        ]
                    else:
                        entry["memories"] = [
                            {"id": m.get("id", ""), "content": m.get("content", ""),
                             "created_at": m.get("created_at", "")}
                            for m in sorted(memories, key=lambda x: x.get("importance", 5), reverse=True)[:100]
                        ]
                result[cat_name] = entry
        return result

    def _store_episodic(self, user_msg: str, ai_msg: str):
        now = datetime.now()
        date_key = now.strftime("%Y-%m-%d")
        ep_file = os.path.join(self.episodic_dir, f"{date_key}.json")
        data = self._load_json(ep_file, {"date": date_key, "exchanges": []})
        data["exchanges"].append({
            "time": now.strftime("%H:%M"),
            "user": user_msg,
            "ai": ai_msg,
            "timestamp": now.isoformat()
        })
        if len(data["exchanges"]) > 100:
            data["exchanges"] = data["exchanges"][-100:]
        self._save_json(ep_file, data)

        self._cleanup_old_episodic()

    def _cleanup_old_episodic(self):
        cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if os.path.exists(self.episodic_dir):
            for fname in os.listdir(self.episodic_dir):
                if fname.endswith(".json"):
                    date_str = fname[:-5]
                    if date_str < cutoff:
                        os.remove(os.path.join(self.episodic_dir, fname))

    def _get_episodic_context(self) -> str:
        if not os.path.exists(self.episodic_dir):
            return ""
        files = sorted([f for f in os.listdir(self.episodic_dir) if f.endswith(".json")], reverse=True)
        lines = []
        recent_count = 0
        for fname in files[:3]:
            data = self._load_json(os.path.join(self.episodic_dir, fname), {})
            exchanges = data.get("exchanges", [])
            for ex in exchanges[-5:]:
                u = ex.get("user", "")[:80]
                a = ex.get("ai", "")[:80]
                t = ex.get("time", "")
                if u or a:
                    lines.append(f"[{t}] 👤: {u}")
                    lines.append(f"[{t}] 🤖: {a}")
                    recent_count += 1
            if recent_count >= 10:
                break
        if lines:
            lines.insert(0, "## 最近对话（情节记忆，短期，7天后自动遗忘）")
        return "\n".join(lines)

    def _get_procedural_context(self) -> str:
        if not os.path.exists(self.procedural_file):
            return ""
        data = self._load_json(self.procedural_file, {})
        insights = data.get("insights", [])
        if not insights:
            return ""
        lines = ["## 你总结的相处经验（过程记忆，长期积累）"]
        for i in insights[-5:]:
            lines.append(f"- {i.get('insight', '')}")
        return "\n".join(lines)

    def add_procedural_insight(self, insight: str):
        data = self._load_json(self.procedural_file, {"insights": [], "updated_at": None})
        data["insights"].append({
            "insight": insight,
            "timestamp": datetime.now().isoformat()
        })
        if len(data["insights"]) > 20:
            data["insights"] = data["insights"][-20:]
        data["updated_at"] = datetime.now().isoformat()
        self._save_json(self.procedural_file, data)

    def _apply_llm_result(self, data: dict):
        categories = data.get("categories", {})
        for cat_name, cat_info in categories.items():
            cat_file = os.path.join(self.categories_dir, f"{cat_name}.json")
            existing = self._load_json(cat_file, {
                "name": cat_name, "summary": "", "memories": [],
                "priority": 5, "decay_rate": 0.01
            })
            if isinstance(cat_info, dict):
                if "summary" in cat_info:
                    existing["summary"] = cat_info["summary"]
                if "priority" in cat_info:
                    existing["priority"] = cat_info["priority"]
                if "decay_rate" in cat_info:
                    existing["decay_rate"] = cat_info["decay_rate"]
            existing["updated_at"] = datetime.now().isoformat()
            self._save_json(cat_file, existing)
            self.meta["categories"][cat_name] = {
                "summary": existing["summary"],
                "priority": existing["priority"],
                "decay_rate": existing["decay_rate"]
            }

        new_memories = data.get("new_memories", [])
        for mem in new_memories:
            cat_name = mem.get("category", "general")
            cat_file = os.path.join(self.categories_dir, f"{cat_name}.json")
            cat_data = self._load_json(cat_file, {
                "name": cat_name, "summary": "", "memories": [],
                "priority": 5, "decay_rate": 0.01
            })
            content = mem.get("content", "")
            mem_entry = {
                "id": str(uuid.uuid4()),
                "content": content,
                "embedding": self._get_embedding(content),
                "type": mem.get("type", "fact"),
                "importance": mem.get("importance", 5),
                "created_at": datetime.now().isoformat(),
                "expires_at": None,
                "access_count": 0,
                "last_accessed": None
            }
            cat_data["memories"].append(mem_entry)
            cat_data["memory_count"] = len(cat_data["memories"])
            self._save_json(cat_file, cat_data)
            if cat_name not in self.meta["categories"]:
                self.meta["categories"][cat_name] = {
                    "summary": "", "priority": 5, "decay_rate": 0.01
                }

        outdated_ids = data.get("outdated_ids", [])
        if outdated_ids:
            for fname in os.listdir(self.categories_dir):
                if fname.endswith(".json"):
                    cat_file = os.path.join(self.categories_dir, fname)
                    cat_data = self._load_json(cat_file, {})
                    memories = cat_data.get("memories", [])
                    original_count = len(memories)
                    cat_data["memories"] = [
                        m for m in memories if m.get("id") not in outdated_ids
                    ]
                    if len(cat_data["memories"]) != original_count:
                        cat_data["memory_count"] = len(cat_data["memories"])
                        cat_data["updated_at"] = datetime.now().isoformat()
                        self._save_json(cat_file, cat_data)

        conflicts = data.get("conflicts", [])
        if conflicts:
            conflict_log = self.meta.setdefault("conflict_log", [])
            for c in conflicts:
                conflict_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "old_id": c.get("old_id", ""),
                    "new_content": c.get("new_content", ""),
                    "reason": c.get("reason", ""),
                    "resolved": False
                })

    def get_memory_context(self, current_message: str, top_k: int = 5) -> str:
        parts = []

        episodic = self._get_episodic_context()
        if episodic:
            parts.append(episodic)

        categories = self._get_category_summaries()
        if categories:
            parts.append("【长期语义记忆】")
            for cat_name, cat_info in sorted(
                categories.items(),
                key=lambda x: self.meta.get("categories", {}).get(x[0], {}).get("priority", 5),
                reverse=True
            ):
                priority = self.meta.get("categories", {}).get(cat_name, {}).get("priority", 5)
                if priority >= 3:
                    cat_file = os.path.join(self.categories_dir, f"{cat_name}.json")
                    cat_data = self._load_json(cat_file, {})
                    memories = cat_data.get("memories", [])
                    if memories:
                        recent = sorted(memories, key=lambda m: m.get("importance", 5), reverse=True)[:3]
                        mem_texts = []
                        for m in recent:
                            created = m.get("created_at", "")[:10]
                            prefix = f"{created}: " if created else ""
                            mem_texts.append(f"{prefix}{m['content']}")
                        parts.append(f"  [{cat_name}] {' | '.join(mem_texts)}")

        relevant = self._search_relevant(current_message, top_k)
        if relevant:
            parts.append("【语义相关记忆】")
            for item in relevant:
                created = item.get("created_at", "")[:10]
                prefix = f"{created}: " if created else ""
                parts.append(f"  · {prefix}{item['content']}")

        procedural = self._get_procedural_context()
        if procedural:
            parts.append(procedural)

        return "\n\n".join(parts) if parts else ""

    def _search_relevant(self, query: str, top_k: int = 5) -> list:
        query_emb = self._get_embedding(query)
        if query_emb is None:
            return []

        scored = []
        if os.path.exists(self.categories_dir):
            for fname in os.listdir(self.categories_dir):
                if fname.endswith(".json"):
                    cat_file = os.path.join(self.categories_dir, fname)
                    cat_data = self._load_json(cat_file, {})
                    for m in cat_data.get("memories", []):
                        mem_emb = m.get("embedding")
                        if mem_emb:
                            similarity = self._cosine_similarity(query_emb, mem_emb)
                            importance = m.get("importance", 5)
                            score = similarity * 0.7 + (importance / 10.0) * 0.3
                            if similarity > 0.4:
                                scored.append({
                                    "content": m["content"],
                                    "score": score,
                                    "similarity": similarity,
                                    "importance": importance,
                                    "created_at": m.get("created_at", ""),
                                    "type": m.get("type", ""),
                                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
